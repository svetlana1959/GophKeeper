"""Device aggregate — the expiry rules the reaper and auth path depend on."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from gophkeeper.domain.device import ACTIVE, REVOKED, Device


def _device(**kw) -> Device:
    return Device(id=uuid4(), account_id=uuid4(), device_name="d", public_key="age1", **kw)


def test_device_without_expiry_never_expires():
    device = _device()
    assert device.is_expired() is False
    assert device.may_authenticate() is True


def test_device_is_expired_only_after_its_expiry():
    now = datetime.now(UTC)
    device = _device(expires_at=now)
    assert device.is_expired(at=now - timedelta(seconds=1)) is False
    assert device.is_expired(at=now) is True
    assert device.is_expired(at=now + timedelta(seconds=1)) is True


def test_expired_device_may_not_authenticate():
    device = _device(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    assert device.may_authenticate() is False


def test_revoked_device_may_not_authenticate_even_if_unexpired():
    device = _device(status=REVOKED, expires_at=datetime.now(UTC) + timedelta(days=1))
    assert device.may_authenticate() is False


def test_set_expiry_updates_the_field_and_can_clear_it():
    device = _device()
    later = datetime.now(UTC) + timedelta(hours=1)
    device.set_expiry(later)
    assert device.expires_at == later
    assert device.status == ACTIVE  # unrelated to lifecycle
    device.set_expiry(None)
    assert device.expires_at is None
