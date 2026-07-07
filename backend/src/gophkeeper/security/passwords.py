"""Password hashing adapter.

Isolates argon2 behind two functions so the rest of the app never imports the
library directly. argon2id with the library defaults is a memory-hard,
salt-per-hash scheme; the salt and parameters are embedded in the returned
string, so ``verify`` needs only the stored hash.
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return an argon2id hash (salt + params embedded) for storage."""
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Report whether ``password`` matches ``hashed``. False on any mismatch."""
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False
