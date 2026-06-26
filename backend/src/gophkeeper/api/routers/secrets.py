"""Secrets endpoints.

EXAMPLE router. Thin by design: decode the request, call the application
service, shape the response. No business logic here — and no try/except for
domain errors, which the registered exception handlers turn into 403/404/409.

Multi-device access (issue #69): every route identifies the calling device via
the ``X-Device-Id`` header (see ``api/deps.get_device_id``) and the service
layer checks that device's grant before doing anything.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from gophkeeper.api.deps import get_device_id, provide
from gophkeeper.api.schemas.secrets import (
    SecretResponse,
    ShareSecretRequest,
    StoreSecretRequest,
    UpdateSecretRequest,
)
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
    secret = await service.update(
        secret_id=secret_id,
        device_id=device_id,
        ciphertext=body.ciphertext,
        base_version=body.base_version,
    )
    return SecretResponse.from_domain(secret)


@router.post("/{secret_id}/share", status_code=status.HTTP_204_NO_CONTENT)
async def share_secret(
    secret_id: UUID,
    body: ShareSecretRequest,
    device_id: UUID = Depends(get_device_id),
    service: SecretService = Depends(provide(SecretService)),
) -> None:
    """Trust another device with this secret (issue #69).

    The calling device must already have access; it can only extend trust it
    holds itself, not grant access on behalf of a secret it can't see.
    """
    await service.share(secret_id, from_device_id=device_id, to_device_id=body.device_id)


@router.delete("/{secret_id}/share/{target_device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_secret_access(
    secret_id: UUID,
    target_device_id: UUID,
    device_id: UUID = Depends(get_device_id),
    service: SecretService = Depends(provide(SecretService)),
) -> None:
    """Revoke a device's access to this secret (e.g. the device was lost)."""

    await service.revoke(
        secret_id, requesting_device_id=device_id, target_device_id=target_device_id
    )
