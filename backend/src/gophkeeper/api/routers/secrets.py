"""Secrets endpoints.

Thin by design: decode the request, call the application service, shape the
response. No business logic and no try/except for domain errors — the registered
exception handlers turn those into 403/404/409.

Multi-device access (issue #69): every route identifies the calling device via
the ``X-Device-Id`` header (see ``api/deps.get_device_id``) and the service layer
checks that device's grant before doing anything. Sharing a secret with a new
device is an asynchronous handshake: the new device creates a request, a device
that already has access reads the queue (with the requester's public key),
re-encrypts the secret locally, pushes it through ``PUT /secrets/{id}``, and only
then approves — the sole place a grant is created.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from gophkeeper.api.deps import get_device_id, provide
from gophkeeper.api.schemas.access_request import (
    AccessRequestResponse,
    PendingAccessRequestResponse,
)
from gophkeeper.api.schemas.secrets import (
    SecretResponse,
    StoreSecretRequest,
    UpdateSecretRequest,
)
from gophkeeper.services.access_request_service import AccessRequestService
from gophkeeper.services.secret_service import SecretService

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
    """All secrets the calling device is trusted to sync (issue #69)."""
    secrets = await service.list_for_device(device_id)
    return [SecretResponse.from_domain(secret) for secret in secrets]


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
    """Replace a secret's ciphertext.

    Also the endpoint used to push a re-encrypted payload when approving another
    device's access request — there is no separate write path for that.
    """
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
    """Ask to be trusted with a secret (issue #69 handshake broker).

    Queues a PENDING request; it grants nothing by itself. The calling device
    does not need existing access — asking for access it lacks is the point.
    """
    request = await service.request(secret_id, device_id=device_id)
    return AccessRequestResponse.from_domain(request)


@router.get("/{secret_id}/requests", response_model=list[PendingAccessRequestResponse])
async def list_secret_access_requests(
    secret_id: UUID,
    device_id: UUID = Depends(get_device_id),
    service: AccessRequestService = Depends(provide(AccessRequestService)),
) -> list[PendingAccessRequestResponse]:
    """Who is currently asking for access, with each requester's public key.

    Only a device that already has access may call this — it needs the public
    keys to do the client-side re-encryption.
    """
    pending = await service.list_pending(secret_id, acting_device_id=device_id)
    return [PendingAccessRequestResponse.from_pending(p) for p in pending]


@router.post("/requests/{request_id}/approve", response_model=AccessRequestResponse)
async def approve_secret_access_request(
    request_id: UUID,
    device_id: UUID = Depends(get_device_id),
    service: AccessRequestService = Depends(provide(AccessRequestService)),
) -> AccessRequestResponse:
    """Confirm a handshake completed and create the grant.

    Call only AFTER pushing the re-encrypted secret via ``PUT /secrets/{id}`` —
    this does not touch the ciphertext (the server cannot), it only records that
    the requesting device may now be trusted.
    """
    request = await service.approve(request_id, acting_device_id=device_id)
    return AccessRequestResponse.from_domain(request)


@router.post("/requests/{request_id}/reject", response_model=AccessRequestResponse)
async def reject_secret_access_request(
    request_id: UUID,
    device_id: UUID = Depends(get_device_id),
    service: AccessRequestService = Depends(provide(AccessRequestService)),
) -> AccessRequestResponse:
    """Decline a handshake. No grant is created."""
    request = await service.reject(request_id, acting_device_id=device_id)
    return AccessRequestResponse.from_domain(request)
