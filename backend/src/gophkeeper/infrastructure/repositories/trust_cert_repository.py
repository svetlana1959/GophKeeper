"""SQLAlchemy implementation of the TrustCertRepository port."""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from gophkeeper.domain.trust import TrustCert, TrustCertRepository


def _from_row(row: RowMapping) -> TrustCert:
    payload: Any = row["payload"]
    if isinstance(payload, str):  # asyncpg may hand JSONB back as raw text
        payload = json.loads(payload)
    return TrustCert(
        id=row["id"],
        account_id=row["account_id"],
        issuer_device_id=row["issuer_device_id"],
        issuer_seq=row["issuer_seq"],
        kind=row["kind"],
        payload=payload,
        log_seq=row["log_seq"],
    )


class SqlAlchemyTrustCertRepository(TrustCertRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, cert: TrustCert) -> int:
        result = await self._session.execute(
            text(
                "INSERT INTO trust_certs "
                "(id, account_id, issuer_device_id, issuer_seq, kind, payload) "
                "VALUES (:id, :account_id, :issuer_device_id, :issuer_seq, :kind, "
                "CAST(:payload AS JSONB)) RETURNING log_seq"
            ),
            {
                "id": cert.id,
                "account_id": cert.account_id,
                "issuer_device_id": cert.issuer_device_id,
                "issuer_seq": cert.issuer_seq,
                "kind": cert.kind,
                "payload": json.dumps(cert.payload),
            },
        )
        return result.scalar_one()

    async def max_issuer_seq(self, issuer_device_id: UUID) -> int | None:
        result = await self._session.execute(
            text("SELECT MAX(issuer_seq) FROM trust_certs WHERE issuer_device_id = :id"),
            {"id": issuer_device_id},
        )
        return result.scalar_one_or_none()

    async def list_since(self, account_id: UUID, since: int, *, limit: int) -> list[TrustCert]:
        result = await self._session.execute(
            text(
                "SELECT id, account_id, issuer_device_id, issuer_seq, kind, payload, log_seq "
                "FROM trust_certs WHERE account_id = :account_id AND log_seq > :since "
                "ORDER BY log_seq LIMIT :limit"
            ),
            {"account_id": account_id, "since": since, "limit": limit},
        )
        return [_from_row(row) for row in result.mappings().all()]
