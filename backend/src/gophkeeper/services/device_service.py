"""Application service for devices.

Read-only: devices are created by joining an account with an invite
(``EnrollmentService.join``), not by the CLI. This service just fetches and
lists them, scoped to an account.
"""

from uuid import UUID

from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import DeviceNotFound
from gophkeeper.domain.unit_of_work import UnitOfWork


class DeviceService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def fetch(self, device_id: UUID, *, account_id: UUID) -> Device:
        """Return a device, scoped to the caller's account.

        A device from another account is reported as not found rather than
        disclosed, so the id cannot be used to enumerate other accounts' rows.
        """
        async with self._uow as uow:
            device = await uow.devices.get(device_id)
        if device.account_id != account_id:
            raise DeviceNotFound(device_id)
        return device

    async def list_for_account(self, account_id: UUID) -> list[Device]:
        async with self._uow as uow:
            return await uow.devices.list_for_account(account_id)
