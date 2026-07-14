"""Trust-log endpoints — publish a signed device cert, pull the delta.

The trust log is the transport for the M4 device trust graph. The server relays
and orders signed vouch/revoke certs but never verifies their signatures; each
device verifies them and recomputes the trusted set locally. A device may publish
only its *own* certs, and its seq must be contiguous.
"""

from fastapi import APIRouter, Depends, Query, status

from gophkeeper.api.deps import get_principal, provide
from gophkeeper.api.schemas.trust import TrustCertBody, TrustChangesResponse
from gophkeeper.domain.errors import AuthenticationError
from gophkeeper.security.principal import DevicePrincipal
from gophkeeper.services.trust_log_service import TrustLogService

router = APIRouter(prefix="/trust", tags=["trust"])

_UNAUTHORIZED = {401: {"description": "Missing, invalid, or expired bearer token."}}


@router.post(
    "/certs",
    response_model=TrustCertBody,
    status_code=status.HTTP_201_CREATED,
    summary="Publish a signed trust cert",
    responses={
        **_UNAUTHORIZED,
        409: {"description": "The cert's seq is not the next in the issuer's chain."},
    },
)
async def publish(
    body: TrustCertBody,
    principal: DevicePrincipal = Depends(get_principal),
    service: TrustLogService = Depends(provide(TrustLogService)),
) -> TrustCertBody:
    """Append a vouch/revoke cert to the caller's account trust log.

    The authenticated device may publish only its own certs (`issuer_id` must be
    this device), and its `seq` must be exactly one past its last published cert.
    The server stores the cert opaquely; it does not check the signature.
    """
    if body.issuer_id != str(principal.device_id):
        raise AuthenticationError("a device may only publish its own trust certs")
    cert = await service.publish(
        account_id=principal.account_id,
        issuer_device_id=principal.device_id,
        kind=body.kind,
        issuer_seq=body.seq,
        payload=body.model_dump(),
    )
    return TrustCertBody(**cert.payload)


@router.get(
    "/certs",
    response_model=TrustChangesResponse,
    summary="Pull trust certs since a cursor",
    responses=_UNAUTHORIZED,
)
async def changes(
    since: int = Query(
        default=0, ge=0, description="Highest log cursor already seen; 0 for the full log"
    ),
    principal: DevicePrincipal = Depends(get_principal),
    service: TrustLogService = Depends(provide(TrustLogService)),
) -> TrustChangesResponse:
    """Return the account's trust certs with `log_seq > since`, in order.

    The client verifies every cert's signature and per-issuer chain, then
    recomputes which devices are trusted.
    """
    certs, cursor = await service.changes(account_id=principal.account_id, since=since)
    return TrustChangesResponse(certs=[TrustCertBody(**c.payload) for c in certs], cursor=cursor)
