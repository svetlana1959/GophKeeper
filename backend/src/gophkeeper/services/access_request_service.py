"""Application service for the access-request handshake broker (issue #69).

REVISION per review: GophKeeper is Zero-Knowledge. The server holds no keys,
so it can never itself decide that a new device may read a secret — that
decision and the re-encryption it requires can only happen on a device that
already holds the key. This service does not grant anything by itself; it
only relays messages between devices:

  - Device B (wants access): request() queues a PENDING row.
  - Device A (owner): list_pending() reads the queue to see who is asking and
    their public key (carried on the Device aggregate, looked up by the
    router — see api/routers/secrets.py). It re-encrypts the secret locally
    (entirely client-side, outside this service) and pushes the result
    through the *existing*, unmodified ``SecretService.update()``.
  - Device A: approve() is the ONLY place in the whole codebase that writes
    a row into ``secret_access`` — i.e. the only path to an actual grant.
    Calling it does not touch the secret; it only records that the
    handshake completed, on the assumption the caller already pushed the
    re-encrypted payload.

Compare this to the old ``SecretService.share()`` this replaces: that method
created a grant directly, with no re-encryption step at all, which is a
'access' that doesn't correspond to anything the new device could actually
decrypt. This service never makes that mistake possible, because the only
write path requires an explicit approve() call the owner makes only after
its client-side re-encryption is already done.
"""

from uuid import UUID, uuid4

from gophkeeper.domain.access_request import AccessRequest
from gophkeeper.domain.errors import NotSecretOwner
from gophkeeper.domain.unit_of_work import UnitOfWork


class AccessRequestService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def request(self, secret_id: UUID, *, device_id: UUID) -> AccessRequest:
        """Device B asks to be let in on a secret.

        Only requires the requesting device to exist and be active — it
        does NOT require existing access, since the whole point is asking
        for access it doesn't have yet. Raises ``AccessRequestAlreadyPending``
        if this device already has an outstanding request for this secret.
        """
        async with self._uow as uow:
            await uow.devices.get(device_id)  # raises DeviceNotFound if unknown
            await uow.secrets.get(secret_id)  # raises SecretNotFound if unknown
            request = AccessRequest(id=uuid4(), secret_id=secret_id, device_id=device_id)
            await uow.access_requests.add(request)
            await uow.commit()
            return request

    async def list_pending(self, secret_id: UUID, *, owner_device_id: UUID) -> list[AccessRequest]:
        """Device A checks the queue for requests against a secret it owns.

        Only a device that already has access to the secret may see who is
        asking for it — it needs to read the requester's public key to do
        the re-encryption, and a device with no access to the secret has no
        business deciding who else gets it either.
        """
        async with self._uow as uow:
            await self._ensure_owner(uow, secret_id, owner_device_id)
            return await uow.access_requests.list_pending_for_secret(secret_id)

    async def approve(self, request_id: UUID, *, owner_device_id: UUID) -> AccessRequest:
        """Device A confirms the handshake completed.

        Precondition the caller is responsible for, not this method: the
        re-encrypted secret has already been pushed via
        ``SecretService.update()``. This method's only effect is recording
        approval and writing the grant — it does not read or touch
        ciphertext, because the server is not able to: that is the entire
        point of Zero-Knowledge.
        """
        async with self._uow as uow:
            request = await uow.access_requests.get(request_id)
            await self._ensure_owner(uow, request.secret_id, owner_device_id)
            request.approve()  # raises AccessRequestNotPending if already settled
            await uow.access_requests.save(request)
            # The ONLY place a grant is created in this entire codebase.
            await uow.access.grant(request.secret_id, request.device_id)
            await uow.commit()
            return request

    async def reject(self, request_id: UUID, *, owner_device_id: UUID) -> AccessRequest:
        """Device A declines the handshake. No grant is ever created."""
        async with self._uow as uow:
            request = await uow.access_requests.get(request_id)
            await self._ensure_owner(uow, request.secret_id, owner_device_id)
            request.reject()  # raises AccessRequestNotPending if already settled
            await uow.access_requests.save(request)
            await uow.commit()
            return request

    async def _ensure_owner(self, uow: UnitOfWork, secret_id: UUID, device_id: UUID) -> None:
        device = await uow.devices.get(device_id)  # raises DeviceNotFound
        if not device.is_active or not await uow.access.has_access(secret_id, device_id):
            raise NotSecretOwner(device_id, secret_id)
