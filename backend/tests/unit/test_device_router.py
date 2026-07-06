from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gophkeeper.api.deps import get_principal, get_uow
from gophkeeper.api.errors import register_exception_handlers
from gophkeeper.api.routers import device as device_router
from gophkeeper.domain.device import REVOKED, Device
from gophkeeper.domain.errors import DeviceNotFound
from gophkeeper.security import tokens
from gophkeeper.security.principal import DevicePrincipal
from gophkeeper.settings.settings import settings


class FakeDeviceRepository:
    def __init__(self, devices: list[Device] | None = None) -> None:
        self.devices = {device.id: device for device in devices or []}
        self.saved: list[UUID] = []

    async def get(self, device_id: UUID) -> Device:
        if device_id not in self.devices:
            raise DeviceNotFound(device_id)
        return self.devices[device_id]

    async def save(self, device: Device) -> None:
        self.devices[device.id] = device
        self.saved.append(device.id)

    async def list_for_account(self, account_id: UUID) -> list[Device]:
        return [device for device in self.devices.values() if device.account_id == account_id]


class FakeUnitOfWork:
    def __init__(self, devices: list[Device] | None = None) -> None:
        self.devices = FakeDeviceRepository(devices)
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass


def _app(uow: FakeUnitOfWork) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(device_router.router)
    app.dependency_overrides[get_uow] = lambda: uow
    return app


def _session_token(device: Device) -> str:
    return tokens.sign(
        {
            "typ": "session",
            "did": str(device.id),
            "aid": str(device.account_id),
        },
        secret=settings.security.secret_key.encode(),
        ttl_seconds=60,
    )


def test_self_revoke_persists_status_and_invalidates_session():
    device = Device(
        id=uuid4(),
        account_id=uuid4(),
        device_name="laptop",
        public_key="age1device",
    )
    uow = FakeUnitOfWork([device])
    headers = {"Authorization": f"Bearer {_session_token(device)}"}

    with TestClient(_app(uow)) as client:
        response = client.post("/devices/self/revoke", headers=headers)
        denied = client.get("/devices", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == REVOKED
    assert uow.devices.devices[device.id].status == REVOKED
    assert uow.devices.saved == [device.id]
    assert uow.committed is True
    assert denied.status_code == 401
    assert denied.json() == {"detail": "device is not active"}


def test_self_revoke_missing_device_returns_not_found():
    principal = DevicePrincipal(device_id=uuid4(), account_id=uuid4())
    uow = FakeUnitOfWork()
    app = _app(uow)
    app.dependency_overrides[get_principal] = lambda: principal

    with TestClient(app) as client:
        response = client.post("/devices/self/revoke")

    assert response.status_code == 404
    assert response.json() == {"detail": f"device {principal.device_id} not found"}
    assert uow.devices.saved == []
    assert uow.committed is False
