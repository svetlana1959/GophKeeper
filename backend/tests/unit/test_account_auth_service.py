from uuid import UUID

import pytest

from gophkeeper.domain.account import Account
from gophkeeper.domain.errors import (
    AccountNotFound,
    AuthenticationError,
    EmailAlreadyRegistered,
    RecoveryKeyAlreadySet,
)
from gophkeeper.domain.identity import AccountIdentity
from gophkeeper.services.account_auth_service import AccountAuthService


class FakeAccountRepository:
    def __init__(self):
        self.accounts: dict[UUID, Account] = {}

    async def add(self, account: Account) -> None:
        self.accounts[account.id] = account

    async def get(self, account_id: UUID) -> Account:
        if account_id not in self.accounts:
            raise AccountNotFound(account_id)
        return self.accounts[account_id]

    async def update(self, account: Account) -> None:
        if account.id not in self.accounts:
            raise AccountNotFound(account.id)
        self.accounts[account.id] = account


class FakeIdentityRepository:
    def __init__(self):
        self.identities: list[AccountIdentity] = []

    async def add(self, identity: AccountIdentity) -> None:
        self.identities.append(identity)

    async def find(self, provider: str, identifier: str) -> AccountIdentity | None:
        return next(
            (i for i in self.identities if i.provider == provider and i.identifier == identifier),
            None,
        )


class FakeUnitOfWork:
    def __init__(self):
        self.accounts = FakeAccountRepository()
        self.identities = FakeIdentityRepository()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass


async def test_register_then_principal_resolves_account():
    uow = FakeUnitOfWork()
    service = AccountAuthService(uow)

    account, token = await service.register(email="Ada@Example.com", password="hunter2secret")
    assert token
    # Email is normalized and stored as a password identity, hashed (not plaintext).
    identity = uow.identities.identities[0]
    assert identity.identifier == "ada@example.com"
    assert identity.secret != "hunter2secret"

    principal = service.principal(token)
    assert principal.account_id == account.id


async def test_register_duplicate_email_rejected():
    uow = FakeUnitOfWork()
    service = AccountAuthService(uow)
    await service.register(email="ada@example.com", password="hunter2secret")
    with pytest.raises(EmailAlreadyRegistered):
        await service.register(email="ADA@example.com", password="another-pass")


async def test_login_with_correct_password_issues_token():
    uow = FakeUnitOfWork()
    service = AccountAuthService(uow)
    account, _ = await service.register(email="ada@example.com", password="hunter2secret")

    token = await service.login(email="ada@example.com", password="hunter2secret")
    assert service.principal(token).account_id == account.id


async def test_login_wrong_password_rejected():
    uow = FakeUnitOfWork()
    service = AccountAuthService(uow)
    await service.register(email="ada@example.com", password="hunter2secret")
    with pytest.raises(AuthenticationError):
        await service.login(email="ada@example.com", password="wrong-password")


async def test_login_unknown_email_rejected():
    uow = FakeUnitOfWork()
    service = AccountAuthService(uow)
    with pytest.raises(AuthenticationError):
        await service.login(email="nobody@example.com", password="whatever12")


async def test_principal_rejects_non_web_token():
    uow = FakeUnitOfWork()
    service = AccountAuthService(uow)
    with pytest.raises(AuthenticationError):
        service.principal("not-a-real-token")


async def test_recovery_pubkey_is_stored_on_the_account():
    uow = FakeUnitOfWork()
    service = AccountAuthService(uow)
    account, _ = await service.register(
        email="ada@example.com", password="hunter2secret", recovery_pubkey="age1recovery"
    )
    stored = await service.fetch_account(account.id)
    assert stored.recovery_pubkey == "age1recovery"


async def test_set_recovery_key_on_account_without_one():
    uow = FakeUnitOfWork()
    service = AccountAuthService(uow)
    account, _ = await service.register(email="ada@example.com", password="hunter2secret")
    assert account.recovery_pubkey is None

    updated = await service.set_recovery_key(account.id, "age1recovery")
    assert updated.recovery_pubkey == "age1recovery"
    assert (await service.fetch_account(account.id)).recovery_pubkey == "age1recovery"


async def test_set_recovery_key_is_write_once():
    uow = FakeUnitOfWork()
    service = AccountAuthService(uow)
    account, _ = await service.register(
        email="ada@example.com", password="hunter2secret", recovery_pubkey="age1first"
    )
    with pytest.raises(RecoveryKeyAlreadySet):
        await service.set_recovery_key(account.id, "age1second")
    # The original key is left untouched.
    assert (await service.fetch_account(account.id)).recovery_pubkey == "age1first"
