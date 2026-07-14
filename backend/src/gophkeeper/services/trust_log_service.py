"""Application service for the device trust log.

publish appends one signed cert after checking the issuer's seq is the next in
its chain (contiguous, no gaps or rewinds). changes returns the account's certs
since a cursor. The server never verifies signatures — that is the client's job;
here it only relays and orders. See docs/sync_design.md §11.
"""

from typing import Any
from uuid import UUID, uuid4

from gophkeeper.domain.errors import TrustCertConflict
from gophkeeper.domain.trust import TrustCert
from gophkeeper.domain.unit_of_work import UnitOfWork

# One page of certs per pull. Trust logs are small (a few certs per device), so a
# generous page returns the whole log in one round trip for any real account.
_PAGE = 500


class TrustLogService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def publish(
        self,
        *,
        account_id: UUID,
        issuer_device_id: UUID,
        kind: str,
        issuer_seq: int,
        payload: dict[str, Any],
    ) -> TrustCert:
        """Append a cert issued by issuer_device_id, enforcing seq contiguity."""
        async with self._uow as uow:
            last = await uow.trust_certs.max_issuer_seq(issuer_device_id)
            expected = 0 if last is None else last + 1
            if issuer_seq != expected:
                raise TrustCertConflict(issuer_device_id, expected, issuer_seq)

            cert = TrustCert(
                id=uuid4(),
                account_id=account_id,
                issuer_device_id=issuer_device_id,
                issuer_seq=issuer_seq,
                kind=kind,
                payload=payload,
            )
            cert.log_seq = await uow.trust_certs.add(cert)
            await uow.commit()
            return cert

    async def changes(self, *, account_id: UUID, since: int) -> tuple[list[TrustCert], int]:
        """Return the account's certs with log_seq > since, and the new cursor."""
        async with self._uow as uow:
            certs = await uow.trust_certs.list_since(account_id, since, limit=_PAGE)
            cursor = certs[-1].log_seq if certs else since
            return certs, cursor
