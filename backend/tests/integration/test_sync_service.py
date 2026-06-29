"""Integration test for SyncService against real PostgreSQL (issue #68).

SyncService itself introduces no new SQL — it composes the existing
secrets/devices/access repositories, which already have their own
integration coverage. This test exists to catch the class of bug seen
earlier in this codebase: a service-level behavior that's correct against
fakes but breaks against the real UUID/asyncpg wire format (e.g. comparing a
raw asyncpg UUID type against a plain uuid.UUID).
"""

from uuid import uuid4

import pytest

from gophkeeper.domain.device import Device
from gophkeeper.domain.secret import Secret
from gophkeeper.domain.sync import ClientSecretState, SyncOutcome, SyncStatus
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from gophkeeper.services.sync_service import SyncService

pytestmark = pytest.mark.integration


async def test_sync_round_trip_against_real_database(database):
    device_a_id = uuid4()
    device_b_id = uuid4()
    secret_id = uuid4()

    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.devices.add(
            Device(id=device_a_id, device_name="A", public_key="ka", is_active=True)
        )
        await uow.devices.add(
            Device(id=device_b_id, device_name="B", public_key="kb", is_active=True)
        )
        await uow.secrets.add(Secret(id=secret_id, account_id="acc", ciphertext=b"v1"))
        await uow.access.grant(secret_id, device_a_id)
        await uow.access.grant(secret_id, device_b_id)
        await uow.commit()

    # device B syncs cold (no local state) -> discovers the secret as NEW
    report = await SyncService(SqlAlchemyUnitOfWork(database)).sync(
        device_id=device_b_id, client_state=[]
    )
    assert report.status == SyncStatus.OK
    assert report.results[0].outcome == SyncOutcome.NEW
    assert report.results[0].secret_id == secret_id
    assert report.results[0].ciphertext == b"v1"

    # device A updates the secret
    async with SqlAlchemyUnitOfWork(database) as uow:
        secret = await uow.secrets.get(secret_id)
        secret.update(b"v2", base_version=1)
        await uow.secrets.save(secret)
        await uow.commit()

    # device B syncs again with its now-stale version=1 -> UPDATED
    report = await SyncService(SqlAlchemyUnitOfWork(database)).sync(
        device_id=device_b_id,
        client_state=[ClientSecretState(id=secret_id, version=1)],
    )
    assert report.results[0].outcome == SyncOutcome.UPDATED
    assert report.results[0].version == 2
    assert report.results[0].ciphertext == b"v2"


async def test_sync_reports_access_revoked_against_real_database(database):
    device_id = uuid4()
    secret_id = uuid4()

    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.devices.add(
            Device(id=device_id, device_name="D", public_key="kd", is_active=True)
        )
        # secret exists, but this device is never granted access to it
        await uow.secrets.add(Secret(id=secret_id, account_id="acc", ciphertext=b"v1"))
        await uow.commit()

    report = await SyncService(SqlAlchemyUnitOfWork(database)).sync(
        device_id=device_id,
        client_state=[ClientSecretState(id=secret_id, version=1)],
    )

    assert report.status == SyncStatus.PARTIAL
    assert report.results[0].outcome == SyncOutcome.ACCESS_REVOKED
    assert report.results[0].ciphertext is None
