"""Reference canonicalization vectors for AgentCard signing (CARD-SIGN-001, CARD-SIGN-002).

These cases do not exercise a SUT and do not change the NOT_AUTOMATABLE status of the
CARD-SIGN requirements. They give the kit known-good RFC 8785 (JCS) canonical signing
payloads so a canonicalization implementation can be checked against fixed bytes:

  CARD-SIGN-001 (spec 8.4.1): the signing payload is the AgentCard canonicalized per RFC 8785
  CARD-SIGN-002 (spec 8.4.1): the signatures field is excluded from the signing payload

Vectors come from card_ref (github.com/chopmob-cloud/AlgoVoi-A2A-Card) and the
algovoi-jcs-conformance-vectors corpus set card_ref_v1. Apache-2.0.
"""
from __future__ import annotations

import json

from pathlib import Path

import pytest


rfc8785 = pytest.importorskip("rfc8785")

_VECTORS = json.loads((Path(__file__).with_name("card_signing_canonicalization_vectors.json")).read_text(encoding="utf-8"))


def _jcs_signing_payload(card: dict) -> str:
    # spec 8.4.2: exclude the signatures field, then RFC 8785 (JCS)
    prepared = {k: v for k, v in card.items() if k != "signatures"}
    return rfc8785.dumps(prepared).decode("utf-8")


@pytest.mark.parametrize("case", _VECTORS["cases"], ids=lambda c: c["id"])
def test_agent_card_signing_payload_is_jcs_without_signatures(case: dict) -> None:
    """The JCS signing payload equals the expected canonical bytes with the signatures field excluded."""
    payload = _jcs_signing_payload(case["agent_card"])
    assert payload == case["expected_jcs_payload"], (
        f"{case['id']} ({case['requirement']}): canonical signing payload mismatch"
    )
