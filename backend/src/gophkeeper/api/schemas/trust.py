"""Trust-log DTOs.

TrustCertBody mirrors the CLI's trust.Cert wire shape (see cli/internal/trust).
The server treats it as an opaque signed blob: it reads only kind, issuer_id, and
seq for structural checks and stores the whole thing verbatim.
"""

from pydantic import BaseModel, Field


class TrustCertBody(BaseModel):
    kind: str = Field(description="'vouch' or 'revoke'.")
    account_id: str = Field(description="Account the cert belongs to.")
    issuer_id: str = Field(description="Device id that signed the cert.")
    seq: int = Field(description="Issuer's monotonic per-cert counter (contiguous).")
    prev_hash: str = Field(default="", description="Chain link to the issuer's previous cert.")
    subject_id: str = Field(default="", description="Vouch: the admitted device id.")
    subject_enc_pub: str = Field(default="", description="Vouch: the subject's age public key.")
    subject_sign_pub: str = Field(default="", description="Vouch: the subject's signing key.")
    target_id: str = Field(default="", description="Revoke: the removed device id.")
    issued_at: int = Field(description="Unix seconds.")
    sig: str = Field(description="Base64 Ed25519 signature over the cert's canonical form.")


class TrustChangesResponse(BaseModel):
    certs: list[TrustCertBody]
    cursor: int = Field(description="New high-water log cursor to pass as `since` next time.")
