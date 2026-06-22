"""RS256 signing keys and JWKS for the auth service.

Loads an RSA keypair from configuration (PEM env vars or file paths). If none is
configured — typical for local dev — an ephemeral keypair is generated once at
process start so that RS256 signing and the ``/.well-known/jwks.json`` endpoint
work out of the box.

The API gateway (Envoy ``jwt_authn`` filter) fetches the public key from the
JWKS endpoint to validate access tokens at the edge.

NOTE: ephemeral keys change on every restart, invalidating previously-issued
tokens. For staging/production, supply a stable keypair via ``JWT_PRIVATE_KEY``
(PEM) or ``JWT_PRIVATE_KEY_PATH``.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import threading
from typing import Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

try:
    from core.config import settings
except ImportError:  # pragma: no cover - import path differs per runner
    from core.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_state: Optional[dict] = None


def _b64u_uint(value: int) -> str:
    """Base64url-encode an unsigned integer (JWK ``n``/``e`` form, no padding)."""
    length = (value.bit_length() + 7) // 8 or 1
    return base64.urlsafe_b64encode(value.to_bytes(length, "big")).rstrip(b"=").decode("ascii")


def _load_configured_keys() -> Tuple[Optional[bytes], Optional[bytes]]:
    """Return (private_pem, public_pem) from settings, or (None, None)."""
    priv = (settings.JWT_PRIVATE_KEY or "").strip()
    pub = (settings.JWT_PUBLIC_KEY or "").strip()
    if priv:
        return priv.encode(), (pub.encode() if pub else None)

    priv_path = (settings.JWT_PRIVATE_KEY_PATH or "").strip()
    pub_path = (settings.JWT_PUBLIC_KEY_PATH or "").strip()
    if priv_path:
        with open(priv_path, "rb") as fh:
            priv_b = fh.read()
        pub_b = None
        if pub_path:
            with open(pub_path, "rb") as fh:
                pub_b = fh.read()
        return priv_b, pub_b
    return None, None


def _load_or_create_cached_key():
    """Dev fallback: a keypair cached on disk so every worker process (and any
    helper process) shares ONE key — otherwise the JWKS endpoint and the token
    signer could disagree across forks."""
    path = (getattr(settings, "JWT_KEY_CACHE_PATH", "") or "/tmp/clan_auth_jwt_signing_key.pem").strip()
    try:
        with open(path, "rb") as fh:
            key = serialization.load_pem_private_key(fh.read(), password=None)
        logger.info("JWT RS256: loaded cached dev signing key (%s)", path)
        return key
    except FileNotFoundError:
        pass
    except Exception as exc:  # corrupt/unreadable -> regenerate
        logger.warning("JWT RS256: cached key unreadable (%s); regenerating", exc)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    try:
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "wb") as fh:
            fh.write(pem)
        os.replace(tmp, path)  # atomic publish
        logger.warning(
            "JWT RS256: generated dev signing key, cached at %s. "
            "Set JWT_PRIVATE_KEY / JWT_PRIVATE_KEY_PATH for production.", path,
        )
    except Exception as exc:
        logger.warning("JWT RS256: could not cache key (%s); using in-memory key", exc)
    return key


def _build_state() -> dict:
    configured_pem, _ = _load_configured_keys()
    if configured_pem:
        private_key = serialization.load_pem_private_key(configured_pem, password=None)
        logger.info("JWT RS256: loaded configured signing key")
    else:
        private_key = _load_or_create_cached_key()

    priv_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    der = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    # Stable, deterministic key id derived from the public key bytes.
    kid = base64.urlsafe_b64encode(hashlib.sha256(der).digest()).rstrip(b"=").decode("ascii")[:16]
    numbers = public_key.public_numbers()

    return {
        "private_pem": priv_pem.decode("ascii") if isinstance(priv_pem, bytes) else priv_pem,
        "public_pem": public_pem.decode("ascii"),
        "kid": kid,
        "jwk": {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": kid,
            "n": _b64u_uint(numbers.n),
            "e": _b64u_uint(numbers.e),
        },
    }


def _get_state() -> dict:
    global _state
    if _state is None:
        with _lock:
            if _state is None:
                _state = _build_state()
    return _state


def signing_key() -> Tuple[str, str]:
    """Return ``(private_pem, kid)`` for signing access/refresh tokens."""
    state = _get_state()
    return state["private_pem"], state["kid"]


def public_pem() -> str:
    """Return the PEM public key used to verify tokens locally."""
    return _get_state()["public_pem"]


def jwks() -> dict:
    """Return the JWKS document published at /.well-known/jwks.json."""
    return {"keys": [_get_state()["jwk"]]}
