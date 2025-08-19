"""
Specification parser for extracting requirements and structure.
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Requirement:
    """Represents a specification requirement."""

    id: str
    section: str
    level: str  # MUST, SHALL, SHOULD, MAY
    text: str
    context: str  # Surrounding text for context


class SpecParser:
    """Parses A2A specification documents."""

    # Regex patterns for requirements
    REQUIREMENT_PATTERN = re.compile(
        r"(.*?)(MUST|SHALL|SHOULD|MAY|REQUIRED|RECOMMENDED)(?! NOT)(.*?)(?:\.|$)", re.MULTILINE | re.IGNORECASE
    )

    # Section header patterns
    SECTION_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def parse_markdown(self, content: str) -> Dict[str, Any]:
        """
        Parse markdown specification.

        Returns:
            Dict with sections, requirements, and structure
        """
        result = {
            "sections": self._extract_sections(content),
            "requirements": self._extract_requirements(content),
            "structure": self._analyze_structure(content),
        }
        return result

    def parse_json_schema(self, schema: dict) -> Dict[str, Any]:
        """
        Parse JSON schema to extract structure and requirements.

        Returns:
            Dict with definitions, required fields, and types
        """
        result = {
            "definitions": self._extract_definitions(schema),
            "required_fields": self._extract_required_fields(schema),
            "error_codes": self._extract_error_codes(schema),
            "methods": self._extract_methods(schema),
            "schema_info": self._extract_schema_info(schema),
        }
        return result

    def _extract_definitions(self, schema: dict) -> Dict[str, Any]:
        """Extract all type definitions from schema."""
        definitions = schema.get("definitions", {})
        extracted = {}

        for def_name, def_content in definitions.items():
            extracted[def_name] = {
                "type": def_content.get("type", "unknown"),
                "description": def_content.get("description", ""),
                "properties": def_content.get("properties", {}),
                "required": def_content.get("required", []),
                "enum": def_content.get("enum", []),
            }

        return extracted

    def _extract_required_fields(self, schema: dict) -> Dict[str, List[str]]:
        """Extract required fields for each object type."""
        definitions = schema.get("definitions", {})
        required_fields = {}

        for def_name, def_content in definitions.items():
            if def_content.get("type") == "object":
                required = def_content.get("required", [])
                if required:
                    required_fields[def_name] = required

        return required_fields

    def _extract_error_codes(self, schema: dict) -> Dict[str, Any]:
        """Extract error codes and their definitions."""
        definitions = schema.get("definitions", {})
        error_codes = {}

        # Look for error-related definitions
        for def_name, def_content in definitions.items():
            if "Error" in def_name:
                properties = def_content.get("properties", {})
                if "code" in properties:
                    code_def = properties["code"]
                    if "const" in code_def:
                        error_codes[def_name] = {
                            "code": code_def["const"],
                            "description": def_content.get("description", ""),
                            "message": properties.get("message", {}).get("const", ""),
                        }

        return error_codes

    def _extract_methods(self, schema: dict) -> Dict[str, Any]:
        """Extract method signatures from request/response definitions."""
        definitions = schema.get("definitions", {})
        methods = {}

        # Look for request/response pairs
        for def_name, def_content in definitions.items():
            if def_name.endswith("Request"):
                method_name = def_name.replace("Request", "")
                response_name = method_name + "Response"

                properties = def_content.get("properties", {})
                method_prop = properties.get("method", {})

                if "const" in method_prop:
                    rpc_method = method_prop["const"]
                    methods[rpc_method] = {
                        "request_type": def_name,
                        "response_type": response_name if response_name in definitions else None,
                        "params": properties.get("params", {}),
                        "description": def_content.get("description", ""),
                    }

        return methods

    def _extract_schema_info(self, schema: dict) -> Dict[str, Any]:
        """Extract general schema information."""
        return {
            "schema_version": schema.get("$schema", ""),
            "total_definitions": len(schema.get("definitions", {})),
            "has_error_codes": any("Error" in name for name in schema.get("definitions", {}).keys()),
            "has_requests": any("Request" in name for name in schema.get("definitions", {}).keys()),
            "has_responses": any("Response" in name for name in schema.get("definitions", {}).keys()),
        }

    def _extract_sections(self, content: str) -> List[Dict[str, str]]:
        """Extract section headers and their content."""
        sections = []
        section_matches = list(self.SECTION_PATTERN.finditer(content))

        for i, match in enumerate(section_matches):
            level = len(match.group(1))  # Number of # characters
            title = match.group(2).strip()
            start_pos = match.end()

            # Find end position (next section of same or higher level)
            end_pos = len(content)
            for j in range(i + 1, len(section_matches)):
                next_match = section_matches[j]
                next_level = len(next_match.group(1))
                if next_level <= level:
                    end_pos = next_match.start()
                    break

            section_content = content[start_pos:end_pos].strip()

            sections.append(
                {"level": level, "title": title, "content": section_content, "start_pos": match.start(), "end_pos": end_pos}
            )

        return sections

    def _extract_requirements(self, content: str) -> List[Requirement]:
        """Extract all requirements (MUST, SHALL, SHOULD, MAY)."""
        requirements = []

        # Split content into sections first
        sections = self._extract_sections(content)

        req_id_counter = 1

        for section in sections:
            section_name = section["title"]
            section_content = section["content"]

            # Find all requirements in this section
            for match in self.REQUIREMENT_PATTERN.finditer(section_content):
                before_text = match.group(1).strip()
                requirement_level = match.group(2).upper()
                after_text = match.group(3).strip()

                # Create requirement text
                req_text = f"{before_text} {requirement_level} {after_text}".strip()

                # Get surrounding context (50 chars before and after)
                start_context = max(0, match.start() - 50)
                end_context = min(len(section_content), match.end() + 50)
                context = section_content[start_context:end_context].strip()

                requirement = Requirement(
                    id=f"REQ-{req_id_counter:03d}", section=section_name, level=requirement_level, text=req_text, context=context
                )

                requirements.append(requirement)
                req_id_counter += 1

        return requirements

    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """Analyze overall document structure."""
        sections = self._extract_sections(content)

        structure = {
            "total_sections": len(sections),
            "section_hierarchy": {},
            "top_level_sections": [s for s in sections if s["level"] == 1],
            "content_length": len(content),
        }

        # Build hierarchy
        for section in sections:
            level = section["level"]
            if level not in structure["section_hierarchy"]:
                structure["section_hierarchy"][level] = []
            structure["section_hierarchy"][level].append(section["title"])

        return structure
