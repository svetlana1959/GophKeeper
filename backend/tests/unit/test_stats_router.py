from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import mark

from gophkeeper.api.routers import stats as stats_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(stats_router.router)
    return TestClient(app)


def test_overview_returns_mock_dashboard_counts():
    with _client() as client:
        response = client.get("/stats/overview")

    assert response.status_code == 200
    assert response.json() == {
        "passwords": 71,
        "bank_cards": 4,
        "notes": 35,
        "files": 13,
        "trusted_devices": 4,
        "revoked_devices": 0,
    }


@mark.parametrize(("period", "expected_points"), [("7d", 7), ("30d", 30), ("90d", 90)])
def test_activity_returns_requested_number_of_points(period: str, expected_points: int):
    with _client() as client:
        response = client.get("/stats/activity", params={"period": period})

    body = response.json()
    assert response.status_code == 200
    assert body["period"] == period
    assert len(body["points"]) == expected_points
    assert body["points"][-1]["date"] == "2026-07-13"
    assert {"date", "created", "updated", "deleted"} <= body["points"][0].keys()


def test_activity_defaults_to_seven_days():
    with _client() as client:
        response = client.get("/stats/activity")

    assert response.status_code == 200
    assert response.json()["period"] == "7d"
    assert len(response.json()["points"]) == 7


def test_activity_rejects_unknown_period():
    with _client() as client:
        response = client.get("/stats/activity", params={"period": "14d"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "period"]


def test_security_returns_mock_security_summary():
    with _client() as client:
        response = client.get("/stats/security")

    assert response.status_code == 200
    assert response.json() == {
        "status": "good",
        "trusted_devices": 4,
        "revoked_devices": 0,
        "alerts": 0,
        "last_sync_at": "2026-07-13T21:30:00Z",
    }
