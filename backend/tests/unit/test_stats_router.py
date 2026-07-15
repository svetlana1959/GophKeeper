from datetime import date, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gophkeeper.api.deps import get_account_id
from gophkeeper.api.routers import stats as stats_router
from gophkeeper.services.stats_service import ActivityPoint, DeviceStats


class FakeStatsService:
    def __init__(self, devices: DeviceStats | None = None) -> None:
        self.devices = devices or DeviceStats()

    async def device_stats(self, _account_id):
        return self.devices

    async def activity(self, _account_id, period):
        start = date(2026, 1, 1)
        return [ActivityPoint(start + timedelta(days=day)) for day in range(period.days)]


def _client(service: FakeStatsService) -> TestClient:
    app = FastAPI()
    app.include_router(stats_router.router)
    app.dependency_overrides[get_account_id] = lambda: uuid4()
    app.dependency_overrides[stats_router._stats_service] = lambda: service
    return TestClient(app)


def test_security_uses_real_device_summary_and_has_no_fake_sync_time():
    with _client(FakeStatsService(DeviceStats(trusted=2, revoked=1, pending=1))) as client:
        response = client.get("/stats/security")

    assert response.status_code == 200
    assert response.json() == {
        "status": "warning",
        "trusted_devices": 2,
        "revoked_devices": 1,
        "pending_devices": 1,
        "alerts": 2,
        "last_sync_at": None,
    }


def test_empty_security_is_good_and_all_counts_are_zero():
    with _client(FakeStatsService()) as client:
        response = client.get("/stats/security")

    assert response.status_code == 200
    assert response.json() == {
        "status": "good",
        "trusted_devices": 0,
        "revoked_devices": 0,
        "pending_devices": 0,
        "alerts": 0,
        "last_sync_at": None,
    }


def test_empty_overview_still_works_without_category_metadata():
    with _client(FakeStatsService()) as client:
        response = client.get("/stats/overview")

    assert response.status_code == 200
    assert response.json() == {
        "passwords": 0,
        "bank_cards": 0,
        "notes": 0,
        "files": 0,
        "trusted_devices": 0,
        "revoked_devices": 0,
        "pending_devices": 0,
    }


@pytest.mark.parametrize(("period", "days"), [("7d", 7), ("30d", 30), ("90d", 90)])
def test_activity_returns_requested_number_of_points(period: str, days: int):
    with _client(FakeStatsService()) as client:
        response = client.get("/stats/activity", params={"period": period})

    assert response.status_code == 200
    assert response.json()["period"] == period
    assert len(response.json()["points"]) == days


def test_activity_rejects_unknown_period():
    with _client(FakeStatsService()) as client:
        response = client.get("/stats/activity", params={"period": "14d"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "period"]
