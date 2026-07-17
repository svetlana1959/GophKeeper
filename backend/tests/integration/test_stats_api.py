"""Full-stack integration coverage for account-scoped statistics."""

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
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return instant.replace(tzinfo=None)
            return instant.astimezone(tz)

    monkeypatch.setattr(stats_service_module, "datetime", FrozenDateTime)


async def _push(api_client, token: str, items: list[dict]) -> dict:
    response = await api_client.post("/sync/push", headers=bearer(token), json={"items": items})
    assert response.status_code == 200, response.text
    return response.json()


async def _revoke(database, device_id: UUID) -> None:
    async with SqlAlchemyUnitOfWork(database) as uow:
        device = await uow.devices.get(device_id)
        device.revoke()
        await uow.devices.save(device)
        await uow.commit()


async def test_stats_require_valid_active_device_authentication(api_client, database):
    unknown_device_token = tokens.sign(
        {"typ": "session", "did": str(uuid4()), "aid": str(uuid4())},
        secret=settings.security.secret_key.encode(),
        ttl_seconds=60,
    )
    for path in _STATS_PATHS:
        missing = await api_client.get(path)
        assert missing.status_code == 401
        assert missing.headers["www-authenticate"] == "Bearer"

        malformed = await api_client.get(path, headers=bearer("not-a-valid-token"))
        assert malformed.status_code == 401
        unknown_device = await api_client.get(path, headers=bearer(unknown_device_token))
        assert unknown_device.status_code == 401

    account = await register_account(api_client, label="stats-auth")
    device = await join_device(api_client, inviter_token=account.token, name="authenticated-device")

    for path in _STATS_PATHS:
        response = await api_client.get(path, headers=bearer(device.token))
        assert response.status_code == 200, response.text

    await _revoke(database, device.id)

    async with SqlAlchemyUnitOfWork(database) as uow:
        stored = await uow.devices.get(device.id)
    assert stored.status == "revoked"

    for path in _STATS_PATHS:
        revoked = await api_client.get(path, headers=bearer(device.token))
        assert revoked.status_code == 401

    challenge = await api_client.post("/auth/challenge", json={"public_key": device.public_key})
    assert challenge.status_code == 401


async def test_overview_and_security_are_repeatable_and_account_scoped(api_client, database):
    empty = await register_account(api_client, label="empty-stats")
    empty_overview = await api_client.get("/stats/overview", headers=bearer(empty.token))
    empty_security = await api_client.get("/stats/security", headers=bearer(empty.token))
    assert empty_overview.status_code == 200
    assert empty_overview.json() == {
        "passwords": 0,
        "bank_cards": 0,
        "notes": 0,
        "files": 0,
        "trusted_devices": 0,
        "revoked_devices": 0,
        "pending_devices": 0,
    }
    assert empty_security.json() == {
        "status": "good",
        "trusted_devices": 0,
        "revoked_devices": 0,
        "pending_devices": 0,
        "alerts": 0,
        "last_sync_at": None,
    }

    first = await register_account(api_client, label="first-stats")
    first_active = await join_device(api_client, inviter_token=first.token, name="first-active")
    await join_device(api_client, inviter_token=first.token, name="first-active-two")
    first_revoked = await join_device(api_client, inviter_token=first.token, name="first-revoked")
    first_revoked_two = await join_device(
        api_client, inviter_token=first.token, name="first-revoked-two"
    )
    await _revoke(database, first_revoked.id)
    await _revoke(database, first_revoked_two.id)

    second = await register_account(api_client, label="second-stats")
    second_one = await join_device(api_client, inviter_token=second.token, name="second-one")
    second_two = await join_device(api_client, inviter_token=second.token, name="second-two")

    async with database.session() as session:
        before = (
            (
                await session.execute(
                    text(
                        "SELECT account_id, status, COUNT(*) AS count FROM devices "
                        "GROUP BY account_id, status ORDER BY account_id, status"
                    )
                )
            )
            .mappings()
            .all()
        )

    first_overview = await api_client.get("/stats/overview", headers=bearer(first_active.token))
    repeated = await api_client.get("/stats/overview", headers=bearer(first_active.token))
    first_security = await api_client.get("/stats/security", headers=bearer(first_active.token))
    second_overview = await api_client.get("/stats/overview", headers=bearer(second_one.token))
    second_security = await api_client.get("/stats/security", headers=bearer(second_one.token))

    assert first_overview.status_code == repeated.status_code == 200
    assert first_overview.json() == repeated.json()
    assert first_overview.json()["trusted_devices"] == 2
    assert first_overview.json()["revoked_devices"] == 2
    assert first_security.json() == {
        "status": "warning",
        "trusted_devices": 2,
        "revoked_devices": 2,
        "pending_devices": 0,
        "alerts": 0,
        "last_sync_at": None,
    }
    assert second_overview.json()["trusted_devices"] == 2
    assert second_overview.json()["revoked_devices"] == 0
    assert second_security.json()["status"] == "good"

    for value in first_overview.json().values():
        assert type(value) is int
    for foreign_value in (
        str(second.id),
        str(second_one.id),
        str(second_two.id),
        second_one.public_key,
        second_two.public_key,
    ):
        assert foreign_value not in json.dumps(first_overview.json())
        assert foreign_value not in json.dumps(first_security.json())

    async with database.session() as session:
        after = (
            (
                await session.execute(
                    text(
                        "SELECT account_id, status, COUNT(*) AS count FROM devices "
                        "GROUP BY account_id, status ORDER BY account_id, status"
                    )
                )
            )
            .mappings()
            .all()
        )
    assert before == after


@pytest.mark.parametrize(("period", "days"), [("7d", 7), ("30d", 30), ("90d", 90)])
async def test_activity_uses_utc_days_and_excludes_other_accounts(
    api_client, database, monkeypatch, period: str, days: int
):
    frozen_now = datetime(2026, 7, 15, 12, tzinfo=UTC)
    _freeze_stats_clock(monkeypatch, frozen_now)

    first = await register_account(api_client, label=f"activity-first-{period}")
    first_device = await join_device(
        api_client, inviter_token=first.token, name=f"activity-first-{period}"
    )
    second = await register_account(api_client, label=f"activity-second-{period}")
    second_device = await join_device(
        api_client, inviter_token=second.token, name=f"activity-second-{period}"
    )

    at_start = uuid4()
    offset_utc_day = uuid4()
    updated = uuid4()
    deleted = uuid4()
    foreign = uuid4()
    created_items = [
        {
            "id": str(secret_id),
            "ciphertext_b64": base64.b64encode(label).decode("ascii"),
            "recipients": [],
        }
        for secret_id, label in (
            (at_start, b"start"),
            (offset_utc_day, b"offset"),
            (updated, b"updated-v1"),
            (deleted, b"deleted-v1"),
        )
    ]
    created_response = await _push(api_client, first_device.token, created_items)
    assert [result["version"] for result in created_response["results"]] == [1, 1, 1, 1]

    await _push(
        api_client,
        first_device.token,
        [
            {
                "id": str(updated),
                "ciphertext_b64": base64.b64encode(b"updated-v2").decode("ascii"),
                "base_version": 1,
                "recipients": [],
            }
        ],
    )
    await _push(
        api_client,
        first_device.token,
        [
            {
                "id": str(deleted),
                "ciphertext_b64": "",
                "base_version": 1,
                "deleted": True,
                "recipients": [],
            }
        ],
    )
    await _push(
        api_client,
        second_device.token,
        [
            {
                "id": str(foreign),
                "ciphertext_b64": base64.b64encode(b"foreign").decode("ascii"),
                "recipients": [],
            }
        ],
    )

    utc_minus_two = timezone(-timedelta(hours=2))
    timestamps = {
        at_start: datetime(2026, 7, 9, 0, tzinfo=UTC),
        offset_utc_day: datetime(2026, 7, 10, 23, 30, tzinfo=utc_minus_two),
        updated: datetime(2026, 7, 14, 23, 59, 59, tzinfo=UTC),
        deleted: datetime(2026, 7, 15, 0, tzinfo=UTC),
        foreign: datetime(2026, 7, 11, 12, tzinfo=UTC),
    }
    async with database.session() as session:
        for secret_id, timestamp in timestamps.items():
            await session.execute(
                text("UPDATE secrets SET updated_at = :updated_at WHERE id = :id"),
                {"id": secret_id, "updated_at": timestamp},
            )
        await session.commit()

        stored = (
            (
                await session.execute(
                    text("SELECT id, account_id, version, deleted FROM secrets ORDER BY id")
                )
            )
            .mappings()
            .all()
        )
    assert len(stored) == 5
    by_id = {row["id"]: row for row in stored}
    assert by_id[updated]["version"] == 2
    assert by_id[updated]["deleted"] is False
    assert by_id[deleted]["version"] == 2
    assert by_id[deleted]["deleted"] is True
    assert by_id[foreign]["account_id"] == str(second.id)

    response = await api_client.get(
        "/stats/activity",
        params={"period": period},
        headers=bearer(first_device.token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["period"] == period
    assert len(body["points"]) == days

    dates = [date.fromisoformat(point["date"]) for point in body["points"]]
    assert dates == sorted(dates)
    assert dates[0] == frozen_now.date() - timedelta(days=days - 1)
    assert dates[-1] == frozen_now.date()

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

    invalid = await api_client.get(
        "/stats/activity",
        params={"period": "14d"},
        headers=bearer(first_device.token),
    )
    assert invalid.status_code == 422


async def test_multidevice_sync_stats_and_revocation_flow(api_client, database, monkeypatch):
    frozen_now = datetime(2026, 7, 15, 12, tzinfo=UTC)
    _freeze_stats_clock(monkeypatch, frozen_now)

    # Current architecture bootstraps devices through a web-created account invite.
    account = await register_account(api_client, label="full-flow")
    first = await join_device(api_client, inviter_token=account.token, name="first-device")
    second = await join_device(api_client, inviter_token=first.token, name="second-device")
    assert first.account_id == second.account_id == account.id

    secret_id = uuid4()
    created = await _push(
        api_client,
        first.token,
        [
            {
                "id": str(secret_id),
                "ciphertext_b64": base64.b64encode(b"version-one").decode("ascii"),
                "recipients": [second.public_key],
            }
        ],
    )
    assert created["results"][0]["status"] == "applied"
    assert created["results"][0]["version"] == 1

    first_pull = await api_client.get(
        "/sync/changes", params={"since": 0}, headers=bearer(second.token)
    )
    assert first_pull.status_code == 200
    assert first_pull.json()["secrets"][0]["id"] == str(secret_id)
    assert first_pull.json()["secrets"][0]["version"] == 1
    cursor = first_pull.json()["cursor"]

    updated = await _push(
        api_client,
        first.token,
        [
            {
                "id": str(secret_id),
                "ciphertext_b64": base64.b64encode(b"version-two").decode("ascii"),
                "base_version": 1,
                "recipients": [],
            }
        ],
    )
    assert updated["results"][0]["version"] == 2
    second_pull = await api_client.get(
        "/sync/changes", params={"since": cursor}, headers=bearer(second.token)
    )
    assert second_pull.status_code == 200
    assert second_pull.json()["secrets"][0]["version"] == 2
    cursor = second_pull.json()["cursor"]

    tombstone = await _push(
        api_client,
        first.token,
        [
            {
                "id": str(secret_id),
                "ciphertext_b64": "",
                "base_version": 2,
                "deleted": True,
                "recipients": [],
            }
        ],
    )
    assert tombstone["results"][0]["version"] == 3
    deleted_pull = await api_client.get(
        "/sync/changes", params={"since": cursor}, headers=bearer(second.token)
    )
    assert deleted_pull.status_code == 200
    assert deleted_pull.json()["secrets"][0]["deleted"] is True
    assert deleted_pull.json()["secrets"][0]["version"] == 3

    async with database.session() as session:
        await session.execute(
            text("UPDATE secrets SET updated_at = :updated_at WHERE id = :id"),
            {"id": secret_id, "updated_at": frozen_now},
        )
        await session.commit()
        secret_row = (
            (
                await session.execute(
                    text("SELECT version, deleted FROM secrets WHERE id = :id"),
                    {"id": secret_id},
                )
            )
            .mappings()
            .one()
        )
        recipient_ids = set(
            (
                await session.execute(
                    text("SELECT device_id FROM secret_recipients WHERE secret_id = :secret_id"),
                    {"secret_id": secret_id},
                )
            ).scalars()
        )
    assert secret_row == {"version": 3, "deleted": True}
    assert recipient_ids == {first.id, second.id}

    before_revoke = await api_client.get("/stats/security", headers=bearer(first.token))
    activity = await api_client.get(
        "/stats/activity", params={"period": "7d"}, headers=bearer(first.token)
    )
    assert before_revoke.json()["trusted_devices"] == 2
    assert before_revoke.json()["revoked_devices"] == 0
    assert activity.json()["points"][-1] == {
        "date": "2026-07-15",
        "created": 0,
        "updated": 0,
        "deleted": 1,
    }

    # There is no revoke API on this branch; exercise the real lifecycle and DB write.
    await _revoke(database, second.id)

    devices = await api_client.get("/devices", headers=bearer(first.token))
    after_revoke = await api_client.get("/stats/security", headers=bearer(first.token))
    assert devices.status_code == 200
    assert {item["id"]: item["status"] for item in devices.json()} == {
        str(first.id): "active",
        str(second.id): "revoked",
    }
    assert after_revoke.json() == {
        "status": "warning",
        "trusted_devices": 1,
        "revoked_devices": 1,
        "pending_devices": 0,
        "alerts": 0,
        "last_sync_at": None,
    }

    assert (
        await api_client.get("/stats/security", headers=bearer(second.token))
    ).status_code == 401
    assert (await api_client.get("/devices", headers=bearer(second.token))).status_code == 401

    async with database.session() as session:
        counts = (
            (
                await session.execute(
                    text(
                        "SELECT "
                        "(SELECT COUNT(*) FROM accounts) AS accounts, "
                        "(SELECT COUNT(*) FROM account_identities) AS identities, "
                        "(SELECT COUNT(*) FROM devices) AS devices, "
                        "(SELECT COUNT(*) FROM invites) AS invites, "
                        "(SELECT COUNT(*) FROM secrets) AS secrets"
                    )
                )
            )
            .mappings()
            .one()
        )
    assert counts == {
        "accounts": 1,
        "identities": 1,
        "devices": 2,
        "invites": 2,
        "secrets": 1,
    }
