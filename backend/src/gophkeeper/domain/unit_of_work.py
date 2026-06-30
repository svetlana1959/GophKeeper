"""Unit of Work port."""

from types import TracebackType
from typing import Protocol, Self

from gophkeeper.domain.access_request import AccessRequestRepository
from gophkeeper.domain.device import DeviceRepository
from gophkeeper.domain.secret import SecretAccessRepository, SecretRepository


class UnitOfWork(Protocol):
    secrets: SecretRepository
    devices: DeviceRepository
    access: SecretAccessRepository
    access_requests: AccessRequestRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
