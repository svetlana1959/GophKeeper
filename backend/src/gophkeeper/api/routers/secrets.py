"""Secrets endpoints.

EXAMPLE router. Thin by design: decode the request, call the application
service, shape the response. No business logic here — and no try/except for
domain errors, which the registered exception handlers turn into 403/404/409.

Multi-device access (issue #69): every route identifies the calling device via
the ``X-Device-Id`` header (see ``api/deps.get_device_id``) and the service
layer checks that device's grant before doing anything.

REVISION per review: the previous version of this router exposed
``POST /secrets/{id}/share`` and ``DELETE /secrets/{id}/share/{device_id}``,
letting any device with access grant another device access directly with no
re-encryption step — wrong for a Zero-Knowledge system. Those two routes are
gone. In their place: an asynchronous request queue. A device that wants
access creates a request; the secret's owner reads the queue (getting the
requester's public key along with it), re-encrypts the secret locally, pushes
it through the unchanged ``PUT /secrets/{id}``, and only then approves the
request — which is the sole place a grant gets created.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from gophkeeper.api.deps import get_device_id, provide
from gophkeeper.api.schemas.access_request import AccessRequestResponse
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
    """All secrets the calling device is trusted to sync.

    This is the multi-device sync endpoint: a trusted device calls this on
    sign-in or reconnect and gets every secret it currently has access to,
    regardless of which device most recently wrote it (issue #69).
    """
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

    Also the endpoint a secret's owner re-uses to push a re-encrypted payload
    after approving another device's access request — see
    ``POST /secrets/requests/{request_id}/approve`` below. No separate write
    path exists for that case; this one is it.
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

    Queues a PENDING request the secret's owner can see and act on — this
    endpoint does not grant anything by itself. The calling device does not
    need existing access to call this; asking for access it doesn't have
    yet is the whole point.
    """
    request = await service.request(secret_id, device_id=device_id)
    return AccessRequestResponse.from_domain(request)


@router.get("/{secret_id}/requests", response_model=list[AccessRequestResponse])
async def list_secret_access_requests(
    secret_id: UUID,
    device_id: UUID = Depends(get_device_id),
    service: AccessRequestService = Depends(provide(AccessRequestService)),
) -> list[AccessRequestResponse]:
    """The secret owner's view of who is currently asking for access.

    Only a device that already has access to this secret may call this — it
    needs the requesters' public keys (looked up via the device_id on each
    pending request) to do the client-side re-encryption.
    """
    requests = await service.list_pending(secret_id, owner_device_id=device_id)
    return [AccessRequestResponse.from_domain(r) for r in requests]


@router.post("/requests/{request_id}/approve", response_model=AccessRequestResponse)
async def approve_secret_access_request(
    request_id: UUID,
    device_id: UUID = Depends(get_device_id),
    service: AccessRequestService = Depends(provide(AccessRequestService)),
) -> AccessRequestResponse:
    """Confirm a handshake completed and create the grant.

    Call this only AFTER pushing the re-encrypted secret via
    ``PUT /secrets/{id}`` — this endpoint does not touch the secret's
    ciphertext itself (the server cannot: Zero-Knowledge), it only records
    that the requesting device may now be trusted.
    """
    request = await service.approve(request_id, owner_device_id=device_id)
    return AccessRequestResponse.from_domain(request)


@router.post("/requests/{request_id}/reject", response_model=AccessRequestResponse)
async def reject_secret_access_request(
    request_id: UUID,
    device_id: UUID = Depends(get_device_id),
    service: AccessRequestService = Depends(provide(AccessRequestService)),
) -> AccessRequestResponse:
    """Decline a handshake. No grant is created."""
    request = await service.reject(request_id, owner_device_id=device_id)
    return AccessRequestResponse.from_domain(request)
