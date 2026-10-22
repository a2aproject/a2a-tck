"""Agent Card protocol binding identifiers (spec Section 5.8)."""

from __future__ import annotations

from typing import Any

from rfc3986_validator import validate_rfc3986

from tck.requirements.base import STANDARD_BINDINGS


def uses_recommended_binding_identifier(value: object) -> bool:
    """Check the recommended identifier form without declaring custom names invalid."""
    return isinstance(value, str) and (value in STANDARD_BINDINGS or bool(validate_rfc3986(value, rule="URI")))


def supports_input_media_type(card: dict[str, Any], media_type: str) -> bool:
    """A negative probe is inapplicable if defaults or any skill advertise its type."""
    target = media_type.partition(";")[0].strip().lower()
    if "/" not in target:
        raise ValueError("Probe media type must contain a type and subtype")
    matching = {target, target.split("/", 1)[0] + "/*", "*/*"}
    skills = card.get("skills", [])
    if not isinstance(skills, list) or any(not isinstance(skill, dict) for skill in skills):
        raise ValueError("Agent Card skills must be an array of objects")
    mode_sets = [card.get("defaultInputModes", [])] + [skill["inputModes"] for skill in skills if "inputModes" in skill]
    modes = []
    for mode_set in mode_sets:
        if not isinstance(mode_set, list) or any(not isinstance(mode, str) or not mode.strip() for mode in mode_set):
            raise ValueError("Agent Card input modes must be arrays of non-empty strings")
        modes.extend(mode.partition(";")[0].strip().lower() for mode in mode_set)
    return any(mode in matching for mode in modes)
