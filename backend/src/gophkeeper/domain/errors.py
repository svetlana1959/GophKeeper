"""Domain errors — raised when a business rule is violated.

These are part of the domain's vocabulary and know nothing about HTTP. The API
layer maps them to status codes (see ``gophkeeper.api.errors``).
"""

from uuid import UUID


class DomainError(Exception):
    """Base class for all domain rule violations."""


class AuthenticationError(DomainError):
    """The caller failed to prove identity: unknown device, bad/expired token,
    or a failed challenge. Maps to 401."""


class InvalidInvite(DomainError):
    """The pairing code is unknown, already used, or expired. Maps to 400."""


class EmailAlreadyRegistered(DomainError):
    """An account identity with this provider + identifier already exists.
    Maps to 409."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"'{identifier}' is already registered")
        self.identifier = identifier


class AccountNotFound(DomainError):
    def __init__(self, account_id: UUID) -> None:
        super().__init__(f"account {account_id} not found")
        self.account_id = account_id


class SecretNotFound(DomainError):
    def __init__(self, secret_id: UUID) -> None:
        super().__init__(f"secret {secret_id} not found")
        self.secret_id = secret_id


class DeviceNotFound(DomainError):
    def __init__(self, device_id: UUID) -> None:
        super().__init__(f"device {device_id} not found")
        self.device_id = device_id


class DeviceAlreadyExists(DomainError):
    def __init__(self, device_id: UUID) -> None:
        super().__init__(f"device {device_id} already exists")
        self.device_id = device_id


class TrustCertConflict(DomainError):
    """A published trust cert's issuer_seq is not the next in the issuer's chain
    (a gap, duplicate, or rewind). The client must re-fetch the log and re-issue
    from the correct seq. Maps to 409."""

    def __init__(self, issuer_device_id: UUID, expected: int, actual: int) -> None:
        super().__init__(
            f"device {issuer_device_id}: trust cert expected seq {expected}, got {actual}"
        )
        self.issuer_device_id = issuer_device_id
        self.expected = expected
        self.actual = actual


class VersionConflict(DomainError):
    """Optimistic-concurrency guard: the client wrote against a stale version.

    The client must pull the current version, re-apply its change, and retry.
    """

    def __init__(self, secret_id: UUID, expected: int, actual: int) -> None:
        super().__init__(
            f"secret {secret_id}: write expected version {expected}, "
            f"but current version is {actual}"
        )
        self.secret_id = secret_id
        self.expected = expected
        self.actual = actual
