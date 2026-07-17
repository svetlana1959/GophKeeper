"""Application service for devices.

Devices are created by joining an account with an invite
(``EnrollmentService.join``), not by the CLI. This service fetches and lists
them, extends a device's self-declared expiry (``heartbeat``), and runs the
background sweep that deletes expired devices (``reap_expired``).
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import DeviceNotFound
from gophkeeper.domain.unit_of_work import UnitOfWork
from gophkeeper.settings.settings import settings


def capped_expiry(ttl_seconds: int | None, *, now: datetime | None = None) -> datetime | None:
    """Turn a device-declared TTL (seconds from now) into an absolute expiry,
    capped at ``device_max_ttl_seconds`` so a bad clock or client can't pin a
    device open forever. ``None`` means "never expire" (CLI devices)."""
    if ttl_seconds is None:
        return None
    capped = min(max(ttl_seconds, 0), settings.security.device_max_ttl_seconds)
    return (now or datetime.now(UTC)) + timedelta(seconds=capped)


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

    async def heartbeat(
        self, device_id: UUID, *, account_id: UUID, ttl_seconds: int
    ) -> Device:
        """Extend a device's expiry to now + ``ttl_seconds`` (capped). Called by
        an active device to keep itself alive while in use; an already-expired
        device can't reach here because it fails authentication first."""
        async with self._uow as uow:
            device = await uow.devices.get(device_id)
            if device.account_id != account_id:
                raise DeviceNotFound(device_id)
            device.set_expiry(capped_expiry(ttl_seconds))
            await uow.devices.save(device)
            await uow.commit()
            return device

    async def reap_expired(self, *, now: datetime | None = None) -> int:
        """The background sweep: delete devices past their declared expiry, plus
        the long-idle backstop that catches devices which declared none. Returns
        the total deleted. Idempotent and account-agnostic."""
        now = now or datetime.now(UTC)
        cutoff = now - timedelta(seconds=settings.security.device_inactive_sweep_seconds)
        async with self._uow as uow:
            deleted = await uow.devices.delete_expired(now=now)
            deleted += await uow.devices.delete_inactive(cutoff=cutoff)
            await uow.commit()
            return deleted
