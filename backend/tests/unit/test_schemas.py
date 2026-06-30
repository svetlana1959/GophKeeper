"""Unit tests for API schemas and domain-to-response conversion.

These are pure Pydantic/DTO tests. They verify the HTTP wire format without
starting FastAPI or connecting to a database.

Covers:
- base64 decoding and validation for ciphertext;
- request DTO conversion to domain sync values;
- response DTO conversion from Device, Secret, AccessRequest, and Sync data.
"""

import base64
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from gophkeeper.api.schemas.access_request import AccessRequestResponse
from gophkeeper.api.schemas.device import DeviceResponse, RegisterDeviceRequest
from gophkeeper.api.schemas.secrets import SecretResponse, StoreSecretRequest, UpdateSecretRequest
from gophkeeper.api.schemas.sync import SyncReportResponse, SyncRequest, SyncResultResponse
from gophkeeper.domain.access_request import AccessRequest, AccessRequestStatus
from gophkeeper.domain.device import Device
from gophkeeper.domain.secret import Secret
from gophkeeper.domain.sync import (
    ClientSecretState,
    SyncOutcome,
    SyncReport,
    SyncResult,
    SyncStatus,
)


def test_store_secret_request_decodes_valid_base64_ciphertext() -> None:
    secret_id = uuid4()
    request = StoreSecretRequest(
        id=secret_id,
        account_id="account-1",
        ciphertext_b64=base64.b64encode(b"encrypted-value").decode("ascii"),
    )

    assert request.id == secret_id
    assert request.ciphertext == b"encrypted-value"


def test_store_secret_request_rejects_invalid_base64() -> None:
    """Invalid ciphertext must fail before it reaches domain/service code."""
    with pytest.raises(ValidationError, match="ciphertext_b64 must be valid base64"):
        StoreSecretRequest(id=uuid4(), account_id="account-1", ciphertext_b64="not base64!")


def test_update_secret_request_decodes_ciphertext() -> None:
    request = UpdateSecretRequest(
        ciphertext_b64=base64.b64encode(b"next-value").decode("ascii"),
        base_version=2,
    )

    assert request.ciphertext == b"next-value"
    assert request.base_version == 2


def test_device_and_access_request_responses_are_built_from_domain_objects() -> None:
    updated_at = datetime(2026, 6, 30, 12, 0, tzinfo=UTC)
    device = Device(
        id=uuid4(),
        device_name="MacBook",
        public_key="public-key",
        is_active=True,
        updated_at=updated_at,
    )
    access_request = AccessRequest(
        id=uuid4(),
        secret_id=uuid4(),
        device_id=device.id,
        status=AccessRequestStatus.PENDING,
        updated_at=updated_at,
    )

    register = RegisterDeviceRequest(
        id=device.id,
        device_name=device.device_name,
        public_key=device.public_key,
    )
    device_response = DeviceResponse.from_domain(device)
    request_response = AccessRequestResponse.from_domain(access_request)

    assert register.id == device.id
    assert device_response.model_dump() == {
        "id": device.id,
        "device_name": "MacBook",
        "public_key": "public-key",
        "is_active": True,
        "updated_at": updated_at,
    }
    assert request_response.status == "PENDING"
    assert request_response.secret_id == access_request.secret_id


def test_secret_and_sync_responses_encode_ciphertext_as_base64() -> None:
    updated_at = datetime(2026, 6, 30, 12, 0, tzinfo=UTC)
    secret = Secret(
        id=uuid4(),
        account_id="account-1",
        ciphertext=b"ciphertext",
        updated_at=updated_at,
    )
    report = SyncReport(
        status=SyncStatus.PARTIAL,
        results=[
            SyncResult(
                secret_id=secret.id,
                outcome=SyncOutcome.UPDATED,
                version=1,
                ciphertext=b"ciphertext",
                updated_at=updated_at,
            ),
            SyncResult(secret_id=uuid4(), outcome=SyncOutcome.ACCESS_REVOKED),
        ],
    )

    secret_response = SecretResponse.from_domain(secret)
    report_response = SyncReportResponse.from_domain(report)
    denied_response = SyncResultResponse.from_domain(report.results[1])

    assert secret_response.ciphertext_b64 == base64.b64encode(b"ciphertext").decode("ascii")
    assert report_response.status == "PARTIAL"
    assert report_response.results[0].ciphertext_b64 == secret_response.ciphertext_b64
    assert denied_response.ciphertext_b64 is None
    assert denied_response.version is None


def test_sync_request_converts_each_client_entry_to_domain_value() -> None:
    first_id = uuid4()
    second_id = uuid4()
    request = SyncRequest(
        client_state=[
            {"id": first_id, "version": 1},
            {"id": second_id, "version": 3},
        ]
    )

    assert request.to_domain() == [
        ClientSecretState(id=first_id, version=1),
        ClientSecretState(id=second_id, version=3),
    ]
