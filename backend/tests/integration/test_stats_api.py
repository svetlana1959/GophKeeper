"""Full-stack coverage for account-scoped statistics.

These are the broad tests: real ASGI app, real database, real auth. They cover
what the stats unit tests (fakes) and the activity_counts repository test can't —
that /stats/* is gated by a valid active device session, stays scoped to the
caller's account, buckets activity by UTC day, and tracks a multi-device sync +
revocation flow end to end. Set-up that has no endpoint (back-dating updated_at,
revoking a device) is done through the database directly; everything a request
can observe is asserted through the API, not re-read from SQL.
"""

import base64
import json
from datetime import UTC, date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

import gophkeeper.services.stats_service as stats_service_module
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from gophkeeper.security import tokens
from gophkeeper.settings.settings import settings
from tests.integration.helpers import bearer, join_device, register_account

pytestmark = pytest.mark.integration
_STATS_PATHS = ("/stats/overview", "/stats/activity?period=7d", "/stats/security")


def _freeze_stats_clock(monkeypatch, instant: datetime) -> None:
    """Pin the service's ``datetime.now`` so activity windows are deterministic."""

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.replace(tzinfo=None) if tz is None else instant.astimezone(tz)

    monkeypatch.setattr(stats_service_module, "datetime", FrozenDateTime)


async def _push(api_client, token: str, items: list[dict]) -> dict:
    response = await api_client.post("/sync/push", headers=bearer(token), json={"items": items})
    assert response.status_code == 200, response.text
    return response.json()


async def _set_updated_at(database, secret_id: UUID, instant: datetime) -> None:
    """Back-date a secret's updated_at — there is no API for this."""
    async with database.session() as session:
        await session.execute(
            text("UPDATE secrets SET updated_at = :updated_at WHERE id = :id"),
            {"id": secret_id, "updated_at": instant},
        )
        await session.commit()


async def _revoke(database, device_id: UUID) -> None:
    """Revoke a device through its real lifecycle — there is no revoke API yet."""
    async with SqlAlchemyUnitOfWork(database) as uow:
        device = await uow.devices.get(device_id)
        device.revoke()
        await uow.devices.save(device)
        await uow.commit()


async def test_stats_require_a_valid_active_device_session(api_client, database):
    unknown_device_token = tokens.sign(
        {"typ": "session", "did": str(uuid4()), "aid": str(uuid4())},
        secret=settings.security.secret_key.encode(),
        ttl_seconds=60,
    )
    for path in _STATS_PATHS:
        missing = await api_client.get(path)
        assert missing.status_code == 401
        assert missing.headers["www-authenticate"] == "Bearer"
        assert (await api_client.get(path, headers=bearer("not-a-token"))).status_code == 401
        unknown = await api_client.get(path, headers=bearer(unknown_device_token))
        assert unknown.status_code == 401

    account = await register_account(api_client, label="stats-auth")
    device = await join_device(api_client, inviter_token=account.token, name="authenticated")
    for path in _STATS_PATHS:
        assert (await api_client.get(path, headers=bearer(device.token))).status_code == 200

    await _revoke(database, device.id)
    for path in _STATS_PATHS:
        assert (await api_client.get(path, headers=bearer(device.token))).status_code == 401


async def test_empty_account_reports_zeroed_stats(api_client):
    account = await register_account(api_client, label="empty-stats")
    device = await join_device(api_client, inviter_token=account.token, name="only-device")

    overview = await api_client.get("/stats/overview", headers=bearer(device.token))
    security = await api_client.get("/stats/security", headers=bearer(device.token))

    assert overview.json() == {
        "passwords": 0,
        "bank_cards": 0,
        "notes": 0,
        "files": 0,
        "trusted_devices": 1,
        "revoked_devices": 0,
        "pending_devices": 0,
    }
    assert security.json() == {
        "status": "good",
        "trusted_devices": 1,
        "revoked_devices": 0,
        "pending_devices": 0,
        "alerts": 0,
        "last_sync_at": None,
    }


async def test_stats_count_only_the_callers_account(api_client, database):
    mine = await register_account(api_client, label="mine")
    my_device = await join_device(api_client, inviter_token=mine.token, name="mine-active")
    await join_device(api_client, inviter_token=mine.token, name="mine-active-two")
    revoked = await join_device(api_client, inviter_token=mine.token, name="mine-revoked")
    await _revoke(database, revoked.id)

    # A second account with different counts must not bleed into the first's stats.
    theirs = await register_account(api_client, label="theirs")
    their_device = await join_device(api_client, inviter_token=theirs.token, name="theirs-only")

    overview = await api_client.get("/stats/overview", headers=bearer(my_device.token))
    security = await api_client.get("/stats/security", headers=bearer(my_device.token))

    assert overview.json()["trusted_devices"] == 2
    assert overview.json()["revoked_devices"] == 1
    # A revoked device is a warning even with zero alerts.
    assert security.json()["status"] == "warning"

    # None of the other account's identifiers appear in this account's stats.
    my_stats = json.dumps(overview.json()) + json.dumps(security.json())
    for foreign in (str(theirs.id), str(their_device.id), their_device.public_key):
        assert foreign not in my_stats


async def test_activity_buckets_by_utc_day(api_client, database, monkeypatch):
    frozen_now = datetime(2026, 7, 15, 12, tzinfo=UTC)
    _freeze_stats_clock(monkeypatch, frozen_now)

    account = await register_account(api_client, label="activity")
    device = await join_device(api_client, inviter_token=account.token, name="activity-device")
    other = await register_account(api_client, label="activity-other")
    other_device = await join_device(api_client, inviter_token=other.token, name="other-device")

    at_start, offset_day, updated, deleted, foreign = (uuid4() for _ in range(5))

    def secret(secret_id: UUID, blob: bytes) -> dict:
        return {
            "id": str(secret_id),
            "ciphertext_b64": base64.b64encode(blob).decode("ascii"),
            "recipients": [],
        }

    await _push(api_client, device.token, [secret(sid, b"v1") for sid in (at_start, offset_day)])
    await _push(api_client, device.token, [secret(updated, b"v1"), secret(deleted, b"v1")])
    await _push(
        api_client,
        device.token,
        [{**secret(updated, b"v2"), "base_version": 1}],
    )
    await _push(
        api_client,
        device.token,
        [{"id": str(deleted), "ciphertext_b64": "", "base_version": 1, "deleted": True}],
    )
    await _push(api_client, other_device.token, [secret(foreign, b"foreign")])

    # offset_day is 07-10 23:30 in UTC-2 == 07-11 01:30 UTC — it must bucket by UTC.
    utc_minus_two = timezone(-timedelta(hours=2))
    await _set_updated_at(database, at_start, datetime(2026, 7, 9, 0, tzinfo=UTC))
    await _set_updated_at(database, offset_day, datetime(2026, 7, 10, 23, 30, tzinfo=utc_minus_two))
    await _set_updated_at(database, updated, datetime(2026, 7, 14, 23, 59, 59, tzinfo=UTC))
    await _set_updated_at(database, deleted, datetime(2026, 7, 15, 0, tzinfo=UTC))
    await _set_updated_at(database, foreign, datetime(2026, 7, 11, 12, tzinfo=UTC))

    response = await api_client.get(
        "/stats/activity", params={"period": "7d"}, headers=bearer(device.token)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    dates = [date.fromisoformat(point["date"]) for point in body["points"]]
    assert dates == sorted(dates)
    assert dates[0] == date(2026, 7, 9) and dates[-1] == date(2026, 7, 15)

    # foreign belongs to the other account and must not appear on any day.
    expected = {
        date(2026, 7, 9): (1, 0, 0),
        date(2026, 7, 11): (1, 0, 0),
        date(2026, 7, 14): (0, 1, 0),
        date(2026, 7, 15): (0, 0, 1),
    }
    for point in body["points"]:
        point_date = date.fromisoformat(point["date"])
        actual = (point["created"], point["updated"], point["deleted"])
        assert actual == expected.get(point_date, (0, 0, 0))


async def test_multidevice_sync_and_revocation_flow(api_client, database, monkeypatch):
    frozen_now = datetime(2026, 7, 15, 12, tzinfo=UTC)
    _freeze_stats_clock(monkeypatch, frozen_now)

    # Every device — including the first — joins through a web-created invite.
    account = await register_account(api_client, label="full-flow")
    first = await join_device(api_client, inviter_token=account.token, name="first-device")
    second = await join_device(api_client, inviter_token=first.token, name="second-device")
    assert first.account_id == second.account_id == account.id

    secret_id = uuid4()

    def push_first(blob: str, **extra) -> dict:
        item = {"id": str(secret_id), "ciphertext_b64": blob, "recipients": extra.pop("to", [])}
        return {**item, **extra}

    # Create, sealed to the second device, and confirm it pulls through.
    created = await _push(
        api_client,
        first.token,
        [push_first(base64.b64encode(b"v1").decode(), to=[second.public_key])],
    )
    assert created["results"][0]["status"] == "applied"
    assert created["results"][0]["version"] == 1

    pull = await api_client.get("/sync/changes", params={"since": 0}, headers=bearer(second.token))
    assert pull.json()["secrets"][0]["id"] == str(secret_id)
    cursor = pull.json()["cursor"]

    # Update, then delete — the second device sees each version via its cursor.
    await _push(
        api_client, first.token, [push_first(base64.b64encode(b"v2").decode(), base_version=1)]
    )
    pull = await api_client.get(
        "/sync/changes", params={"since": cursor}, headers=bearer(second.token)
    )
    assert pull.json()["secrets"][0]["version"] == 2
    cursor = pull.json()["cursor"]

    await _push(api_client, first.token, [push_first("", base_version=2, deleted=True)])
    pull = await api_client.get(
        "/sync/changes", params={"since": cursor}, headers=bearer(second.token)
    )
    tombstone = pull.json()["secrets"][0]
    assert tombstone["version"] == 3
    assert tombstone["deleted"] is True

    # The deletion registers as today's activity, and both devices are trusted.
    await _set_updated_at(database, secret_id, frozen_now)
    before = await api_client.get("/stats/security", headers=bearer(first.token))
    activity = await api_client.get(
        "/stats/activity", params={"period": "7d"}, headers=bearer(first.token)
    )
    assert (before.json()["trusted_devices"], before.json()["revoked_devices"]) == (2, 0)
    assert activity.json()["points"][-1] == {
        "date": "2026-07-15",
        "created": 0,
        "updated": 0,
        "deleted": 1,
    }

    # Revoke the second device: stats flip, /devices reflects it, its token dies.
    await _revoke(database, second.id)
    devices = await api_client.get("/devices", headers=bearer(first.token))
    after = await api_client.get("/stats/security", headers=bearer(first.token))
    assert {item["id"]: item["status"] for item in devices.json()} == {
        str(first.id): "active",
        str(second.id): "revoked",
    }
    assert after.json() == {
        "status": "warning",
        "trusted_devices": 1,
        "revoked_devices": 1,
        "pending_devices": 0,
        "alerts": 0,
        "last_sync_at": None,
    }
    assert (await api_client.get("/devices", headers=bearer(second.token))).status_code == 401
