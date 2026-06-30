"""Application service for the access-request handshake broker (issue #69).

GophKeeper is Zero-Knowledge: the server holds no keys and never grants access
on its own. This service only relays messages between devices — a requesting
device queues a PENDING request, and a device that already has the secret reads
the queue (with the requester's public key), re-encrypts the secret locally, and
pushes it through the existing ``SecretService.update()``. ``approve()`` is the
only place in the codebase that writes a row into ``secret_access``; it records
that the handshake completed and never touches ciphertext.
"""

from uuid import UUID, uuid4

from gophkeeper.domain.access_request import AccessRequest, PendingAccessRequest
from gophkeeper.domain.errors import AccessDenied, NotTrustedWithSecret
from gophkeeper.domain.unit_of_work import UnitOfWork


class AccessRequestService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def request(self, secret_id: UUID, *, device_id: UUID) -> AccessRequest:
        """Device B asks to be let in on a secret.

        Requires the requesting device to exist and be active, but not to have
        access — asking for access it lacks is the whole point. Raises
        ``AccessRequestAlreadyPending`` if it already has an outstanding request.
        """
        async with self._uow as uow:
            device = await uow.devices.get(device_id)  # raises DeviceNotFound if unknown
            if not device.is_active:
                raise AccessDenied(device_id)
            await uow.secrets.get(secret_id)  # raises SecretNotFound if unknown
            request = AccessRequest(id=uuid4(), secret_id=secret_id, device_id=device_id)
            await uow.access_requests.add(request)
            await uow.commit()
            return request

    async def list_pending(
        self, secret_id: UUID, *, acting_device_id: UUID
    ) -> list[PendingAccessRequest]:
        """The queue of pending requests for a secret, each paired with the
        requester's current public key for the re-encryption step.

        Only a device that already has access may read this — it needs the
        public keys to re-encrypt, and a device with no access has no standing
        to decide who else gets in.
        """
        async with self._uow as uow:
            await self._ensure_trusted_with_secret(uow, secret_id, acting_device_id)
            requests = await uow.access_requests.list_pending_for_secret(secret_id)
            pending = []
            for request in requests:
                requester = await uow.devices.get(request.device_id)
                pending.append(PendingAccessRequest(request, requester.public_key))
            return pending

    async def approve(self, request_id: UUID, *, acting_device_id: UUID) -> AccessRequest:
        """Confirm a handshake completed and create the grant.

        The caller is responsible for having already pushed the re-encrypted
        payload via ``SecretService.update()``; this only records approval and
        writes the grant — it never reads or touches ciphertext.
        """
        async with self._uow as uow:
            request = await uow.access_requests.get(request_id)
            await self._ensure_trusted_with_secret(uow, request.secret_id, acting_device_id)
            request.approve()  # raises AccessRequestNotPending if already settled
            await uow.access_requests.save(request)
            # The only place a grant is created in this codebase.
            await uow.access.grant(request.secret_id, request.device_id)
            await uow.commit()
            return request

    async def reject(self, request_id: UUID, *, acting_device_id: UUID) -> AccessRequest:
        """Decline a handshake. No grant is ever created."""
        async with self._uow as uow:
            request = await uow.access_requests.get(request_id)
            await self._ensure_trusted_with_secret(uow, request.secret_id, acting_device_id)
            request.reject()  # raises AccessRequestNotPending if already settled
            await uow.access_requests.save(request)
            await uow.commit()
            return request

    async def _ensure_trusted_with_secret(
        self, uow: UnitOfWork, secret_id: UUID, device_id: UUID
    ) -> None:
        # Same predicate as SecretService._ensure_access today (active + granted),
        # kept distinct because "may administer the request queue" and "may touch
        # the ciphertext" are different intents that will diverge once auth lands.
        device = await uow.devices.get(device_id)  # raises DeviceNotFound
        if not device.is_active or not await uow.access.has_access(secret_id, device_id):
            raise NotTrustedWithSecret(device_id, secret_id)
