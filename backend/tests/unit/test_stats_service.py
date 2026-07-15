from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from gophkeeper.domain.device import ACTIVE, PENDING, REVOKED, Device
from gophkeeper.domain.secret import SecretActivityCount
from gophkeeper.services.stats_service import StatsService, StatsWindow


class FakeDeviceRepository:
    def __init__(self, devices: list[Device] | None = None) -> None:
        self.devices = devices or []

    async def list_for_account(self, account_id: UUID) -> list[Device]:
        return [device for device in self.devices if device.account_id == account_id]


class FakeSecretRepository:
    def __init__(self, counts: list[SecretActivityCount] | None = None) -> None:
        self.counts = counts or []
        self.calls: list[tuple[str, datetime, datetime]] = []

    async def activity_counts(
        self, account_id: str, *, start_at: datetime, end_at: datetime
    ) -> list[SecretActivityCount]:
        self.calls.append((account_id, start_at, end_at))
        return self.counts


class FakeUnitOfWork:
    def __init__(
        self,
        *,
        devices: list[Device] | None = None,
        counts: list[SecretActivityCount] | None = None,
    ) -> None:
        self.devices = FakeDeviceRepository(devices)
        self.secrets = FakeSecretRepository(counts)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass


async def test_device_stats_are_scoped_and_keep_statuses_separate():
    account_id = uuid4()
    other_account_id = uuid4()
    devices = [
        Device(uuid4(), account_id, "active", "key-active", status=ACTIVE),
        Device(uuid4(), account_id, "revoked", "key-revoked", status=REVOKED),
        Device(uuid4(), account_id, "pending", "key-pending", status=PENDING),
        Device(uuid4(), other_account_id, "other", "key-other", status=ACTIVE),
    ]

    result = await StatsService(FakeUnitOfWork(devices=devices)).device_stats(account_id)

    assert result.trusted == 1
    assert result.revoked == 1
    assert result.pending == 1
    assert result.alerts == 2


async def test_device_stats_for_empty_account_are_zero():
    result = await StatsService(FakeUnitOfWork()).device_stats(uuid4())

    assert result.trusted == result.revoked == result.pending == result.alerts == 0


@pytest.mark.parametrize(
    ("period", "expected_days"),
    [(StatsWindow.SEVEN_DAYS, 7), (StatsWindow.THIRTY_DAYS, 30), (StatsWindow.NINETY_DAYS, 90)],
)
async def test_activity_has_one_sorted_point_per_day(period: StatsWindow, expected_days: int):
    account_id = uuid4()
    today = date(2026, 7, 15)
    event_day = today.replace(day=13)
    count = SecretActivityCount(event_day, created=2, updated=1, deleted=3)
    uow = FakeUnitOfWork(counts=[count])

    points = await StatsService(uow).activity(account_id, period, today=today)

    assert len(points) == expected_days
    assert points[-1].date == today
    assert [point.date for point in points] == sorted(point.date for point in points)
    event = next(point for point in points if point.date == event_day)
    assert (event.created, event.updated, event.deleted) == (2, 1, 3)
    assert all(
        (point.created, point.updated, point.deleted) == (0, 0, 0)
        for point in points
        if point.date != event_day
    )
    assert uow.secrets.calls == [
        (
            str(account_id),
            datetime.combine(points[0].date, datetime.min.time(), tzinfo=UTC),
            datetime(2026, 7, 16, tzinfo=UTC),
        )
    ]
