"""Application service for web account authentication.

This is the *authority* plane: a human proves they own an account with a login
identity (email + password today) and receives a stateless web session token
carrying only ``account_id``. It holds no age key and can decrypt nothing — its
sole power is to act as the account (e.g. mint a device invite).

Modeled around ``AccountIdentity`` so new methods (OAuth, …) are added as new
providers, not new branches here: register/login resolve an identity by
``(provider, identifier)`` and this service stays password-specific only in the
one place that hashes/verifies a secret.
"""

from uuid import UUID, uuid4

from gophkeeper.domain.account import Account
from gophkeeper.domain.errors import (
    AuthenticationError,
    EmailAlreadyRegistered,
    RecoveryKeyAlreadySet,
)
from gophkeeper.domain.identity import PASSWORD, AccountIdentity
from gophkeeper.domain.unit_of_work import UnitOfWork
from gophkeeper.security import passwords, tokens
from gophkeeper.security.principal import AccountPrincipal
from gophkeeper.settings.settings import settings

_WEB_TYP = "web"


def _normalize_email(email: str) -> str:
    return email.strip().lower()


class AccountAuthService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    @property
    def _secret(self) -> bytes:
        return settings.security.secret_key.encode()

    async def register(
        self, *, email: str, password: str, recovery_pubkey: str | None = None
    ) -> tuple[Account, str]:
        """Create an account with a password identity, returning it and a token.

        The recovery public key is stored as given (the browser mints the pair
        and keeps the private half); it is never required here.
        """
        identifier = _normalize_email(email)
        async with self._uow as uow:
            if await uow.identities.find(PASSWORD, identifier) is not None:
                raise EmailAlreadyRegistered(identifier)

            account = Account(id=uuid4(), recovery_pubkey=recovery_pubkey)
            await uow.accounts.add(account)
            await uow.identities.add(
                AccountIdentity(
                    id=uuid4(),
                    account_id=account.id,
                    provider=PASSWORD,
                    identifier=identifier,
                    secret=passwords.hash_password(password),
                )
            )
            await uow.commit()
        return account, self._issue(account.id)

    async def login(self, *, email: str, password: str) -> str:
        """Verify a password identity and return a web session token."""
        identifier = _normalize_email(email)
        async with self._uow as uow:
            identity = await uow.identities.find(PASSWORD, identifier)
        if identity is None or identity.secret is None:
            raise AuthenticationError("invalid email or password")
        if not passwords.verify_password(password, identity.secret):
            raise AuthenticationError("invalid email or password")
        return self._issue(identity.account_id)

    async def fetch_account(self, account_id: UUID) -> Account:
        """Return the account (e.g. to read its recovery public key)."""
        async with self._uow as uow:
            return await uow.accounts.get(account_id)

    async def set_recovery_key(self, account_id: UUID, recovery_pubkey: str) -> Account:
        """Set the account's recovery public key, once.

        The recovery key is write-once: its private half only ever lived in the
        user's browser, so overwriting the public half would strand every secret
        already sealed to the old key. If one is set, this refuses (409).
        """
        async with self._uow as uow:
            account = await uow.accounts.get(account_id)
            if account.recovery_pubkey is not None:
                raise RecoveryKeyAlreadySet(account_id)
            account.recovery_pubkey = recovery_pubkey
            await uow.accounts.update(account)
            await uow.commit()
        return account

    def principal(self, token: str) -> AccountPrincipal:
        """Resolve a web session token to its account principal."""
        try:
            payload = tokens.verify(token, secret=self._secret)
        except tokens.TokenError as exc:
            raise AuthenticationError(str(exc)) from exc
        if payload.get("typ") != _WEB_TYP:
            raise AuthenticationError("expected a web session token")
        return AccountPrincipal(account_id=UUID(payload["aid"]))

    def _issue(self, account_id: UUID) -> str:
        return tokens.sign(
            {"typ": _WEB_TYP, "aid": str(account_id)},
            secret=self._secret,
            ttl_seconds=settings.security.session_ttl_seconds,
        )
