"""Verifier command for the card-sign runner: the ``field-level-prune`` reading, no SDK imported.

    python tck/conformance/verifiers/field_level_prune.py CARD.json JWKS.json

Exit status 0 means this reading accepts the card's signature, 1 that it refuses. The reading is the one named in
``conformance-vectors/a2a-card-sign-v01/README.md``:

* the covered bytes are the served card without its ``signatures``, with empty field values (``""``, ``[]``, ``{}``)
  removed recursively and array elements kept even when they become empty -- so a card carrying
  ``securityRequirements: [{}]`` is read as served (S1-009) and not as its pruned form (S1-010), which is the pair
  that names this reading;
* RFC 8785 over those bytes;
* unknown fields are kept as served, and a card carrying the same schema field under both its JSON name and its
  protobuf name is refused, the reading proposed on a2aproject/A2A#2122.

Nothing is imported from an SDK or from the corpus generator: the covered bytes are built here from the served JSON,
and the signature is checked over exactly those bytes with ``cryptography`` (the one package this command needs).
"""

from __future__ import annotations

import base64
import json
import re
import sys

from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils


def snake(name: str) -> str:
    """The protobuf (snake_case) spelling of a JSON (lowerCamelCase) field name."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


SIG_LEN = 64  # r || s, 32 bytes each, as JWS ES256 spells a signature


def is_empty(value: object) -> bool:
    """True for the three empty values the reading removes: ``""``, ``[]`` and ``{}``."""
    return value in ("", [], {})


def prune(node: object) -> object:
    """Remove empty field values recursively. An element of an array is never removed, however it reads."""
    if isinstance(node, dict):
        out = {}
        for key, raw in node.items():
            member = prune(raw)
            if is_empty(member):
                continue
            out[key] = member
        return out
    if isinstance(node, list):
        return [prune(element) for element in node]
    return node


def dual_named(node: object) -> bool:
    """True when an object carries one schema field under both its JSON name and its protobuf name."""
    if isinstance(node, dict):
        keys = set(node)
        if any(key != snake(key) and snake(key) in keys for key in keys):
            return True
        return any(dual_named(value) for value in node.values())
    if isinstance(node, list):
        return any(dual_named(element) for element in node)
    return False


def jcs(node: object) -> bytes:
    """RFC 8785: object members sorted by UTF-16 code unit, no insignificant whitespace."""
    if isinstance(node, dict):
        members = sorted(node.items(), key=lambda item: item[0].encode("utf-16-be"))
        body = ",".join(f"{json.dumps(k, ensure_ascii=False)}:{jcs(v).decode('utf-8')}" for k, v in members)
        return ("{" + body + "}").encode("utf-8")
    if isinstance(node, list):
        return ("[" + ",".join(jcs(v).decode("utf-8") for v in node) + "]").encode("utf-8")
    return json.dumps(node, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def b64u(value: str) -> bytes:
    """Base64url-decode without padding, as JWS spells its parts."""
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def verifies(jwk: dict, protected: str, payload: bytes, signature: str) -> bool:
    """ES256 over ``protected.payload`` with the JWK's P-256 public key."""
    try:
        public = ec.EllipticCurvePublicNumbers(
            int.from_bytes(b64u(jwk["x"]), "big"), int.from_bytes(b64u(jwk["y"]), "big"), ec.SECP256R1()
        ).public_key()
        raw = b64u(signature)
        if len(raw) != SIG_LEN:
            return False
        signing_input = (protected + "." + base64.urlsafe_b64encode(payload).rstrip(b"=").decode()).encode("utf-8")
        public.verify(
            utils.encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")),
            signing_input,
            ec.ECDSA(hashes.SHA256()),
        )
        return True
    except Exception:  # any failure to verify is a refusal
        return False


def main(card_path: str, jwks_path: str) -> int:
    """Return 0 if a signature on the served card verifies over the bytes this reading covers, else 1."""
    card = json.loads(Path(card_path).read_text(encoding="utf-8"))
    if dual_named(card):
        return 1
    covered = prune({key: value for key, value in card.items() if key != "signatures"})
    payload = jcs(covered)
    keys = json.loads(Path(jwks_path).read_text(encoding="utf-8"))["keys"]
    for signature in card.get("signatures") or []:
        try:
            header = json.loads(b64u(signature["protected"]))
        except Exception:
            continue
        if header.get("alg") != "ES256":
            continue
        jwk = next((key for key in keys if key.get("kid") == header.get("kid")), None)
        if jwk is not None and verifies(jwk, signature["protected"], payload, signature["signature"]):
            return 0
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
