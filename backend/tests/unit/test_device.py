from uuid import uuid4

import pytest

from gophkeeper.domain.device import ACTIVE, PENDING, REVOKED, Device
from gophkeeper.domain.errors import DomainError


def _device(*, status: str = ACTIVE) -> Device:
    return Device(
        id=uuid4(),
        account_id=uuid4(),
        device_name="laptop",
        public_key="age1device",
        status=status,
    )


def test_pending_device_can_activate():
    device = _device(status=PENDING)

    device.activate()

    assert device.status == ACTIVE
    assert device.may_authenticate() is True


def test_revoked_device_cannot_activate():
    device = _device(status=REVOKED)

    with pytest.raises(DomainError, match="cannot activate a revoked device"):
        device.activate()


def test_revoke_is_idempotent():
    device = _device()
    device.revoke()
    revoked_at = device.updated_at

    device.revoke()

    assert device.status == REVOKED
    assert device.updated_at == revoked_at


def test_invalid_status_is_rejected():
    with pytest.raises(DomainError, match="invalid device status"):
        _device(status="unknown")
