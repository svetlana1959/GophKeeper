"""Sync endpoints — push local changes, pull the delta.

Both are scoped to the authenticated device's account (from get_principal), so a
device can only ever sync its own account's secrets.
"""

from fastapi import APIRouter, Depends, Query

from gophkeeper.api.deps import get_principal, provide
from gophkeeper.api.schemas.sync import (
    ChangedSecretResponse,
    ChangesResponse,
    PushRequest,
    PushResponse,
    PushResultResponse,
)
from gophkeeper.security.principal import DevicePrincipal
from gophkeeper.services.sync_service import PushItem, SyncService

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/push", response_model=PushResponse)
async def push(
    body: PushRequest,
    principal: DevicePrincipal = Depends(get_principal),
    service: SyncService = Depends(provide(SyncService)),
) -> PushResponse:
    items = [
        PushItem(
            id=item.id,
            ciphertext=item.ciphertext,
            base_version=item.base_version,
            deleted=item.deleted,
        )
        for item in body.items
    ]
    results = await service.push(account_id=str(principal.account_id), items=items)
    return PushResponse(
        results=[
            PushResultResponse(id=r.id, status=r.status, version=r.version, seq=r.seq)
            for r in results
        ]
    )


@router.get("/changes", response_model=ChangesResponse)
async def changes(
    since: int = Query(default=0, ge=0),
    principal: DevicePrincipal = Depends(get_principal),
    service: SyncService = Depends(provide(SyncService)),
) -> ChangesResponse:
    secrets, cursor = await service.changes(account_id=str(principal.account_id), since=since)
    return ChangesResponse(
        secrets=[ChangedSecretResponse.from_domain(s) for s in secrets],
        cursor=cursor,
    )
