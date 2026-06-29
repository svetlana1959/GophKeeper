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

    This is checked on every ``fetch``/``update``/``store`` — it is unrelated
    to the access-request handshake below, which is the only way a device
    that does *not* yet have access can come to have it.
    """

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
    """A device may have only one outstanding PENDING request per secret.

    Mirrors the partial unique index on the ``access_requests`` table —
    checked here too so callers see the domain's own error, not a raw
    database constraint violation.
    """

    def __init__(self, secret_id: UUID, device_id: UUID) -> None:
        super().__init__(f"device {device_id} already has a pending request for secret {secret_id}")
        self.secret_id = secret_id
        self.device_id = device_id


class AccessRequestNotPending(DomainError):
    """Raised when approve()/reject() is called on a request already settled.

    Approval and rejection are one-way: once a request leaves PENDING it is
    history, not something to act on again.
    """

    def __init__(self, request_id: UUID, current_status: str) -> None:
        super().__init__(f"access request {request_id} is {current_status}, not PENDING")
        self.request_id = request_id
        self.current_status = current_status


class NotSecretOwner(DomainError):
    """Raised when a device that does not itself have access to a secret tries
    to act on requests for that secret (list/approve/reject).

    Only a device that can already decrypt a secret is in a position to
    re-encrypt it for someone else — a device with no access has no standing
    to manage who else gets it, mirroring the same rule the old direct-share
    flow enforced, just applied to the request queue instead.
    """

    def __init__(self, device_id: UUID, secret_id: UUID) -> None:
        super().__init__(f"device {device_id} does not own secret {secret_id}")
        self.device_id = device_id
        self.secret_id = secret_id
