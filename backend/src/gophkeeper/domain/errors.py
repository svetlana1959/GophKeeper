"""Domain errors — raised when a business rule is violated.

These are part of the domain's vocabulary and know nothing about HTTP. The API
layer maps them to status codes (see ``gophkeeper.api.errors``).
"""
from uuid import UUID

class DomainError(Exception):
    """Base class for all domain rule violations."""


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


class AccessDenied(DomainError):
    """Raised when a device that is not trusted for a secret tries to use it.

    Covers issue #69's "untrusted device -> access denied" criterion.
    ``secret_id`` is ``None`` for the device-level case (the device itself is
    unknown or deactivated, before any specific secret comes into it).
    """

    def __init__(self, device_id: UUID, secret_id: UUID | None = None) -> None:
        if secret_id is None:
            super().__init__(f"device {device_id} is not trusted")
        else:
            super().__init__(f"device {device_id} has no access to secret {secret_id}")
        self.device_id = device_id
        self.secret_id = secret_id
