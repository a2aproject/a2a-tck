"""Verifier command for the card-sign runner, backed by the official a2a-python SDK (a2a-sdk).

    python tck/conformance/verifiers/a2a_python.py CARD.json JWKS.json

Exit status 0 means the SDK accepted the card's signature, 1 that it refused. The card is parsed the way an a2a-python
consumer parses one (``json_format.Parse`` into ``AgentCard``, unknown fields ignored) and handed to
``create_signature_verifier``; the key is resolved from the JWKS by ``kid``. Requires ``a2a-sdk``, which is not a TCK
dependency; the self-test workflow installs a pinned version.
"""

from __future__ import annotations

import json
import sys

from pathlib import Path

from a2a.types import AgentCard
from a2a.utils import signing
from google.protobuf import json_format
from jwt import PyJWK


def main(card_path: str, jwks_path: str) -> int:
    """Return 0 if a2a-sdk verifies the card at ``card_path`` against the keys at ``jwks_path``, else 1."""
    keys = json.loads(Path(jwks_path).read_text(encoding="utf-8"))["keys"]

    def key_provider(kid: str | None, _jku: str | None) -> PyJWK:
        for key in keys:
            if key["kid"] == kid:
                return PyJWK(key)
        raise ValueError("kid not in JWKS")

    card = json_format.Parse(Path(card_path).read_text(encoding="utf-8"), AgentCard(), ignore_unknown_fields=True)
    try:
        signing.create_signature_verifier(key_provider, ["ES256"])(card)
    except Exception:  # any refusal by the SDK is a reject verdict
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
