"""Secrets endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from gophkeeper.api.deps import get_device_id, provide
from gophkeeper.api.schemas.access_request import AccessRequestResponse
from gophkeeper.api.schemas.secrets import (
    SecretResponse,
    StoreSecretRequest,
    UpdateSecretRequest,
)
from gophkeeper.api.schemas.sync import SyncReportResponse, SyncRequest
from gophkeeper.services.access_request_service import AccessRequestService
from gophkeeper.services.secret_service import SecretService
from gophkeeper.services.sync_service import SyncService

router = APIRouter(prefix="/secrets", tags=["secrets"])


@router.post("", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
async def store_secret(
    body: StoreSecretRequest,
    device_id: UUID = Depends(get_device_id),
    service: SecretService = Depends(provide(SecretService)),
) -> SecretResponse:
    secret = await service.store(
        account_id=body.account_id,
        secret_id=body.id,
        device_id=device_id,
        ciphertext=body.ciphertext,
    )
    return SecretResponse.from_domain(secret)


@router.get("", response_model=list[SecretResponse])
async def list_secrets(
    device_id: UUID = Depends(get_device_id),
    service: SecretService = Depends(provide(SecretService)),
) -> list[SecretResponse]:
    """Return secrets the calling device may sync."""
    secrets = await service.list_for_device(device_id)
    return [SecretResponse.from_domain(secret) for secret in secrets]


@router.post("/sync", response_model=SyncReportResponse)
async def sync_secrets(
    body: SyncRequest,
    device_id: UUID = Depends(get_device_id),
    service: SyncService = Depends(provide(SyncService)),
) -> SyncReportResponse:
    """Synchronize the calling device's local secret state."""
    report = await service.sync(device_id=device_id, client_state=body.to_domain())
    return SyncReportResponse.from_domain(report)


@router.get("/{secret_id}", response_model=SecretResponse)
async def fetch_secret(
    secret_id: UUID,
    device_id: UUID = Depends(get_device_id),
    service: SecretService = Depends(provide(SecretService)),
) -> SecretResponse:
    secret = await service.fetch(secret_id, device_id=device_id)
    return SecretResponse.from_domain(secret)


@router.put("/{secret_id}", response_model=SecretResponse)
async def update_secret(
    secret_id: UUID,
    body: UpdateSecretRequest,
    device_id: UUID = Depends(get_device_id),
    service: SecretService = Depends(provide(SecretService)),
) -> SecretResponse:
    """Replace a secret's ciphertext."""
    secret = await service.update(
        secret_id=secret_id,
        device_id=device_id,
        ciphertext=body.ciphertext,
        base_version=body.base_version,
    )
    return SecretResponse.from_domain(secret)


@router.post(
    "/{secret_id}/requests",
    response_model=AccessRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_secret_access(
    secret_id: UUID,
    device_id: UUID = Depends(get_device_id),
    service: AccessRequestService = Depends(provide(AccessRequestService)),
) -> AccessRequestResponse:
    """Create a pending access request for this secret."""
    request = await service.request(secret_id, device_id=device_id)
    return AccessRequestResponse.from_domain(request)


@router.get("/{secret_id}/requests", response_model=list[AccessRequestResponse])
async def list_secret_access_requests(
    secret_id: UUID,
    device_id: UUID = Depends(get_device_id),
    service: AccessRequestService = Depends(provide(AccessRequestService)),
) -> list[AccessRequestResponse]:
    """Return pending access requests for this secret."""
    requests = await service.list_pending(secret_id, owner_device_id=device_id)
    return [AccessRequestResponse.from_domain(r) for r in requests]


@router.post("/requests/{request_id}/approve", response_model=AccessRequestResponse)
async def approve_secret_access_request(
    request_id: UUID,
    device_id: UUID = Depends(get_device_id),
    service: AccessRequestService = Depends(provide(AccessRequestService)),
) -> AccessRequestResponse:
    """Approve an access request."""
    request = await service.approve(request_id, owner_device_id=device_id)
    return AccessRequestResponse.from_domain(request)


@router.post("/requests/{request_id}/reject", response_model=AccessRequestResponse)
async def reject_secret_access_request(
    request_id: UUID,
    device_id: UUID = Depends(get_device_id),
    service: AccessRequestService = Depends(provide(AccessRequestService)),
) -> AccessRequestResponse:
    """Reject an access request."""
    request = await service.reject(request_id, owner_device_id=device_id)
    return AccessRequestResponse.from_domain(request)
