"""Example domain test — pure, no database, no FastAPI.

Because the invariants live on the aggregate, they are tested in isolation. This
is the payoff of keeping the domain free of infrastructure.
"""

import pytest

from gophkeeper.domain.errors import DomainError, VersionConflict
from gophkeeper.domain.secret import Secret


def _make() -> Secret:
    return Secret(id="s1", account_id="a1", ciphertext=b"v1")


def test_update_bumps_version_and_replaces_ciphertext():
    secret = _make()
    secret.update(b"v2", base_version=1)
    assert secret.version == 2
    assert secret.ciphertext == b"v2"


def test_update_rejects_stale_write():
    secret = _make()
    with pytest.raises(VersionConflict):
        secret.update(b"v2", base_version=0)


def test_delete_is_idempotent():
    secret = _make()
    secret.delete()
    version_after_delete = secret.version
    secret.delete()
    assert secret.deleted is True
    assert secret.is_active is False
    assert secret.version == version_after_delete


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": ""},
        {"account_id": ""},
        {"ciphertext": b""},
        {"version": 0},
    ],
)
def test_construction_rejects_invalid_state(kwargs):
    valid = {"id": "s1", "account_id": "a1", "ciphertext": b"v1"}
    with pytest.raises(DomainError):
        Secret(**{**valid, **kwargs})


def test_update_rejects_empty_ciphertext():
    secret = _make()
    with pytest.raises(DomainError):
        secret.update(b"", base_version=1)
