"""Unit tests for the Device aggregate."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import DomainError


def _make_device(*, is_active: bool = True) -> Device:
    return Device(
        id=uuid4(),
        device_name="MacBook",
        public_key="public-key",
        is_active=is_active,
    )


@pytest.mark.parametrize(
    "field, value",
    [
        ("device_name", ""),
        ("public_key", ""),
    ],
)
def test_device_rejects_empty_required_fields(field: str, value: str) -> None:
    values = {
        "id": uuid4(),
        "device_name": "MacBook",
        "public_key": "public-key",
        "is_active": True,
    }
    values[field] = value

    with pytest.raises(DomainError):
        Device(**values)


def test_deactivate_marks_device_inactive_and_updates_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _make_device()
    deactivated_at = datetime(2026, 6, 30, 12, 0, tzinfo=UTC)
    monkeypatch.setattr("gophkeeper.domain.device._now", lambda: deactivated_at)

    device.deactivate()

    assert device.is_active is False
    assert device.updated_at == deactivated_at


def test_activate_marks_device_active_and_updates_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _make_device(is_active=False)
    activated_at = datetime(2026, 6, 30, 12, 5, tzinfo=UTC)
    monkeypatch.setattr("gophkeeper.domain.device._now", lambda: activated_at)

    device.activate()

    assert device.is_active is True
    assert device.updated_at == activated_at
