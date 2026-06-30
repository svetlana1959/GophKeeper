"""Unit tests for FastAPI dependencies and domain-error mapping."""

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException, status

from gophkeeper.api import deps, errors
from gophkeeper.domain.errors import (
    AccessDenied,
    AccessRequestAlreadyPending,
    AccessRequestNotFound,
    AccessRequestNotPending,
    DeviceAlreadyExists,
    DeviceNotFound,
    NotSecretOwner,
    SecretNotFound,
    VersionConflict,
)
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


class FakeService:
    def __init__(self, uow: object) -> None:
        self.uow = uow


def _response_body(response) -> dict[str, object]:
    return json.loads(response.body)


def test_get_database_reads_adapter_from_application_state() -> None:
    database = object()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(database=database)))

    assert deps.get_database(request) is database


def test_get_uow_builds_sqlalchemy_unit_of_work_without_opening_a_session() -> None:
    database = object()

    uow = deps.get_uow(database)

    assert isinstance(uow, SqlAlchemyUnitOfWork)
    assert uow._database is database


def test_get_device_id_returns_header_value_or_raises_clear_http_error() -> None:
    device_id = uuid4()

    assert deps.get_device_id(device_id) == device_id

    with pytest.raises(HTTPException) as exc_info:
        deps.get_device_id(None)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "X-Device-Id header is required"


def test_provide_builds_service_from_the_request_unit_of_work() -> None:
    uow = object()
    provider = deps.provide(FakeService)

    service = provider(uow)

    assert isinstance(service, FakeService)
    assert service.uow is uow


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        SecretNotFound(uuid4()),
        DeviceNotFound(uuid4()),
        AccessRequestNotFound(uuid4()),
    ],
)
async def test_not_found_handler_returns_404(error: Exception) -> None:
    response = await errors._not_found_handler(None, error)  # type: ignore[arg-type]

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert _response_body(response)["detail"] == str(error)


@pytest.mark.asyncio
async def test_conflict_handler_includes_version_details_only_for_version_conflicts() -> None:
    secret_id = uuid4()
    version_conflict = VersionConflict(secret_id, expected=1, actual=2)

    version_response = await errors._conflict_handler(None, version_conflict)  # type: ignore[arg-type]
    duplicate = DeviceAlreadyExists(uuid4())
    duplicate_response = await errors._conflict_handler(  # type: ignore[arg-type]
        None,
        duplicate,
    )

    assert version_response.status_code == status.HTTP_409_CONFLICT
    assert _response_body(version_response) == {
        "detail": str(version_conflict),
        "expected_version": 1,
        "actual_version": 2,
    }
    assert _response_body(duplicate_response) == {"detail": str(duplicate)}
    assert "expected_version" not in _response_body(duplicate_response)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        DeviceAlreadyExists(uuid4()),
        AccessRequestAlreadyPending(uuid4(), uuid4()),
        AccessRequestNotPending(uuid4(), "APPROVED"),
    ],
)
async def test_non_version_conflict_errors_return_409(error: Exception) -> None:
    response = await errors._conflict_handler(None, error)  # type: ignore[arg-type]

    assert response.status_code == status.HTTP_409_CONFLICT
    assert _response_body(response) == {"detail": str(error)}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        AccessDenied(uuid4()),
        NotSecretOwner(uuid4(), uuid4()),
    ],
)
async def test_forbidden_handler_returns_403(error: Exception) -> None:
    response = await errors._forbidden_handler(None, error)  # type: ignore[arg-type]

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert _response_body(response)["detail"] == str(error)


def test_register_exception_handlers_registers_every_domain_error_group() -> None:
    app = FastAPI()

    errors.register_exception_handlers(app)

    assert SecretNotFound in app.exception_handlers
    assert DeviceNotFound in app.exception_handlers
    assert AccessRequestNotFound in app.exception_handlers
    assert DeviceAlreadyExists in app.exception_handlers
    assert VersionConflict in app.exception_handlers
    assert AccessRequestAlreadyPending in app.exception_handlers
    assert AccessRequestNotPending in app.exception_handlers
    assert AccessDenied in app.exception_handlers
    assert NotSecretOwner in app.exception_handlers
