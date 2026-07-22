"""Account-scoped Dashboard statistics from zero-knowledge-safe metadata."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from uuid import UUID

from gophkeeper.domain.device import ACTIVE, PENDING, REVOKED
from gophkeeper.domain.unit_of_work import UnitOfWork


class StatsWindow(StrEnum):
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    NINETY_DAYS = "90d"

    @property
    def days(self) -> int:
        return {self.SEVEN_DAYS: 7, self.THIRTY_DAYS: 30, self.NINETY_DAYS: 90}[self]


@dataclass(frozen=True)
class DeviceStats:
    trusted: int = 0
    revoked: int = 0
    pending: int = 0

    @property
    def has_warning(self) -> bool:
        """Whether stored device lifecycle state warrants attention."""
        return self.revoked > 0 or self.pending > 0


@dataclass(frozen=True)
class ActivityPoint:
    date: date
    created: int = 0
    updated: int = 0
    deleted: int = 0


class StatsService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def device_stats(self, account_id: UUID) -> DeviceStats:
        async with self._uow as uow:
            devices = await uow.devices.list_for_account(account_id)

        statuses = {ACTIVE: 0, REVOKED: 0, PENDING: 0}
        for device in devices:
            statuses[device.status] += 1
        return DeviceStats(
            trusted=statuses[ACTIVE],
            revoked=statuses[REVOKED],
            pending=statuses[PENDING],
        )

    async def activity(
        self, account_id: UUID, period: StatsWindow, *, today: date | None = None
    ) -> list[ActivityPoint]:
        """Return daily latest-mutation counts, including zero-filled UTC days."""
        end_date = (today or datetime.now(UTC).date()) + timedelta(days=1)
        start_date = end_date - timedelta(days=period.days)
        start_at = datetime.combine(start_date, time.min, tzinfo=UTC)
        end_at = datetime.combine(end_date, time.min, tzinfo=UTC)

        async with self._uow as uow:
            counts = await uow.secrets.activity_counts(
                str(account_id), start_at=start_at, end_at=end_at
            )
        by_date = {count.date: count for count in counts}
        return [
            ActivityPoint(
                date=day,
                created=by_date[day].created if day in by_date else 0,
                updated=by_date[day].updated if day in by_date else 0,
                deleted=by_date[day].deleted if day in by_date else 0,
            )
            for offset in range(period.days)
            if (day := start_date + timedelta(days=offset))
        ]
