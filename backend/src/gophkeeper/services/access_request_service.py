"""Application service for access requests."""

from uuid import UUID, uuid4

from gophkeeper.domain.access_request import AccessRequest
from gophkeeper.domain.errors import NotSecretOwner
from gophkeeper.domain.unit_of_work import UnitOfWork


class AccessRequestService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def request(self, secret_id: UUID, *, device_id: UUID) -> AccessRequest:
        """Create a pending access request."""
        async with self._uow as uow:
            await uow.devices.get(device_id)
            await uow.secrets.get(secret_id)
            request = AccessRequest(id=uuid4(), secret_id=secret_id, device_id=device_id)
            await uow.access_requests.add(request)
            await uow.commit()
            return request

    async def list_pending(self, secret_id: UUID, *, owner_device_id: UUID) -> list[AccessRequest]:
        """Return pending requests visible to the secret owner."""
        async with self._uow as uow:
            await self._ensure_owner(uow, secret_id, owner_device_id)
            return await uow.access_requests.list_pending_for_secret(secret_id)

    async def approve(self, request_id: UUID, *, owner_device_id: UUID) -> AccessRequest:
        """Approve a request and create the access grant."""
        async with self._uow as uow:
            request = await uow.access_requests.get(request_id)
            await self._ensure_owner(uow, request.secret_id, owner_device_id)
            request.approve()
            await uow.access_requests.save(request)
            await uow.access.grant(request.secret_id, request.device_id)
            await uow.commit()
            return request

    async def reject(self, request_id: UUID, *, owner_device_id: UUID) -> AccessRequest:
        """Reject a request without creating a grant."""
        async with self._uow as uow:
            request = await uow.access_requests.get(request_id)
            await self._ensure_owner(uow, request.secret_id, owner_device_id)
            request.reject()
            await uow.access_requests.save(request)
            await uow.commit()
            return request

    async def _ensure_owner(self, uow: UnitOfWork, secret_id: UUID, device_id: UUID) -> None:
        device = await uow.devices.get(device_id)
        if not device.is_active or not await uow.access.has_access(secret_id, device_id):
            raise NotSecretOwner(device_id, secret_id)
