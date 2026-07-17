"""Narrow DeviceRepository test — the SQL contract stats depends on.

Device persistence round-trips through the API in the sync/revocation flow
(test_stats_api.py). What that flow doesn't pin down at the SQL layer is that
``list_for_account`` returns *every* status (not just active ones) and stays
scoped to one account — the query the security summary counts over. A status
filter or a missing account predicate would silently skew every account's stats,
so it's asserted directly here.
"""

from uuid import uuid4

import pytest

from gophkeeper.domain.account import Account
from gophkeeper.domain.device import ACTIVE, REVOKED, Device
from gophkeeper.domain.errors import DeviceNotFound
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


async def test_get_unknown_device_raises(database):
    # SyncService catches this branch; DeviceService.fetch reraises its own, so the
    # repository's own not-found is only reachable here.
    async with SqlAlchemyUnitOfWork(database) as uow:
        with pytest.raises(DeviceNotFound):
            await uow.devices.get(uuid4())


async def test_list_for_account_returns_all_statuses_scoped_to_the_account(database):
    account_id = uuid4()
    other_account_id = uuid4()
    active_id = uuid4()
    revoked_id = uuid4()

    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.accounts.add(Account(id=account_id))
        await uow.accounts.add(Account(id=other_account_id))
        await uow.devices.add(
            Device(active_id, account_id, "laptop", "key-active", "sign-active", status=ACTIVE)
        )
        await uow.devices.add(
            Device(revoked_id, account_id, "phone", "key-revoked", status=REVOKED)
        )
        await uow.devices.add(Device(uuid4(), other_account_id, "intruder", "key-other"))
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        devices = await uow.devices.list_for_account(account_id)

    by_id = {d.id: d for d in devices}
    # Only this account's devices, and revoked ones are kept (not filtered out).
    assert set(by_id) == {active_id, revoked_id}
    assert by_id[active_id].is_active is True
    assert by_id[revoked_id].is_active is False
    # Columns map to the right fields (not transposed) and round-trip intact.
    active = by_id[active_id]
    assert (active.device_name, active.public_key, active.sign_public_key) == (
        "laptop",
        "key-active",
        "sign-active",
    )
