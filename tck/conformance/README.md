# Offline conformance runners

## Agent Card signatures: `card_sign.py`

Runs a verifier over the a2a-card-sign-v01 vectors (`conformance-vectors/a2a-card-sign-v01`) and scores it against
each reading of specification section 8.4. CARD-SIGN-001 and CARD-SIGN-002 are `NOT_AUTOMATABLE` against a running SUT;
this tests them offline, against a verifier instead of a server. Standard library only.

```
python -m tck.conformance.card_sign                                   # check the corpus itself
python -m tck.conformance.card_sign --verifier "node verify.mjs {card} {jwks}" --no-false-accepts dual-name-refuse
python -m tck.conformance.card_sign --verdicts verdicts.json --json-out report.json
```

- `--verifier` runs the command once per vector; `{card}` is a file holding the served card, `{jwks}` the corpus test key
  set, and exit status 0 means accept.
- `--no-false-accepts READING` fails only when the verifier accepts a vector that reading rejects.
- `--require READING` fails unless the verifier gets every vector of that reading right.
- Either gate also fails when the verifier rejects a MUST-ACCEPT control, so a verifier that cannot run does not pass.
- Divergences from a proposed reading (s4 `dual-name-refuse`) are reported and never fail a gate; accepting
  S4-REJECT-005 is a false accept under both s4 readings.

`verifiers/a2a_python.py` is a ready verifier command for the official a2a-python SDK (`a2a-sdk`).

## In an SDK's CI: `.github/workflows/card-sign-vectors.yml`

A reusable workflow. An SDK repository calls it with its own verifier command:

```yaml
jobs:
  card-sign:
    uses: a2aproject/a2a-tck/.github/workflows/card-sign-vectors.yml@<a2a-tck commit>
    with:
      tck-ref: <the same a2a-tck commit>
      node-version: "22"
      setup: npm ci && npm run build
      verifier: node scripts/verify-card.mjs {card} {jwks}
```

The `verifier` job runs the vectors and keeps `card-sign-report.json` (verdicts, tables, gate outcome). By default it
gates on false accepts under both s4 readings and on rejected controls. The `probity` job runs the pinned Probity reader
(probityai/agent-evidence-vectors, an independently written consumer) on its declared s3 and s4 subsets and keeps its
fresh report beside the SDK's. `card-sign-vectors-selftest.yml` calls the workflow on this repository with a2a-sdk 1.2.1.
