"""Replay the opt-in TCK profile against its installed native source reader."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import subprocess
import zipfile

from pathlib import Path
from typing import Any

from tck.validators.history_boundary_corpus import (
    SELECTED_MANIFEST_SHA256,
    load_history_boundary_corpus,
    project_native_history_case,
    replay_history_boundary_corpus,
)


def verify_source(profile: Path, manifest: dict[str, Any]) -> None:
    """Bind the original public source fixture, pins and recorded reader bytes."""
    expected = manifest["source"]
    fields = {
        "native-fixture.zip": "fixtureSha256",
        "consumer-pins.json": "consumerPinsSha256",
        "recorded-report.json": "recordedReportSha256",
    }
    for name, field in fields.items():
        if hashlib.sha256((profile / "results" / name).read_bytes()).hexdigest() != expected[field]:
            raise ValueError(f"Native source {name} digest differs")


def extract_packet(profile: Path, output: Path) -> Path:
    """Extract the selected ZIP while refusing duplicates, links and unsafe paths."""
    packet = output / "native-packet"
    packet.mkdir()
    with zipfile.ZipFile(profile / "results" / "native-fixture.zip") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Native source ZIP contains duplicate names")
        for entry in archive.infolist():
            safe_member(entry)
            archive.extract(entry, packet)
    return packet


def safe_member(entry: zipfile.ZipInfo) -> None:
    """Require ordinary bounded relative ZIP members from the selected packet."""
    path = Path(entry.filename)
    if path.is_absolute() or ".." in path.parts or entry.is_dir():
        raise ValueError("Native source ZIP member path differs")
    if stat.S_ISLNK(entry.external_attr >> 16):
        raise ValueError("Native source ZIP cannot contain symlinks")


def run_reader(profile: Path, reader: Path, packet: Path, output: Path) -> None:
    """Execute the separately installed reader with bounded time and full streams."""
    command = [
        str(reader.resolve(strict=True)),
        str(packet.resolve()),
        "--pins-file",
        str((profile / "results" / "consumer-pins.json").resolve()),
    ]
    (output / "reader-command.json").write_text(json.dumps({"command": command, "timeoutSeconds": 15}, indent=2) + "\n")
    with (output / "reader.stdout").open("wb") as stdout, (output / "reader.stderr").open("wb") as stderr:
        result = subprocess.run(command, check=False, timeout=15, stdout=stdout, stderr=stderr)
    (output / "reader-returncode.json").write_text(json.dumps({"returncode": result.returncode}) + "\n")
    if result.returncode != 0:
        raise ValueError("Installed native reader refused source packet")
    if (output / "reader.stdout").read_bytes() != (profile / "results" / "recorded-report.json").read_bytes():
        raise ValueError("Installed native reader output differs from original")


def verify_projection(directory: Path, packet: Path) -> None:
    """Recompute every portable row from the reader-verified original case bytes."""
    rows = load_history_boundary_corpus(directory, manifest_sha256=SELECTED_MANIFEST_SHA256)
    for row in rows:
        original = (packet / "cases" / (row["id"] + ".json")).read_bytes()
        projected = project_native_history_case(original, case_id=row["id"])
        if json.dumps(projected, sort_keys=True) != json.dumps(row, sort_keys=True):
            raise ValueError(f"Portable projection differs: {row['id']}")


def replay(directory: Path, profile: Path, reader: Path, output: Path) -> dict[str, Any]:
    """Bind source bytes, independently replay native evidence, then run TCK APIs."""
    output.mkdir(parents=True, exist_ok=False)
    try:
        load_history_boundary_corpus(directory, manifest_sha256=SELECTED_MANIFEST_SHA256)
        manifest = json.loads((directory / "manifest.json").read_bytes())
        verify_source(profile, manifest)
        packet = extract_packet(profile, output)
        run_reader(profile, reader, packet, output)
        verify_projection(directory, packet)
        report = replay_history_boundary_corpus(directory, manifest_sha256=SELECTED_MANIFEST_SHA256)
        if not report["passed"]:
            raise ValueError("TCK history boundary corpus refused")
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        (output / "failure.json").write_text(json.dumps({"status": "refused", "reason": str(error)}) + "\n")
        raise
    report["sourceBinding"] = "installed-native-reader-and-exact-projection"
    report["nativeReaderScope"] = "PEER"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    """Select public source/installed reader and retain one fresh replay directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus", type=Path, default=Path(__file__).resolve().parents[1] / "conformance-vectors" / "a2a-history-boundary-v01"
    )
    parser.add_argument("--observer-profile", type=Path, required=True)
    parser.add_argument("--reader", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = replay(args.corpus, args.observer_profile, args.reader, args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
