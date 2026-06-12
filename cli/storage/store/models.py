"""
Domain models for the local encrypted store.

All fields that could contain secret material are stored as ciphertext (bytes).
Plaintext NEVER appears in these models or on disk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TrustedDevice:
    """One row in the trusted_devices table.

    Represents either the local device or a remote peer.
    """

    id: str                        # Device UUID (generated on init or received from server)
    device_name: str               # Human-readable label, e.g. "laptop-arsenez"
    public_key: str                # AGE public key (age1…)
    is_active: bool = True         # False when the device has been revoked
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LocalDevice:
    """Extension row in local_device (1:1 with TrustedDevice).

    ``private_key_encrypted`` holds either:
    - An Argon2id/scrypt-derived, PIN-encrypted blob when the user set a PIN during init.
    - The raw AGE private key when no PIN was set (file permissions 0o600 are the guard).

    Either way, callers must decrypt/unwrap before use and must never log or re-persist
    the plaintext result.
    """

    device_id: str                  # FK → trusted_devices.id
    private_key_encrypted: bytes    # AGE private key at rest
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Secret:
    """One row in the secrets table.

    The actual secret content lives only in ``encrypted_payload`` (a JSON blob encrypted
    with ChaCha20-Poly1305 or AES-GCM).  ``nonce`` is stored alongside so the payload
    can be decrypted when the caller has obtained the DEK via SecretRecipient.
    """

    id: str                        # UUID — matches server-side ID
    encrypted_payload: bytes       # Encrypted JSON blob
    nonce: bytes                   # Cryptographic nonce for the AEAD cipher
    folder_id: str = ""            # Optional categorisation / group
    version: int = 1               # Monotonically increasing; used for conflict detection
    is_deleted: bool = False       # Soft-delete / tombstone flag
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SecretRecipient:
    """One row in the secret_recipients junction table.

    Each row holds a copy of the Data-Encryption Key (DEK) that was used to encrypt
    the corresponding Secret, itself wrapped asymmetrically with the device's AGE
    public key so only that device can unwrap it.
    """

    secret_id: str      # FK → secrets.id
    device_id: str      # FK → trusted_devices.id
    encrypted_dek: bytes  # DEK wrapped with device AGE key (X25519/age)
