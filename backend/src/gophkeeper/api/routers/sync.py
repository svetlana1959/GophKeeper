"""Sync endpoints — push local changes, pull the delta.

Both are scoped to the authenticated device's account (from get_principal), so a
device can only ever sync its own account's secrets.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from gophkeeper.api.deps import get_account_id, get_principal, provide
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


_UNAUTHORIZED = {401: {"description": "Missing, invalid, or expired bearer token."}}


@router.post(
    "/push",
    response_model=PushResponse,
    summary="Push local changes",
    responses=_UNAUTHORIZED,
)
async def push(
    body: PushRequest,
    principal: DevicePrincipal = Depends(get_principal),
    service: SyncService = Depends(provide(SyncService)),
) -> PushResponse:
    """Upload a batch of changes for the caller's account.

    Each item is created, updated against its `base_version`, or tombstoned.
    Optimistic concurrency is per item: a stale write comes back with
    `status: "conflict"` and the winning `version` (so the client can pull and
    reconcile) while the rest of the batch still applies. `recipients` sets which
    devices may pull the secret.
    """
    items = [
        PushItem(
            id=item.id,
            ciphertext=item.ciphertext,
            base_version=item.base_version,
            deleted=item.deleted,
            recipients=item.recipients,
        )
        for item in body.items
    ]
    results = await service.push(
        account_id=str(principal.account_id),
        device_id=principal.device_id,
        items=items,
    )
    return PushResponse(
        results=[
            PushResultResponse(id=r.id, status=r.status, version=r.version, seq=r.seq)
            for r in results
        ]
    )


@router.get(
    "/changes",
    response_model=ChangesResponse,
    summary="Pull changes since a cursor",
    responses=_UNAUTHORIZED,
)
async def changes(
    since: int = Query(
        default=0, ge=0, description="Highest seq already applied; 0 for a full pull"
    ),
    principal: DevicePrincipal = Depends(get_principal),
    service: SyncService = Depends(provide(SyncService)),
) -> ChangesResponse:
    """Return the secrets this device may read with `seq > since`.

    Results are ordered by `seq` and include tombstones (deleted secrets) so the
    deletion propagates. The response `cursor` is the new high-water mark to pass
    as `since` next time.
    """
    secrets, cursor = await service.changes(
        account_id=str(principal.account_id), device_id=principal.device_id, since=since
    )
    return ChangesResponse(
        secrets=[ChangedSecretResponse.from_domain(s) for s in secrets],
        cursor=cursor,
    )


@router.get(
    "/all",
    response_model=ChangesResponse,
    summary="Read the whole account's ciphertext (recovery / full decrypt)",
    responses=_UNAUTHORIZED,
)
async def all_secrets(
    account_id: UUID = Depends(get_account_id),
    service: SyncService = Depends(provide(SyncService)),
) -> ChangesResponse:
    """Return every live secret in the account, regardless of recipient.

    For a client that decrypts with the recovery key — which is a recipient in the
    ciphertext but not a device, so it can't use the recipient-scoped `/changes`.
    Payloads are opaque; a caller that isn't a recipient still can't read them.
    Accepts either a web (account) or a device session.
    """
    secrets = await service.all_for_account(str(account_id))
    return ChangesResponse(
        secrets=[ChangedSecretResponse.from_domain(s) for s in secrets],
        cursor=max((s.seq for s in secrets), default=0),
    )
