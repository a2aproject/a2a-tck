"""Keep the executable error bindings aligned with the vendored specification."""

from __future__ import annotations

from pathlib import Path

from tck.requirements.base import ERROR_BINDINGS


_SPEC_PATH = Path(__file__).resolve().parents[3] / "specification" / "specification.md"
_MAPPING_HEADING = "### 5.4. Error Code Mappings"
_MAPPING_END = "**Custom Binding Requirements:**"
_MAPPING_COLUMN_COUNT = 4


def _spec_error_bindings() -> dict[str, tuple[int, str, int]]:
    """Parse the canonical Section 5.4 mapping table from the vendored spec."""
    specification = _SPEC_PATH.read_text(encoding="utf-8")
    mapping_section = specification.split(_MAPPING_HEADING, maxsplit=1)[1].split(_MAPPING_END, maxsplit=1)[0]

    bindings = {}
    for line in mapping_section.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) != _MAPPING_COLUMN_COUNT or not cells[1].lstrip("-").isdigit():
            continue
        http_status = cells[3].split(maxsplit=1)[0]
        if not http_status.isdigit():
            continue
        bindings[cells[0]] = (int(cells[1]), cells[2], int(http_status))
    return bindings


def test_error_bindings_match_section_5_4() -> None:
    """Every executable A2A error binding must match the vendored spec table."""
    expected = _spec_error_bindings()
    actual = {
        name: (binding.jsonrpc_code, binding.grpc_status, binding.http_status)
        for name, binding in ERROR_BINDINGS.items()
        if name in expected
    }

    assert actual == expected
