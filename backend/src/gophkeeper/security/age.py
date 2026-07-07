"""age encryption — the one cryptographic operation the server performs.

The server only ever *encrypts to* a device's public key (to issue a login
challenge). It never holds a private key and never decrypts. This thin wrapper
isolates the pyrage dependency so the rest of the code talks in bytes.
"""

from pyrage import encrypt, x25519


class InvalidPublicKey(ValueError):
    """The supplied string is not a valid age (X25519) recipient."""


def encrypt_to(public_key: str, plaintext: bytes) -> bytes:
    """Encrypt ``plaintext`` to an age public key (``age1...``).

    Raises ``InvalidPublicKey`` if the key cannot be parsed.
    """
    try:
        recipient = x25519.Recipient.from_str(public_key)
    except Exception as exc:  # pyrage raises a bare exception on bad input
        raise InvalidPublicKey(public_key) from exc
    return encrypt(plaintext, [recipient])
