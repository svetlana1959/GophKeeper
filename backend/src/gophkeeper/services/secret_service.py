"""Application service for secrets — the use-case layer.

EXAMPLE service. It orchestrates the domain and the Unit of Work: open the
transaction, drive the aggregate, commit. It holds no business rules itself
(those live on ``Secret``) and knows nothing about HTTP. It depends on the UoW
*port*, so it is trivially testable with a fake.
"""

from gophkeeper.domain.secret import Secret
from gophkeeper.domain.unit_of_work import UnitOfWork


class SecretService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def store(self, *, account_id: str, secret_id: str, ciphertext: bytes) -> Secret:
        async with self._uow as uow:
            secret = Secret(id=secret_id, account_id=account_id, ciphertext=ciphertext)
            await uow.secrets.add(secret)
            await uow.commit()
            return secret

    async def update(self, *, secret_id: str, ciphertext: bytes, base_version: int) -> Secret:
        async with self._uow as uow:
            secret = await uow.secrets.get(secret_id)
            secret.update(ciphertext, base_version=base_version)  # may raise VersionConflict
            await uow.secrets.save(secret)
            await uow.commit()
            return secret

    async def fetch(self, secret_id: str) -> Secret:
        async with self._uow as uow:
            return await uow.secrets.get(secret_id)
