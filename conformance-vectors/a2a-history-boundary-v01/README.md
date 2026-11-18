# Provisional JSON-RPC caller/history application profile

This opt-in profile checks two declared outcomes of a history-retaining
application through the TCK's public `JsonRpcResponse`, history extractor and
`InternalError` binding. It adds no `RequirementSpec`, conformance severity or
automatic live-SUT test. TCK adoption remains a maintainer decision. The existing
canonicalization contribution in #228 has separate scope and ownership.

The current TCK maps history persistence to `CORE-HIST-004` at **MAY** level.
The vendored specification's §3.2.4 defines requested history length; §3.3.2
requires appropriate errors, and §9.5 maps JSON-RPC `InternalError` to `-32603`.
Those statements do not mandate durable persistence for every implementation or
absence after every failed send. This profile's stronger application boundary
is selected explicitly, including complete store readback and these exact
controlled conflict outcomes.

| Selected case | Native outcome | Application assertion |
| --- | --- | --- |
| Ten `accepted-retry` cases | One competing unchanged commit makes the first native CAS stale; the unchanged native consumer retries and returns a Task | The exact submitted follow-up occurs once after prior history and the prior agent status message; the caller Task equals committed readback |
| Ten `rejected-absent` cases | Two competing unchanged commits exhaust the native saves; native `InternalError` reaches the caller | JSON-RPC code, message and native ErrorInfo details are preserved; the selected rejected follow-up is absent and committed Task content remains unchanged |

The original measurements are from [Observer #46](https://github.com/probityai/agent-evidence-observer/pull/46),
using SDK `52030cf43f2e96d25949952e385e3b73fe93bc2a` and actual MySQL 8.0.46.
The native SDK handlers, versioned stores, ASGI JSON-RPC dispatcher, protobuf
Task readback and separate SQL connection execute in that source profile.
Its observer workflow pins the MySQL OCI digest and enforces finite resources.
The trace is unsigned same-operator instrumentation. Python SDK #1303 changed
an integration assertion, not runtime code; its author's 300 repetitions remain
separate evidence.

`corpus.json` contains deterministic projections of all twenty original native
case receipts. `manifest.json` pins the corpus, source-case bytes, original ZIP,
consumer pins, recorded reader report, source revisions and measured substrate.
The raw send reply is an actual wire response. Before/after Task objects are
original native store observations adapted for the TCK API; they do not become
new network GetTask observations. Replaying this contribution runs no new model,
database, concurrency schedule or inference.

Run the ordinary TCK checks:

```sh
uv sync --extra dev
make lint unit-test
```

For complete native-source binding, obtain the exact public Observer source and
normally install its framework-free reader in a separate Python 3.12 environment:

```sh
git clone https://github.com/probityai/agent-evidence-observer.git /tmp/a2a-history-observer
git -C /tmp/a2a-history-observer checkout 2c131b84f72cc8e54b95af0a9124509be72914ff
python3.12 -m venv /tmp/a2a-history-reader
/tmp/a2a-history-reader/bin/python -m pip install \
  /tmp/a2a-history-observer/interop/a2a-history-boundary-2026-10-02
uv run python scripts/replay_history_boundary.py \
  --observer-profile /tmp/a2a-history-observer/interop/a2a-history-boundary-2026-10-02 \
  --reader /tmp/a2a-history-reader/bin/probity-read-a2a-history \
  --output /tmp/a2a-history-tck-replay-001
```

Use a fresh output directory. The script authenticates selected source files,
executes the separately installed reader with a 15-second bound, retains both
streams, requires exact original report bytes, reproduces every portable row
from original case bytes, and runs the TCK validator over all twenty rows.
Failed runs retain `failure.json`; no partial population reports success.
The source reader joins exact native protobuf/SQL/CAS/source bytes without
importing the SDK, SQLAlchemy, HTTPX, Starlette or a running database.

The tests include source population/digest controls, request/task/context joins,
native error details, missing/duplicated/changed history and correlated
reply/readback tampering, with Hypothesis coverage for request identifiers and
changed submitted payloads. All scope remains **PEER**: no independent custody,
network server process, production authentication, models, all concurrency
schedules, normative TCK adoption, producer acceptance or recurring adoption.

The proposed integration question is whether the TCK wants this reusable,
opt-in application-profile shape. A future live-SUT adapter would need declared
conflict controls and independent complete persisted readback; a normal protocol
error alone cannot supply either assumption.
