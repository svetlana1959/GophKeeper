"""Domain errors."""

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
    """Raised when the client writes against a stale version."""

    def __init__(self, secret_id: UUID, expected: int, actual: int) -> None:
        super().__init__(
            f"secret {secret_id}: write expected version {expected}, "
            f"but current version is {actual}"
        )
        self.secret_id = secret_id
        self.expected = expected
        self.actual = actual


class AccessDenied(DomainError):
    """Raised when a device is not trusted for an operation."""

    def __init__(self, device_id: UUID, secret_id: UUID | None = None) -> None:
        if secret_id is None:
            super().__init__(f"device {device_id} is not trusted")
        else:
            super().__init__(f"device {device_id} has no access to secret {secret_id}")
        self.device_id = device_id
        self.secret_id = secret_id


class AccessRequestNotFound(DomainError):
    def __init__(self, request_id: UUID) -> None:
        super().__init__(f"access request {request_id} not found")
        self.request_id = request_id


class AccessRequestAlreadyPending(DomainError):
    """Raised when a pending request already exists."""

    def __init__(self, secret_id: UUID, device_id: UUID) -> None:
        super().__init__(f"device {device_id} already has a pending request for secret {secret_id}")
        self.secret_id = secret_id
        self.device_id = device_id


class AccessRequestNotPending(DomainError):
    """Raised when a settled request is approved or rejected again."""

    def __init__(self, request_id: UUID, current_status: str) -> None:
        super().__init__(f"access request {request_id} is {current_status}, not PENDING")
        self.request_id = request_id
        self.current_status = current_status


class NotSecretOwner(DomainError):
    """Raised when a device cannot manage requests for a secret."""

    def __init__(self, device_id: UUID, secret_id: UUID) -> None:
        super().__init__(f"device {device_id} does not own secret {secret_id}")
        self.device_id = device_id
        self.secret_id = secret_id
