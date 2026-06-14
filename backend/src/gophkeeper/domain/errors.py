"""Domain errors — raised when a business rule is violated.

These are part of the domain's vocabulary and know nothing about HTTP. The API
layer maps them to status codes (see ``gophkeeper.api.errors``).
"""


class DomainError(Exception):
    """Base class for all domain rule violations."""


class SecretNotFound(DomainError):
    def __init__(self, secret_id: str) -> None:
        super().__init__(f"secret {secret_id!r} not found")
        self.secret_id = secret_id

class DeviceNotFound(DomainError):
    def __init__(self, device_id: str) -> None:
        super().__init__(f"device {device_id!r} not found")
        self.device_id = device_id


class VersionConflict(DomainError):
    """Optimistic-concurrency guard: the client wrote against a stale version.

    The client must pull the current version, re-apply its change, and retry.
    """

    def __init__(self, secret_id: str, expected: int, actual: int) -> None:
        super().__init__(
            f"secret {secret_id!r}: write expected version {expected}, "
            f"but current version is {actual}"
        )
        self.secret_id = secret_id
        self.expected = expected
        self.actual = actual
