"""The authenticated caller of a request.

Two kinds of caller authenticate. A **device** proves it holds its age key (the
challenge flow) and gets a ``DevicePrincipal``. A **human on the web** proves an
account identity (password today) and gets an ``AccountPrincipal`` carrying just
``account_id`` — it holds no key and can decrypt nothing. Endpoints that only
need "which account" (e.g. minting an invite) accept either, so authorization
stays uniform.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DevicePrincipal:
    device_id: UUID
    account_id: UUID


@dataclass(frozen=True)
class AccountPrincipal:
    account_id: UUID
