"""Web account endpoints — register, log in, read the current account.

This is the authority plane the webapp talks to. Registration and login return a
web session token (bearer) that identifies the account but holds no key. `/me`
is readable by either a web session or a device session, so the CLI can also read
the account's recovery public key.
"""

from fastapi import APIRouter, Depends, status

from gophkeeper.api.deps import get_account_id, provide
from gophkeeper.api.schemas.account import (
    AccountResponse,
    AccountSessionResponse,
    LoginRequest,
    RegisterAccountRequest,
)
from gophkeeper.services.account_auth_service import AccountAuthService
from gophkeeper.settings.settings import settings

router = APIRouter(prefix="/accounts", tags=["accounts"])

_TTL = settings.security.session_ttl_seconds


@router.post(
    "",
    response_model=AccountSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
    responses={409: {"description": "This email is already registered."}},
)
async def register_account(
    body: RegisterAccountRequest,
    service: AccountAuthService = Depends(provide(AccountAuthService)),
) -> AccountSessionResponse:
    """Create an account from an email + password, returning a web session token.

    Account creation lives on the web, not the CLI. An optional `recovery_pubkey`
    (minted in the browser) is stored as the account's recovery key; its private
    half never leaves the user.
    """
    _, token = await service.register(
        email=body.email,
        password=body.password,
        recovery_pubkey=body.recovery_pubkey,
    )
    return AccountSessionResponse(access_token=token, expires_in=_TTL)


@router.post(
    "/login",
    response_model=AccountSessionResponse,
    summary="Log in to an account",
    responses={401: {"description": "Invalid email or password."}},
)
async def login(
    body: LoginRequest,
    service: AccountAuthService = Depends(provide(AccountAuthService)),
) -> AccountSessionResponse:
    """Exchange email + password for a web session token."""
    token = await service.login(email=body.email, password=body.password)
    return AccountSessionResponse(access_token=token, expires_in=_TTL)


@router.get(
    "/me",
    response_model=AccountResponse,
    summary="Read the current account",
    responses={401: {"description": "Missing, invalid, or expired bearer token."}},
)
async def me(
    account_id=Depends(get_account_id),
    service: AccountAuthService = Depends(provide(AccountAuthService)),
) -> AccountResponse:
    """Return the caller's account, including its recovery public key.

    Accepts either a web session or a device session, so the CLI can read the
    recovery key it must seal secrets to.
    """
    account = await service.fetch_account(account_id)
    return AccountResponse(id=account.id, recovery_pubkey=account.recovery_pubkey)
