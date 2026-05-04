from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"pbkdf2_sha256$120000${_b64url_encode(salt)}${_b64url_encode(digest)}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, iterations, salt_value, digest_value = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False

    salt = _b64url_decode(salt_value)
    expected = _b64url_decode(digest_value)
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        int(iterations),
    )
    return hmac.compare_digest(candidate, expected)


def create_access_token(
    claims: dict[str, Any],
    *,
    secret_key: str,
    ttl_seconds: int,
) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = dict(claims)
    payload["exp"] = int(time.time()) + ttl_seconds
    signing_input = ".".join(
        (
            _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        )
    )
    signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def decode_access_token(token: str, *, secret_key: str) -> dict[str, Any] | None:
    try:
        header_value, payload_value, signature_value = token.split(".", 2)
    except ValueError:
        return None

    signing_input = f"{header_value}.{payload_value}"
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        provided_signature = _b64url_decode(signature_value)
    except Exception:
        return None
    if not hmac.compare_digest(provided_signature, expected_signature):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_value))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def sign_payload(payload: dict[str, Any], *, secret_key: str) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(secret_key.encode("utf-8"), canonical, hashlib.sha256).digest()
    return _b64url_encode(signature)


def verify_payload_signature(payload: dict[str, Any], signature: str, *, secret_key: str) -> bool:
    expected = sign_payload(payload, secret_key=secret_key)
    return hmac.compare_digest(expected, signature)
