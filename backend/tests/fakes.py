"""In-memory fakes for the repositories and Unit of Work.

Shared by the service unit tests and the API tests so both drive the real
service/router code against a fast, real (not mocked) implementation of the
out-of-process dependencies, and assert on final state.
"""

from uuid import UUID, uuid4

from gophkeeper.domain.access_request import AccessRequest, AccessRequestStatus
from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import (
    AccessRequestAlreadyPending,
    AccessRequestNotFound,
    DeviceNotFound,
    SecretNotFound,
)
from gophkeeper.domain.secret import Secret


class FakeDeviceRepository:
    def __init__(self) -> None:
        self.devices: dict[UUID, Device] = {}

    async def add(self, device: Device) -> None:
        self.devices[device.id] = device

    async def get(self, device_id: UUID) -> Device:
        if device_id not in self.devices:
            raise DeviceNotFound(device_id)
        return self.devices[device_id]

    async def exists(self, device_id: UUID) -> bool:
        return device_id in self.devices

    async def list_active(self) -> list[Device]:
        return [d for d in self.devices.values() if d.is_active]

    async def save(self, device: Device) -> None:
        self.devices[device.id] = device


class FakeSecretRepository:
    def __init__(self) -> None:
        self.secrets: dict[UUID, Secret] = {}

    async def add(self, secret: Secret) -> None:
        self.secrets[secret.id] = secret

    async def get(self, secret_id: UUID) -> Secret:
        if secret_id not in self.secrets:
            raise SecretNotFound(secret_id)
        return self.secrets[secret_id]

    async def list_for_account(self, account_id: str, *, include_deleted: bool = False):
        return [s for s in self.secrets.values() if s.account_id == account_id]

    async def save(self, secret: Secret) -> None:
        self.secrets[secret.id] = secret


class FakeSecretAccessRepository:
    def __init__(self) -> None:
        self.grants: set[tuple[UUID, UUID]] = set()
        self.grant_calls: list[tuple[UUID, UUID]] = []

    async def grant(self, secret_id: UUID, device_id: UUID) -> None:
        self.grants.add((secret_id, device_id))
        self.grant_calls.append((secret_id, device_id))

    async def has_access(self, secret_id: UUID, device_id: UUID) -> bool:
        return (secret_id, device_id) in self.grants

    async def list_secret_ids_for_device(self, device_id: UUID) -> list[UUID]:
        return [sid for sid, did in self.grants if did == device_id]


class FakeAccessRequestRepository:
    def __init__(self) -> None:
        self.requests: dict[UUID, AccessRequest] = {}

    async def add(self, request: AccessRequest) -> None:
        for existing in self.requests.values():
            if (
                existing.secret_id == request.secret_id
                and existing.device_id == request.device_id
                and existing.status == AccessRequestStatus.PENDING
            ):
                raise AccessRequestAlreadyPending(request.secret_id, request.device_id)
        self.requests[request.id] = request

    async def get(self, request_id: UUID) -> AccessRequest:
        if request_id not in self.requests:
            raise AccessRequestNotFound(request_id)
        return self.requests[request_id]

    async def list_pending_for_secret(self, secret_id: UUID) -> list[AccessRequest]:
        return [
            r
            for r in self.requests.values()
            if r.secret_id == secret_id and r.status == AccessRequestStatus.PENDING
        ]

    async def save(self, request: AccessRequest) -> None:
        self.requests[request.id] = request


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.devices = FakeDeviceRepository()
        self.secrets = FakeSecretRepository()
        self.access = FakeSecretAccessRepository()
        self.access_requests = FakeAccessRequestRepository()
        self.committed = False

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, *_) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass


def make_device(*, public_key: str = "pk", is_active: bool = True) -> Device:
    return Device(id=uuid4(), device_name="d", public_key=public_key, is_active=is_active)
