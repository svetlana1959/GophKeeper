"""Unit tests for the AccessRequest aggregate."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from gophkeeper.domain.access_request import AccessRequest, AccessRequestStatus
from gophkeeper.domain.errors import AccessRequestNotPending, DomainError


def _make_request() -> AccessRequest:
    return AccessRequest(id=uuid4(), secret_id=uuid4(), device_id=uuid4())


@pytest.mark.parametrize(
    "field",
    ["secret_id", "device_id"],
)
def test_access_request_rejects_missing_identifiers(field: str) -> None:
    values = {"id": uuid4(), "secret_id": uuid4(), "device_id": uuid4()}
    values[field] = None

    with pytest.raises(DomainError):
        AccessRequest(**values)


def test_approve_marks_request_approved_and_updates_timestamp() -> None:
    request = _make_request()
    approved_at = datetime(2026, 6, 30, 12, 0, tzinfo=UTC)

    request.approve(at=approved_at)

    assert request.status is AccessRequestStatus.APPROVED
    assert request.updated_at == approved_at
    assert request.is_pending is False


def test_reject_marks_request_rejected_and_updates_timestamp() -> None:
    request = _make_request()
    rejected_at = datetime(2026, 6, 30, 12, 5, tzinfo=UTC)

    request.reject(at=rejected_at)

    assert request.status is AccessRequestStatus.REJECTED
    assert request.updated_at == rejected_at
    assert request.is_pending is False


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_settled_request_cannot_be_changed_again(action: str) -> None:
    request = _make_request()
    request.approve()

    with pytest.raises(AccessRequestNotPending) as exc_info:
        getattr(request, action)()

    assert exc_info.value.current_status == AccessRequestStatus.APPROVED
