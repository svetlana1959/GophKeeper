"""Application service for device enrollment.

create_invite mints a single-use pairing code (only its hash is stored). join
validates a presented code and admits the new device into the invite's account.
The code authorizes the join; resharing the account's secrets to the new device
happens on a key-holding device's next sync.
"""

import hashlib
import secrets as randbytes
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from gophkeeper.domain.device import ACTIVE, Device
from gophkeeper.domain.errors import DeviceAlreadyExists, InvalidInvite
from gophkeeper.domain.invite import Invite
from gophkeeper.domain.unit_of_work import UnitOfWork
from gophkeeper.settings.settings import settings

# 24 bytes of token_urlsafe is ~192 bits of entropy, so the code is
# unguessable and a plain (unsalted) SHA-256 lookup is safe: there is nothing to
# brute-force and the DB does an indexed equality match, not an in-app compare,
# so there's no timing surface. Do not shorten this without revisiting the hash.
_CODE_BYTES = 24


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


class EnrollmentService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create_invite(self, *, account_id: UUID) -> tuple[Invite, str]:
        """Create an invite and return it with the plaintext code (shown once)."""
        code = randbytes.token_urlsafe(_CODE_BYTES)
        expires_at = datetime.now(UTC) + timedelta(seconds=settings.security.invite_ttl_seconds)
        invite = Invite(
            id=uuid4(),
            account_id=account_id,
            code_hash=_hash_code(code),
            expires_at=expires_at,
        )
        async with self._uow as uow:
            await uow.invites.add(invite)
            await uow.commit()
        return invite, code

    async def join(self, *, code: str, device_name: str, public_key: str) -> Device:
        """Admit a device into the invite's account, consuming the invite."""
        async with self._uow as uow:
            invite = await uow.invites.find_by_code_hash(_hash_code(code))
            if invite is None or not invite.is_valid():
                raise InvalidInvite("invalid or expired invite code")

            existing = await uow.devices.find_by_public_key(public_key)
            if existing is not None:
                raise DeviceAlreadyExists(existing.id)

            device = Device(
                id=uuid4(),
                account_id=invite.account_id,
                device_name=device_name,
                public_key=public_key,
                status=ACTIVE,
            )
            await uow.devices.add(device)
            invite.consume()
            if not await uow.invites.consume(invite):
                # Another concurrent join consumed the code first; the device add
                # above rolls back with the transaction.
                raise InvalidInvite("invalid or expired invite code")
            await uow.commit()
            return device
