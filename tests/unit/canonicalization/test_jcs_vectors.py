"""Agent Card canonicalization conformance tests driven by the a2a-jcs-v01 corpus.

Requirements tested:
    CARD-SIGN-001, CARD-SIGN-002

Specification Section 8.4.1 states two rules that are pure functions of the
Agent Card content, so both are decidable from a vector corpus without a
running server:

* rule 2, canonicalize the card per RFC 8785 -- CARD-SIGN-001, exercised by
  the A3, A4, A5 and A6 groups;
* rule 3, exclude the ``signatures`` field from the signed content --
  CARD-SIGN-002, exercised by the A2 group.

Each vector carries a disposition.  MUST-ACCEPT vectors pin the exact canonical
bytes; MUST-REJECT vectors pin input a conformant canonicalizer has to refuse.
The expected bytes were not written by hand -- every one is the agreed output
of two independent RFC 8785 implementations, so this module measures the TCK's
canonicalizer against outside work rather than against itself.

A MUST-REJECT vector also asserts *where* the refusal happened.  Malformed
input that never reaches the canonicalizer would let a canonicalizer that
refuses nothing at all pass the whole reject half of the corpus.
"""

from __future__ import annotations

import hashlib
import json

from pathlib import Path
from typing import Any

import pytest

from tck.canonicalization.jcs import (
    CanonicalizationError,
    assert_signatures_excluded,
    canonicalize,
    canonicalize_agent_card,
)
from tck.requirements.registry import get_requirement_by_id
from tck.requirements.tags import NOT_AUTOMATABLE


CORPUS_ROOT = Path(__file__).parent.parent.parent.parent / "conformance-vectors" / "a2a-jcs-v01"
MANIFEST_PATH = CORPUS_ROOT / "MANIFEST.json"

#: Clause marking the a2a-specific rule, as opposed to a plain RFC 8785 clause.
SIGNATURES_EXCLUSION_CLAUSE = "a2a-spec-8.4.1-rule-3"

#: Which requirement each vector group discharges.  Every group in the corpus
#: must appear here exactly once; ``test_every_group_is_claimed`` enforces it,
#: so a group added upstream cannot land silently unattributed.
GROUP_REQUIREMENTS = {
    "a2-signatures-exclusion": "CARD-SIGN-002",
    "a3-object-key-ordering": "CARD-SIGN-001",
    "a4-string-serialization": "CARD-SIGN-001",
    "a5-number-serialization": "CARD-SIGN-001",
    "a6-arrays-nesting-literals": "CARD-SIGN-001",
}

#: Requirements this corpus discharges, and which therefore must not carry the
#: ``not-automatable`` tag any more.
COVERED_REQUIREMENTS = sorted(set(GROUP_REQUIREMENTS.values()))


def _load_manifest() -> dict[str, Any]:
    """Read the corpus manifest."""
    manifest: dict[str, Any] = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return manifest


def _load_vectors() -> list[dict[str, Any]]:
    """Read every vector the manifest lists, in manifest order."""
    manifest = _load_manifest()
    vectors = []
    for entry in manifest["vectors"]:
        record = json.loads((CORPUS_ROOT / entry["path"]).read_text(encoding="utf-8"))
        record["_path"] = entry["path"]
        record["_group"] = entry["path"].split("/")[0]
        vectors.append(record)
    return vectors


MANIFEST = _load_manifest()
VECTORS = _load_vectors()

ACCEPT_VECTORS = [v for v in VECTORS if v["disposition"] == "MUST-ACCEPT"]
REJECT_VECTORS = [v for v in VECTORS if v["disposition"] == "MUST-REJECT"]


def _canonicalize_vector_input(vector: dict[str, Any]) -> bytes:
    """Canonicalize a MUST-ACCEPT vector's input the way its clause requires.

    Args:
        vector: The vector record.

    Returns:
        The canonical bytes produced by the TCK canonicalizer.
    """
    if vector["clause"] == SIGNATURES_EXCLUSION_CLAUSE:
        return canonicalize_agent_card(vector["input"])
    return canonicalize(vector["input"])


class TestCorpusIntegrity:
    """The corpus must be intact before any verdict drawn from it means anything."""

    def test_manifest_lists_every_vector_file_on_disk(self) -> None:
        """CARD-SIGN-001: the manifest accounts for every vector file present."""
        on_disk = {
            str(path.relative_to(CORPUS_ROOT))
            for path in CORPUS_ROOT.rglob("*.json")
            if path.name != "MANIFEST.json"
        }
        listed = {entry["path"] for entry in MANIFEST["vectors"]}
        assert on_disk == listed, (
            f"corpus and manifest disagree; only on disk: {sorted(on_disk - listed)}, "
            f"only in manifest: {sorted(listed - on_disk)}"
        )

    def test_every_vector_matches_its_recorded_hash(self) -> None:
        """CARD-SIGN-001: no vector file has been edited since the manifest was built."""
        mismatched = []
        for entry in MANIFEST["vectors"]:
            digest = hashlib.sha256((CORPUS_ROOT / entry["path"]).read_bytes()).hexdigest()
            if digest != entry["sha256"]:
                mismatched.append(f"{entry['path']}: got {digest}, manifest says {entry['sha256']}")
        assert not mismatched, "vector files altered since the manifest was built: " + "; ".join(mismatched)

    def test_corpus_digest_reproduces(self) -> None:
        """CARD-SIGN-001: the manifest body hashes to the digest it carries."""
        body = _load_manifest()
        stored = body.pop("corpusDigest")
        recomputed = hashlib.sha256(
            json.dumps(body, indent=2, sort_keys=False).encode("utf-8")
        ).hexdigest()
        assert recomputed == stored, f"manifest body hashes to {recomputed}, but it carries {stored}"

    def test_counts_match_the_manifest(self) -> None:
        """CARD-SIGN-001: the loaded vector counts match the manifest's own tally.

        A truncated corpus otherwise passes every remaining vector and reports
        a clean run, which is the one failure this whole module cannot survive.
        """
        counts = MANIFEST["counts"]
        assert len(VECTORS) == counts["total"]
        assert len(ACCEPT_VECTORS) == counts["accept"]
        assert len(REJECT_VECTORS) == counts["reject"]


class TestRequirementBinding:
    """The corpus groups and the requirement registry must stay in agreement."""

    def test_every_group_is_claimed(self) -> None:
        """CARD-SIGN-001: every corpus group is attributed to a requirement."""
        assert set(MANIFEST["groups"]) == set(GROUP_REQUIREMENTS)

    @pytest.mark.parametrize("requirement_id", COVERED_REQUIREMENTS)
    def test_covered_requirement_exists(self, requirement_id: str) -> None:
        """CARD-SIGN-001: each covered requirement resolves in the registry."""
        assert get_requirement_by_id(requirement_id).id == requirement_id

    @pytest.mark.parametrize("requirement_id", COVERED_REQUIREMENTS)
    def test_covered_requirement_is_not_tagged_not_automatable(self, requirement_id: str) -> None:
        """CARD-SIGN-001: a requirement this corpus tests is no longer not-automatable.

        This is the assertion that keeps the tag honest.  Restoring the
        ``not-automatable`` tag on a requirement these vectors exercise turns
        this test red rather than quietly re-hiding covered ground.
        """
        requirement = get_requirement_by_id(requirement_id)
        assert NOT_AUTOMATABLE not in requirement.tags, (
            f"{requirement_id} is exercised by the a2a-jcs-v01 corpus but is still "
            f"tagged {NOT_AUTOMATABLE!r}"
        )

    @pytest.mark.parametrize("requirement_id", COVERED_REQUIREMENTS)
    def test_covered_requirement_has_vectors(self, requirement_id: str) -> None:
        """CARD-SIGN-001: each covered requirement actually has vectors behind it."""
        groups = {group for group, req in GROUP_REQUIREMENTS.items() if req == requirement_id}
        owned = [v for v in VECTORS if v["_group"] in groups]
        assert owned, f"{requirement_id} claims groups {sorted(groups)} but no vector loaded from them"


class TestMustAcceptVectors:
    """Every MUST-ACCEPT vector pins exact canonical bytes."""

    @pytest.mark.parametrize("vector", ACCEPT_VECTORS, ids=lambda v: v["id"])
    def test_canonical_bytes_match(self, vector: dict[str, Any]) -> None:
        """CARD-SIGN-001: canonicalization produces the corpus's expected bytes.

        The A2 group vectors additionally cover CARD-SIGN-002, since their
        expected bytes are only reachable once the ``signatures`` field has
        been excluded.
        """
        expected = bytes.fromhex(vector["expected"]["canonical_utf8_hex"])
        produced = _canonicalize_vector_input(vector)
        assert produced == expected, (
            f"{vector['id']} ({vector['clause']}): canonicalization produced "
            f"{produced!r}, corpus expects {expected!r}. {vector['rationale']}"
        )

    @pytest.mark.parametrize("vector", ACCEPT_VECTORS, ids=lambda v: v["id"])
    def test_canonical_bytes_are_valid_utf8(self, vector: dict[str, Any]) -> None:
        """CARD-SIGN-001: canonical output decodes as UTF-8, as RFC 8785 requires."""
        _canonicalize_vector_input(vector).decode("utf-8")


class TestMustRejectVectors:
    """Every MUST-REJECT vector pins input a conformant canonicalizer refuses."""

    @pytest.mark.parametrize(
        "vector",
        [v for v in REJECT_VECTORS if v["clause"] != SIGNATURES_EXCLUSION_CLAUSE],
        ids=lambda v: v["id"],
    )
    def test_canonicalizer_refuses(self, vector: dict[str, Any]) -> None:
        """CARD-SIGN-001: the canonicalizer refuses input that has no canonical form.

        The refusal has to come from the canonicalizer.  ``json.loads`` accepts
        every one of these inputs -- lone surrogate escapes become real lone
        surrogates and ``NaN``/``Infinity`` become real floats -- so a refusal
        raised at parse time would mean the canonicalizer was never asked.
        """
        parsed = json.loads(vector["input_raw"])
        with pytest.raises(CanonicalizationError):
            canonicalize(parsed)

    @pytest.mark.parametrize(
        "vector",
        [v for v in REJECT_VECTORS if v["clause"] == SIGNATURES_EXCLUSION_CLAUSE],
        ids=lambda v: v["id"],
    )
    def test_signatures_field_is_detected_in_signing_input(self, vector: dict[str, Any]) -> None:
        """CARD-SIGN-002: a signing payload still carrying ``signatures`` is refused.

        These vectors present already-canonical bytes that were signed without
        the exclusion applied.  The field's presence is the whole defect, and
        it must be detected whether the array is populated or empty.
        """
        parsed = json.loads(vector["input_raw"])
        with pytest.raises(CanonicalizationError):
            assert_signatures_excluded(parsed)
