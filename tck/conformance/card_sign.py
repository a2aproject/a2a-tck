"""Offline runner for the a2a-card-sign-v01 vectors (Agent Card signatures, spec section 8.4).

CARD-SIGN-001 and CARD-SIGN-002 are marked NOT_AUTOMATABLE against a running SUT: a server never shows which bytes it
signed. They can be tested offline instead, by handing a verifier signed cards whose covered bytes are recorded and
checking which ones it accepts. This module does that for conformance-vectors/a2a-card-sign-v01:

* ``check_corpus`` validates the corpus itself: every file matches its sha256 in MANIFEST.json, every expectation is
  well formed, every recorded canonical form is RFC 8785 output, and every signature verifies over the bytes its vector
  says it covers (MUST-REJECT vectors: it does not verify over the bytes a verifier would compute). It needs no
  third-party package; ES256 is verified with a small P-256 implementation below.
* ``score`` reports, per reading, how many vectors a verifier gets right and how many signatures it accepts that the
  reading rejects. Readings are scored per group: s0 to s2 together, s3 (``"axis": "unknown-fields"``) and s4
  (``"axis": "dual-name"``) in their own tables. s4 is labelled against a sentence proposed on a2aproject/A2A#2122,
  not against the specification text, so accepting a dual-name card under that reading counts as a divergence, not a
  false accept. S4-REJECT-005 is rejected under every reading, so accepting it is a false accept in both s4 columns.

Run a verifier over every vector::

    uv run python -m tck.conformance.card_sign --verifier "node verify.mjs {card} {jwks}"

The command is run once per vector with ``{card}`` replaced by a file holding the served card and ``{jwks}`` by the
corpus test key set; exit status 0 means the verifier accepted the card. ``--verdicts file.json`` scores recorded
verdicts instead (``{"verdicts": {"S0-001": true, ...}}``). ``--require READING`` exits 1 unless the verifier gets every
vector of that reading right with no false accepts. ``--no-false-accepts READING`` exits 1 only if the verifier accepts a
vector that reading rejects, so an SDK's own CI can stop a regression such as accepting S4-REJECT-005 without first
adopting a reading for the rest of the corpus. Either gate also fails when the verifier rejects a MUST-ACCEPT control,
since a verifier that cannot run rejects everything and would otherwise pass a false-accept gate.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shlex
import subprocess
import sys
import tempfile

from pathlib import Path


CORPUS = Path(__file__).resolve().parents[2] / "conformance-vectors" / "a2a-card-sign-v01"

TABLES: list[tuple[str, str | None, list[str]]] = [
    (
        "s0 to s2",
        None,
        [
            "rule-1-served-scope",
            "rule-1-descriptor-scope",
            "prune-empty",
            "served-as-is",
            "field-level-prune",
            "rule-1-element-collapse",
        ],
    ),
    ("s3 unknown fields", "unknown-fields", ["unknown-retain", "unknown-exclude", "unknown-reject"]),
    ("s4 dual names (labelled against a proposal)", "dual-name", ["dual-name-tolerate", "dual-name-refuse"]),
]
PROPOSAL_READINGS = {"dual-name-refuse"}
# S1-009 and S1-010 carry an array element that becomes empty (securityRequirements: [{}]). Two readings differ only there,
# and the corpus names them on that pair alone: field-level-prune removes empty field values but never an element, and
# rule-1-element-collapse applies rule 1 (served scope) after removing elements that become empty. On every other vector
# they read as the reading they refine. refuse-empty-element (the strict verifier reading of the signer sentence widened on
# a2aproject/A2A#2122) rejects both vectors of the pair and is not a column: it says nothing about other cards.
ELEMENT_ALIASES = {"field-level-prune": "prune-empty", "rule-1-element-collapse": "rule-1-served-scope"}
KNOWN_READINGS = {r for _, _, rs in TABLES for r in rs} | {"rule-1-as-written", "refuse-empty-element"}

# --- ES256 (ECDSA P-256 with SHA-256), verification only -------------------------------------------------------------

_P = 2**256 - 2**224 + 2**192 + 2**96 - 1
_A = _P - 3
_B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
_SIG_LEN = 64
_G = (0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296, 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5)


def _add(p1: tuple[int, int] | None, p2: tuple[int, int] | None) -> tuple[int, int] | None:
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    if p1[0] == p2[0] and (p1[1] + p2[1]) % _P == 0:
        return None
    if p1 == p2:
        lam = (3 * p1[0] * p1[0] + _A) * pow(2 * p1[1], -1, _P) % _P
    else:
        lam = (p2[1] - p1[1]) * pow(p2[0] - p1[0], -1, _P) % _P
    x = (lam * lam - p1[0] - p2[0]) % _P
    return x, (lam * (p1[0] - x) - p1[1]) % _P


def _mul(k: int, point: tuple[int, int]) -> tuple[int, int] | None:
    acc: tuple[int, int] | None = None
    add: tuple[int, int] | None = point
    while k:
        if k & 1:
            acc = _add(acc, add)
        add = _add(add, add)
        k >>= 1
    return acc


def _b64u(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def es256_verify(jwk: dict, protected: str, payload: bytes, signature: str) -> bool:
    """True if ``signature`` (raw r || s, base64url) verifies over the JWS signing input for ``payload``."""
    x, y = int.from_bytes(_b64u(jwk["x"]), "big"), int.from_bytes(_b64u(jwk["y"]), "big")
    if (y * y - (x * x * x + _A * x + _B)) % _P:
        return False
    raw = _b64u(signature)
    if len(raw) != _SIG_LEN:
        return False
    r, s = int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")
    if not (0 < r < _N and 0 < s < _N):
        return False
    signing_input = (protected + "." + base64.urlsafe_b64encode(payload).rstrip(b"=").decode()).encode()
    e = int.from_bytes(hashlib.sha256(signing_input).digest(), "big")
    w = pow(s, -1, _N)
    point = _add(_mul(e * w % _N, _G), _mul(r * w % _N, (x, y)))
    return point is not None and point[0] % _N == r


# --- corpus ----------------------------------------------------------------------------------------------------------


def load(corpus: Path = CORPUS) -> tuple[dict, list[dict]]:
    """MANIFEST.json and every vector it lists, in MANIFEST order."""
    manifest = json.loads((corpus / "MANIFEST.json").read_text(encoding="utf-8"))
    return manifest, [json.loads((corpus / v["path"]).read_text(encoding="utf-8")) for v in manifest["vectors"]]


def _is_jcs(data: bytes) -> bool:
    # The corpus holds no floating-point numbers, so RFC 8785 output equals sorted keys, no whitespace, raw UTF-8.
    try:
        obj = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return False
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") == data


def check_corpus(corpus: Path = CORPUS) -> list[str]:
    """Problems found in the corpus; an empty list means it is consistent."""
    problems: list[str] = []
    manifest = json.loads((corpus / "MANIFEST.json").read_text(encoding="utf-8"))
    jwk = json.loads((corpus / "testkey_jwks.json").read_text(encoding="utf-8"))["keys"][0]
    if len(manifest["vectors"]) != manifest["counts"]["total"]:
        problems.append("MANIFEST counts.total does not match the number of vectors")
    seen: set[str] = set()
    for entry in manifest["vectors"]:
        raw = (corpus / entry["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            problems.append(entry["path"] + ": sha256 differs from MANIFEST")
            continue
        doc = json.loads(raw)
        vid = doc["id"]
        if vid in seen:
            problems.append(vid + ": duplicate id")
        seen.add(vid)
        acc, rej = set(doc["accept_under"]), set(doc["reject_under"])
        if acc & rej or not (acc | rej) <= KNOWN_READINGS:
            problems.append(vid + ": accept_under / reject_under overlap or name an unknown reading")
        if doc["disposition"] == "MUST-REJECT" and acc:
            problems.append(vid + ": MUST-REJECT vector lists readings that accept it")
        sigs = doc["served_card"].get("signatures") or []
        payloads = [bytes.fromhex(h) for h in doc.get("canonical_utf8_hex_per_signature") or [doc["canonical_utf8_hex"]]]
        if not sigs or len(payloads) != len(sigs):
            problems.append(vid + ": signatures and recorded payloads do not pair up")
            continue
        for sig, payload in zip(sigs, payloads, strict=True):
            if not _is_jcs(payload):
                problems.append(vid + ": recorded canonical bytes are not RFC 8785 output")
            if b'"signatures"' in payload:
                problems.append(vid + ": recorded canonical bytes include the signatures member (CARD-SIGN-002)")
            ok = es256_verify(jwk, sig["protected"], payload, sig["signature"])
            if doc["disposition"] == "MUST-REJECT" and ok:
                problems.append(vid + ": reject vector verifies over the bytes a verifier computes")
            if doc["disposition"] != "MUST-REJECT" and not ok:
                problems.append(vid + ": signature does not cover its recorded bytes")
    return problems


def expected(doc: dict, reading: str) -> bool:
    """True if ``reading`` accepts the vector; rule-1-as-written stands for both rule 1 scopes.

    An element reading the vector does not name reads as the reading it refines (``ELEMENT_ALIASES``).
    """
    accept = set(doc["accept_under"])
    if reading in ELEMENT_ALIASES and reading not in accept | set(doc["reject_under"]):
        reading = ELEMENT_ALIASES[reading]
    if "rule-1-as-written" in accept:
        accept |= {"rule-1-served-scope", "rule-1-descriptor-scope"}
    return reading in accept


def score(docs: list[dict], verdicts: dict[str, bool]) -> list[tuple[str, dict[str, dict[str, int]]]]:
    """Per table, per reading: right, of, false_accepts, divergences, false_rejects over the vectors in ``verdicts``."""
    out = []
    for title, axis, readings in TABLES:
        group = [d for d in docs if d.get("axis") == axis and d["id"] in verdicts]
        if not group:
            continue
        table = {}
        for r in readings:
            right = fa = div = fr = 0
            for d in group:
                want, got = expected(d, r), bool(verdicts[d["id"]])
                right += want == got
                # Under a proposal reading, accepting a card that only the proposal rejects is a divergence; accepting a
                # MUST-REJECT card is a false accept under every reading.
                if got and not want and r in PROPOSAL_READINGS and d["disposition"] != "MUST-REJECT":
                    div += 1
                else:
                    fa += got and not want
                fr += want and not got
            table[r] = {"right": right, "of": len(group), "false_accepts": fa, "divergences": div, "false_rejects": fr}
        out.append((title, table))
    return out


def run_verifier(template: str, docs: list[dict], corpus: Path = CORPUS, timeout: float = 60) -> dict[str, bool]:
    """Run ``template`` once per vector; exit status 0 is an accept."""
    verdicts = {}
    jwks = str(corpus / "testkey_jwks.json")
    with tempfile.TemporaryDirectory() as tmp:
        for d in docs:
            card = Path(tmp) / (d["id"] + ".json")
            card.write_text(json.dumps(d["served_card"], ensure_ascii=False), encoding="utf-8")
            cmd = [part.replace("{card}", str(card)).replace("{jwks}", jwks) for part in shlex.split(template)]
            verdicts[d["id"]] = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False).returncode == 0
    return verdicts


def render(tables: list[tuple[str, dict[str, dict[str, int]]]]) -> str:
    """Plain-text tables; acceptances under a proposal reading are printed as divergences."""
    lines = []
    for title, table in tables:
        lines.append(title)
        for reading, s in table.items():
            line = f"  {reading:<26} {s['right']:>3}/{s['of']:<3} false accepts {s['false_accepts']}"
            if reading in PROPOSAL_READINGS:
                line += f", divergences {s['divergences']}"
            lines.append(line)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point; exit 0 pass, 1 a ``--require`` reading not met, 2 corpus inconsistent."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--verifier", help='command template, e.g. "node verify.mjs {card} {jwks}"; exit 0 = accept')
    src.add_argument("--verdicts", type=Path, help='JSON file {"verdicts": {"S0-001": true, ...}}')
    ap.add_argument("--require", action="append", default=[], help="exit 1 unless conformant to this reading")
    ap.add_argument(
        "--no-false-accepts",
        action="append",
        default=[],
        metavar="READING",
        help="exit 1 if the verifier accepts any vector this reading rejects (false rejects and divergences do not fail)",
    )
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--json-out", type=Path, help="also write the verdicts, tables and gate outcome to this JSON file")
    args = ap.parse_args(argv)
    problems = check_corpus(args.corpus)
    if problems:
        print("corpus inconsistent:\n  " + "\n  ".join(problems))
        return 2
    _, docs = load(args.corpus)
    if not args.verifier and not args.verdicts:
        print(f"corpus consistent: {len(docs)} vectors, every signature covers its recorded bytes")
        return 0
    if args.verifier:
        verdicts = run_verifier(args.verifier, docs, args.corpus)
    else:
        verdicts = json.loads(args.verdicts.read_text(encoding="utf-8"))["verdicts"]
    tables = score(docs, verdicts)
    print(render(tables))
    # A verifier that cannot run rejects everything, which no false-accept gate notices. Every reading accepts the
    # MUST-ACCEPT controls, so a gated run fails when any of them is rejected.
    controls_rejected = [d["id"] for d in docs if d["disposition"] == "MUST-ACCEPT" and d["id"] in verdicts and not verdicts[d["id"]]]
    if controls_rejected:
        print("verifier rejected vectors every reading accepts (" + ", ".join(controls_rejected) + "): check that it runs")
    failed = [r for r in args.require for _, t in tables if r in t and (t[r]["right"] != t[r]["of"] or t[r]["false_accepts"])]
    failed += [r for r in args.no_false_accepts for _, t in tables if r in t and t[r]["false_accepts"]]
    unknown = [r for r in args.require + args.no_false_accepts if not any(r in t for _, t in tables)]
    if unknown:
        print("unknown reading: " + ", ".join(unknown))
    if args.json_out:
        manifest_sha = hashlib.sha256((args.corpus / "MANIFEST.json").read_bytes()).hexdigest()
        report = {
            "runner": "tck.conformance.card_sign",
            "corpus": {"vectors": len(docs), "manifest_sha256": manifest_sha},
            "source": "verifier" if args.verifier else "verdicts",
            "verdicts": verdicts,
            "tables": [{"title": title, "readings": table} for title, table in tables],
            "gates": {
                "require": args.require,
                "no_false_accepts": args.no_false_accepts,
                "failed": failed,
                "unknown": unknown,
                "controls_rejected": controls_rejected,
            },
        }
        args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    gated = bool(args.require or args.no_false_accepts)
    return 1 if failed or unknown or (gated and controls_rejected) else 0


if __name__ == "__main__":
    sys.exit(main())
