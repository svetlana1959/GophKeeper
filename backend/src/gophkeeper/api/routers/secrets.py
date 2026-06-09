"""Secrets endpoints.

EXAMPLE router. Thin by design: decode the request, call the application
service, shape the response. No business logic here — and no try/except for
domain errors, which the registered exception handlers turn into 404/409.
"""

from fastapi import APIRouter, Depends, status

from gophkeeper.api.deps import provide
from gophkeeper.api.schemas.secrets import (
    SecretResponse,
    StoreSecretRequest,
    UpdateSecretRequest,
)
from gophkeeper.services.secret_service import SecretService

router = APIRouter(prefix="/secrets", tags=["secrets"])


@router.post("", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
async def store_secret(
    body: StoreSecretRequest,
    service: SecretService = Depends(provide(SecretService)),
) -> SecretResponse:
    secret = await service.store(
        account_id=body.account_id,
        secret_id=body.id,
        ciphertext=body.ciphertext,
    )
    return SecretResponse.from_domain(secret)


@router.get("/{secret_id}", response_model=SecretResponse)
async def fetch_secret(
    secret_id: str,
    service: SecretService = Depends(provide(SecretService)),
) -> SecretResponse:
    secret = await service.fetch(secret_id)
    return SecretResponse.from_domain(secret)


@router.put("/{secret_id}", response_model=SecretResponse)
async def update_secret(
    secret_id: str,
    body: UpdateSecretRequest,
    service: SecretService = Depends(provide(SecretService)),
) -> SecretResponse:
    secret = await service.update(
        secret_id=secret_id,
        ciphertext=body.ciphertext,
        base_version=body.base_version,
    )
    return SecretResponse.from_domain(secret)
