"""The authenticated caller of a request.

Today only a device authenticates (via the age challenge). A future web login
will add an ``AccountPrincipal`` carrying just ``account_id``; endpoints depend on
the union so authorization checks stay uniform.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DevicePrincipal:
    device_id: UUID
    account_id: UUID
