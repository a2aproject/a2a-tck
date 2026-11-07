"""Tests for the offline runner of the a2a-card-sign-v01 vectors."""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import sys

from typing import TYPE_CHECKING

import pytest

from tck.conformance import card_sign


if TYPE_CHECKING:
    from pathlib import Path


CORPUS = card_sign.CORPUS


@pytest.fixture(scope="module")
def docs() -> list[dict]:
    """All vectors, in MANIFEST order."""
    return card_sign.load()[1]


def _by_id(docs: list[dict], vid: str) -> dict:
    return next(d for d in docs if d["id"] == vid)


def test_corpus_is_consistent() -> None:
    """Every file matches MANIFEST and every signature covers the bytes its vector records."""
    assert card_sign.check_corpus() == []


def test_corpus_counts(docs: list[dict]) -> None:
    """MANIFEST counts every vector and the three scoring axes are all present."""
    manifest = card_sign.load()[0]
    assert len(docs) == manifest["counts"]["total"]
    assert {d.get("axis") for d in docs} == {None, "unknown-fields", "dual-name"}


def test_es256_verifies_a_corpus_signature_and_rejects_one_changed_byte(docs: list[dict]) -> None:
    """The P-256 verifier accepts a corpus signature and refuses one changed payload or signature byte."""
    jwk = json.loads((CORPUS / "testkey_jwks.json").read_text(encoding="utf-8"))["keys"][0]
    doc = _by_id(docs, "S0-001")
    sig = doc["served_card"]["signatures"][0]
    payload = bytes.fromhex(doc["canonical_utf8_hex"])
    assert card_sign.es256_verify(jwk, sig["protected"], payload, sig["signature"])
    assert not card_sign.es256_verify(jwk, sig["protected"], payload.replace(b"text/plain", b"text/plaiN"), sig["signature"])
    raw = bytearray(base64.urlsafe_b64decode(sig["signature"] + "=="))
    raw[-1] ^= 1
    flipped = base64.urlsafe_b64encode(bytes(raw)).rstrip(b"=").decode()
    assert not card_sign.es256_verify(jwk, sig["protected"], payload, flipped)


def test_es256_rejects_a_point_off_the_curve(docs: list[dict]) -> None:
    """A public key that is not on P-256 never verifies."""
    jwk = dict(json.loads((CORPUS / "testkey_jwks.json").read_text(encoding="utf-8"))["keys"][0])
    jwk["y"] = jwk["x"]
    doc = _by_id(docs, "S0-001")
    sig = doc["served_card"]["signatures"][0]
    assert not card_sign.es256_verify(jwk, sig["protected"], bytes.fromhex(doc["canonical_utf8_hex"]), sig["signature"])


def test_check_corpus_reports_a_tampered_vector(tmp_path: Path) -> None:
    """A changed vector is caught by its sha256, and again by its signature once the sha256 is updated."""
    corpus = tmp_path / "corpus"
    shutil.copytree(CORPUS, corpus)
    manifest = json.loads((corpus / "MANIFEST.json").read_text(encoding="utf-8"))
    entry = manifest["vectors"][0]
    path = corpus / entry["path"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["canonical_utf8_hex"] = doc["canonical_utf8_hex"].replace("74657874", "54657874", 1)
    data = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode()
    path.write_bytes(data)
    assert any("sha256 differs" in p for p in card_sign.check_corpus(corpus))
    entry["sha256"] = hashlib.sha256(data).hexdigest()
    (corpus / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert any("does not cover its recorded bytes" in p for p in card_sign.check_corpus(corpus))


def test_rule_1_as_written_counts_for_both_scopes() -> None:
    """A vector accepted under rule-1-as-written is expected to pass under both rule 1 scopes."""
    doc = {"accept_under": ["rule-1-as-written"], "reject_under": []}
    assert card_sign.expected(doc, "rule-1-served-scope")
    assert card_sign.expected(doc, "rule-1-descriptor-scope")
    assert not card_sign.expected(doc, "prune-empty")


def test_an_honest_verifier_for_each_reading_scores_full_marks(docs: list[dict]) -> None:
    """A verifier that follows one reading exactly gets every vector of that reading right."""
    for _, _, readings in card_sign.TABLES:
        for reading in readings:
            verdicts = {d["id"]: card_sign.expected(d, reading) for d in docs}
            for _, table in card_sign.score(docs, verdicts):
                if reading in table:
                    s = table[reading]
                    assert (s["right"], s["false_accepts"], s["false_rejects"]) == (s["of"], 0, 0)


def test_accepting_everything_is_scored_as_false_accepts(docs: list[dict]) -> None:
    """Accepting every card counts one false accept per vector the reading rejects."""
    tables = dict(card_sign.score(docs, dict.fromkeys((d["id"] for d in docs), True)))
    s0 = tables["s0 to s2"]["rule-1-served-scope"]
    assert s0["false_accepts"] == sum(1 for d in docs if d.get("axis") is None and not card_sign.expected(d, "rule-1-served-scope"))
    assert s0["false_accepts"] > 0


def test_s4_acceptance_is_labelled_a_divergence(docs: list[dict]) -> None:
    """Under the proposed dual-name-refuse reading, accepting a dual-name card is reported as a divergence."""
    s4 = [d for d in docs if d.get("axis") == "dual-name"]
    verdicts = {d["id"]: d["id"] != "S4-REJECT-005" for d in s4}
    dual = sum(1 for d in s4 if "dual-name-refuse" in d["reject_under"] and d["disposition"] != "MUST-REJECT")
    tables = card_sign.score(docs, verdicts)
    ((title, table),) = tables
    assert title.startswith("s4")
    assert table["dual-name-tolerate"]["false_accepts"] == 0
    assert (table["dual-name-refuse"]["false_accepts"], table["dual-name-refuse"]["divergences"]) == (0, dual)
    assert f"false accepts 0, divergences {dual}" in card_sign.render(tables)


def test_accepting_s4_reject_005_is_a_false_accept_in_both_s4_columns(docs: list[dict]) -> None:
    """S4-REJECT-005 is rejected under every reading, so accepting it is never just a divergence."""
    verdicts = {d["id"]: d["id"] == "S4-REJECT-005" for d in docs if d.get("axis") == "dual-name"}
    ((_, table),) = card_sign.score(docs, verdicts)
    assert table["dual-name-tolerate"]["false_accepts"] == 1
    assert (table["dual-name-refuse"]["false_accepts"], table["dual-name-refuse"]["divergences"]) == (1, 0)


def test_s4_reject_005_is_rejected_under_every_reading(docs: list[dict]) -> None:
    """A protobuf-name member added after signing is rejected under both s4 readings."""
    doc = _by_id(docs, "S4-REJECT-005")
    assert doc["disposition"] == "MUST-REJECT"
    assert not any(card_sign.expected(doc, r) for r in ("dual-name-tolerate", "dual-name-refuse"))
    assert "default_input_modes" in doc["served_card"]


def test_main_scores_recorded_verdicts_and_enforces_require(docs: list[dict], tmp_path: Path) -> None:
    """The CLI exits 1 when a required reading is not met or unknown, 0 when it is met."""
    verdicts = tmp_path / "v.json"
    reading = "rule-1-served-scope"
    honest = {d["id"]: card_sign.expected(d, reading) or d["disposition"] == "MUST-ACCEPT" for d in docs}
    verdicts.write_text(json.dumps({"verdicts": honest}), encoding="utf-8")
    assert card_sign.main(["--verdicts", str(verdicts), "--require", reading, "--require", "unknown-exclude"]) == 1
    assert card_sign.main(["--verdicts", str(verdicts), "--require", reading]) == 0
    assert card_sign.main(["--verdicts", str(verdicts), "--require", "no-such-reading"]) == 1


def test_main_runs_a_verifier_command(docs: list[dict], tmp_path: Path) -> None:
    """The CLI runs a verifier command per vector and reads exit status 0 as an accept."""
    script = tmp_path / "accept_s0.py"
    script.write_text(
        "import json, sys\ncard = json.load(open(sys.argv[1]))\nsys.exit(0 if 'default_input_modes' not in card else 1)\n",
        encoding="utf-8",
    )
    verdicts = card_sign.run_verifier(f"{sys.executable} {script} {{card}} {{jwks}}", docs)
    assert verdicts["S0-001"] is True
    assert verdicts["S4-REJECT-005"] is False
    assert card_sign.main([]) == 0


def test_no_false_accepts_fails_only_on_false_accepts(docs: list[dict], tmp_path: Path) -> None:
    """--no-false-accepts ignores false rejects and divergences but fails on an accepted MUST-REJECT card."""
    s4 = {d["id"]: d for d in docs if d.get("axis") == "dual-name"}
    strict = {vid: vid == "S4-004" for vid in s4}
    loose = {**strict, "S4-REJECT-005": True}
    for name, verdicts, want in (("strict", strict, 0), ("loose", loose, 1)):
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps({"verdicts": verdicts}), encoding="utf-8")
        for reading in ("dual-name-tolerate", "dual-name-refuse"):
            assert card_sign.main(["--verdicts", str(path), "--no-false-accepts", reading]) == want
    assert card_sign.main(["--verdicts", str(tmp_path / "strict.json"), "--require", "dual-name-tolerate"]) == 1


def test_json_out_records_verdicts_tables_and_gates(docs: list[dict], tmp_path: Path) -> None:
    """--json-out writes what was scored and why the run passed or failed, for a CI job to retain."""
    verdicts = {d["id"]: card_sign.expected(d, "rule-1-served-scope") or d["disposition"] == "MUST-ACCEPT" for d in docs}
    src = tmp_path / "v.json"
    src.write_text(json.dumps({"verdicts": verdicts}), encoding="utf-8")
    out = tmp_path / "report.json"
    assert card_sign.main(["--verdicts", str(src), "--no-false-accepts", "dual-name-refuse", "--json-out", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["corpus"]["vectors"] == len(docs)
    assert report["verdicts"] == verdicts
    assert [t["title"] for t in report["tables"]] == [title for title, _, _ in card_sign.TABLES]
    assert report["gates"] == {
        "require": [],
        "no_false_accepts": ["dual-name-refuse"],
        "failed": [],
        "unknown": [],
        "controls_rejected": [],
    }


def test_a_verifier_that_rejects_everything_fails_a_gated_run(docs: list[dict], tmp_path: Path) -> None:
    """A broken verifier rejects every card; the MUST-ACCEPT controls make a gated run fail instead of pass."""
    src = tmp_path / "v.json"
    src.write_text(json.dumps({"verdicts": dict.fromkeys((d["id"] for d in docs), False)}), encoding="utf-8")
    assert card_sign.main(["--verdicts", str(src)]) == 0
    assert card_sign.main(["--verdicts", str(src), "--no-false-accepts", "dual-name-refuse"]) == 1


def test_element_pair_names_its_readings(docs: list[dict]) -> None:
    """S1-009 keeps the empty element, S1-010 collapses it; refuse-empty-element rejects both; every reading accepts one."""
    by_id = {d["id"]: d for d in docs}
    s9, s10 = by_id["S1-009"], by_id["S1-010"]
    assert s9["served_card"]["securityRequirements"] == [{}] == s10["served_card"]["securityRequirements"]
    assert "refuse-empty-element" in s9["reject_under"] and "refuse-empty-element" in s10["reject_under"]
    for _, axis, readings in card_sign.TABLES:
        if axis is None:
            for r in readings:
                assert card_sign.expected(s9, r) != card_sign.expected(s10, r), r


def test_field_level_prune_agrees_with_prune_empty_except_on_the_element_pair(docs: list[dict]) -> None:
    """A reader that only checks empty fields scores like prune-empty everywhere but S1-009 and S1-010."""
    differ = [
        d["id"]
        for d in docs
        if d.get("axis") is None and card_sign.expected(d, "field-level-prune") != card_sign.expected(d, "prune-empty")
    ]
    assert differ == ["S1-009", "S1-010"]
    differ = [
        d["id"]
        for d in docs
        if d.get("axis") is None
        and card_sign.expected(d, "rule-1-element-collapse") != card_sign.expected(d, "rule-1-served-scope")
    ]
    assert differ == ["S1-009", "S1-010"]
