"""Application service for device enrollment.

The inviter (client) generates the pairing code and uploads only its hash plus a
roster of its trusted devices, each MAC'd under the code — the server never sees
the code. join validates a presented code hash, admits the new device, and
records the join MAC so the inviter can later verify who redeemed the code and
vouch for it. See docs/sync_design.md §11.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from gophkeeper.domain.device import ACTIVE, Device
from gophkeeper.domain.errors import DeviceAlreadyExists, InvalidInvite, InviteNotFound
from gophkeeper.domain.invite import Invite
from gophkeeper.domain.unit_of_work import UnitOfWork
from gophkeeper.settings.settings import settings


class EnrollmentService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create_invite(self, *, account_id: UUID, code_hash: str, roster_json: str) -> Invite:
        """Store a client-generated invite (code hash + MAC'd roster).

        The plaintext code never reaches the server; the inviter shows it once.
        """
        expires_at = datetime.now(UTC) + timedelta(seconds=settings.security.invite_ttl_seconds)
        invite = Invite(
            id=uuid4(),
            account_id=account_id,
            code_hash=code_hash,
            expires_at=expires_at,
            roster_json=roster_json,
        )
        async with self._uow as uow:
            await uow.invites.add(invite)
            await uow.commit()
        return invite

    async def join(
        self,
        *,
        code_hash: str,
        device_name: str,
        public_key: str,
        sign_public_key: str,
        join_mac: str,
    ) -> tuple[Device, str]:
        """Admit a device, consuming the invite. Returns the device and the
        inviter's MAC'd roster (for the joiner to adopt as anchors)."""
        async with self._uow as uow:
            invite = await uow.invites.find_by_code_hash(code_hash)
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
                sign_public_key=sign_public_key,
                status=ACTIVE,
            )
            await uow.devices.add(device)
            invite.join_mac = join_mac
            invite.joined_device_id = device.id
            invite.consume()
            if not await uow.invites.consume(invite):
                # Another concurrent join consumed the code first; the device add
                # above rolls back with the transaction.
                raise InvalidInvite("invalid or expired invite code")
            await uow.commit()
            return device, invite.roster_json

    async def join_proof(
        self, *, account_id: UUID, invite_id: UUID
    ) -> tuple[Invite, Device | None]:
        """Return an invite the caller's account owns and the device that redeemed
        it (None if not yet consumed), so the inviter can verify the join MAC."""
        async with self._uow as uow:
            invite = await uow.invites.find_by_id(invite_id)
            if invite is None or invite.account_id != account_id:
                raise InviteNotFound(invite_id)
            device = None
            if invite.joined_device_id is not None:
                device = await uow.devices.get(invite.joined_device_id)
            return invite, device
