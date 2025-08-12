"""Compares two versions of specifications to identify changes."""

from typing import Any, Dict

from deepdiff import DeepDiff


class SpecComparator:
    """Compares specification versions."""

    def compare_specs(self, old_spec: Dict, new_spec: Dict) -> Dict[str, Any]:
        """Compare two specification versions.

        Args:
            old_spec: Dict with 'markdown' and 'json' parsed specs
            new_spec: Dict with 'markdown' and 'json' parsed specs

        Returns:
            Dict with added, removed, and modified elements
        """
        comparison = {
            "markdown_changes": self._compare_markdown(old_spec.get("markdown", {}), new_spec.get("markdown", {})),
            "json_changes": self._compare_json(old_spec.get("json", {}), new_spec.get("json", {})),
            "summary": {},
            "impact_classification": {},
        }

        # Generate summary
        comparison["summary"] = self._generate_summary(comparison)

        # Classify changes by impact
        comparison["impact_classification"] = self._classify_changes(comparison)

        return comparison

    def _classify_changes(self, comparison: Dict) -> Dict[str, Any]:
        """Classify changes by their impact level."""
        classification = {
            "breaking_changes": [],
            "non_breaking_additions": [],
            "documentation_changes": [],
            "behavioral_changes": [],
        }

        # Analyze JSON changes for breaking changes
        json_changes = comparison["json_changes"]

        # Breaking: Removed required fields
        for change in json_changes["required_fields"]["removed"]:
            classification["breaking_changes"].append(
                {
                    "type": "required_field_removed",
                    "object": change["object"],
                    "fields": change["fields"],
                    "impact": "Client code using these fields will break",
                }
            )

        # Breaking: Removed required fields from existing objects
        for change in json_changes["required_fields"]["modified"]:
            if change["removed_fields"]:
                classification["breaking_changes"].append(
                    {
                        "type": "required_field_removed_from_object",
                        "object": change["object"],
                        "removed_fields": change["removed_fields"],
                        "impact": "Client code expecting these fields will break",
                    }
                )

        # Breaking: Removed methods
        for change in json_changes["methods"]["removed"]:
            classification["breaking_changes"].append(
                {"type": "method_removed", "method": change["name"], "impact": "Client code calling this method will break"}
            )

        # Breaking: Removed definitions
        for change in json_changes["definitions"]["removed"]:
            classification["breaking_changes"].append(
                {"type": "definition_removed", "definition": change["name"], "impact": "Client code using this type will break"}
            )

        # Breaking: Modified error codes
        for change in json_changes["error_codes"]["modified"]:
            classification["breaking_changes"].append(
                {
                    "type": "error_code_changed",
                    "error": change["name"],
                    "old_code": change["old_info"].get("code"),
                    "new_code": change["new_info"].get("code"),
                    "impact": "Client error handling code may break",
                }
            )

        # Non-breaking: Added methods
        for change in json_changes["methods"]["added"]:
            classification["non_breaking_additions"].append(
                {"type": "method_added", "method": change["name"], "impact": "New functionality available"}
            )

        # Non-breaking: Added optional fields
        for change in json_changes["required_fields"]["modified"]:
            if change["added_fields"]:
                classification["non_breaking_additions"].append(
                    {
                        "type": "required_field_added",
                        "object": change["object"],
                        "added_fields": change["added_fields"],
                        "impact": "New required fields - servers must implement",
                    }
                )

        # Non-breaking: Added definitions
        for change in json_changes["definitions"]["added"]:
            classification["non_breaking_additions"].append(
                {"type": "definition_added", "definition": change["name"], "impact": "New types available for use"}
            )

        # Non-breaking: Added error codes
        for change in json_changes["error_codes"]["added"]:
            classification["non_breaking_additions"].append(
                {
                    "type": "error_code_added",
                    "error": change["name"],
                    "code": change["error_info"].get("code"),
                    "impact": "New error condition defined",
                }
            )

        # Analyze requirement changes
        md_changes = comparison["markdown_changes"]

        # Breaking: Removed MUST requirements
        for change in md_changes["requirements"]["removed"]:
            if change["level"] in ["MUST", "SHALL", "REQUIRED"]:
                classification["breaking_changes"].append(
                    {
                        "type": "mandatory_requirement_removed",
                        "requirement": change["requirement"].text,
                        "section": change["section"],
                        "impact": "Previously mandatory behavior no longer required",
                    }
                )

        # Behavioral: Added MUST requirements
        for change in md_changes["requirements"]["added"]:
            if change["level"] in ["MUST", "SHALL", "REQUIRED"]:
                classification["behavioral_changes"].append(
                    {
                        "type": "mandatory_requirement_added",
                        "requirement": change["requirement"].text,
                        "section": change["section"],
                        "impact": "New mandatory behavior required",
                    }
                )
            elif change["level"] in ["SHOULD", "RECOMMENDED"]:
                classification["documentation_changes"].append(
                    {
                        "type": "recommendation_added",
                        "requirement": change["requirement"].text,
                        "section": change["section"],
                        "impact": "New recommended practice",
                    }
                )

        # Documentation: Section changes
        for change in md_changes["sections"]["added"]:
            classification["documentation_changes"].append(
                {"type": "section_added", "section": change["title"], "impact": "New documentation section"}
            )

        for change in md_changes["sections"]["modified"]:
            classification["documentation_changes"].append(
                {
                    "type": "section_modified",
                    "section": change["title"],
                    "impact": "Documentation updated",
                    "change_size": change["content_diff"],
                }
            )

        # Calculate impact score
        classification["impact_score"] = self._calculate_impact_score(classification)

        return classification

    def _calculate_impact_score(self, classification: Dict) -> Dict[str, int]:
        """Calculate numeric impact scores."""
        return {
            "breaking_score": len(classification["breaking_changes"]) * 10,
            "behavioral_score": len(classification["behavioral_changes"]) * 5,
            "addition_score": len(classification["non_breaking_additions"]) * 2,
            "documentation_score": len(classification["documentation_changes"]) * 1,
            "total_impact": (
                len(classification["breaking_changes"]) * 10
                + len(classification["behavioral_changes"]) * 5
                + len(classification["non_breaking_additions"]) * 2
                + len(classification["documentation_changes"]) * 1
            ),
        }

    def _compare_markdown(self, old_md: Dict, new_md: Dict) -> Dict[str, Any]:
        """Compare markdown specifications."""
        changes = {
            "requirements": {"added": [], "removed": [], "modified": []},
            "sections": {"added": [], "removed": [], "modified": []},
        }

        # Compare requirements
        old_reqs = {r.id: r for r in old_md.get("requirements", [])}
        new_reqs = {r.id: r for r in new_md.get("requirements", [])}

        # Since requirement IDs are auto-generated, compare by content
        old_req_texts = {r.text: r for r in old_md.get("requirements", [])}
        new_req_texts = {r.text: r for r in new_md.get("requirements", [])}

        # Find added requirements
        for req_text, req in new_req_texts.items():
            if req_text not in old_req_texts:
                changes["requirements"]["added"].append({"requirement": req, "section": req.section, "level": req.level})

        # Find removed requirements
        for req_text, req in old_req_texts.items():
            if req_text not in new_req_texts:
                changes["requirements"]["removed"].append({"requirement": req, "section": req.section, "level": req.level})

        # Find modified requirements (same section/level but different text)
        # For now, we'll consider requirements as either added or removed
        # More sophisticated diff could identify text modifications

        # Compare sections
        old_sections = {s["title"]: s for s in old_md.get("sections", [])}
        new_sections = {s["title"]: s for s in new_md.get("sections", [])}

        # Find added sections
        for title, section in new_sections.items():
            if title not in old_sections:
                changes["sections"]["added"].append(section)

        # Find removed sections
        for title, section in old_sections.items():
            if title not in new_sections:
                changes["sections"]["removed"].append(section)

        # Find modified sections (same title but different content)
        for title in old_sections:
            if title in new_sections:
                old_content = old_sections[title]["content"]
                new_content = new_sections[title]["content"]
                if old_content != new_content:
                    changes["sections"]["modified"].append(
                        {
                            "title": title,
                            "old_content": old_content,
                            "new_content": new_content,
                            "content_diff": self._generate_text_diff(old_content, new_content),
                        }
                    )

        return changes

    def _compare_json(self, old_json: Dict, new_json: Dict) -> Dict[str, Any]:
        """Compare JSON schema specifications."""
        changes = {
            "definitions": {"added": [], "removed": [], "modified": []},
            "error_codes": {"added": [], "removed": [], "modified": []},
            "methods": {"added": [], "removed": [], "modified": []},
            "required_fields": {"added": [], "removed": [], "modified": []},
        }

        # Compare definitions
        old_defs = old_json.get("definitions", {})
        new_defs = new_json.get("definitions", {})

        # Added definitions
        for def_name in new_defs:
            if def_name not in old_defs:
                changes["definitions"]["added"].append({"name": def_name, "definition": new_defs[def_name]})

        # Removed definitions
        for def_name in old_defs:
            if def_name not in new_defs:
                changes["definitions"]["removed"].append({"name": def_name, "definition": old_defs[def_name]})

        # Modified definitions
        for def_name in old_defs:
            if def_name in new_defs:
                old_def = old_defs[def_name]
                new_def = new_defs[def_name]

                # Use DeepDiff for detailed comparison
                diff = DeepDiff(old_def, new_def, ignore_order=True)
                if diff:
                    changes["definitions"]["modified"].append(
                        {"name": def_name, "old_definition": old_def, "new_definition": new_def, "diff": diff}
                    )

        # Compare error codes
        old_errors = old_json.get("error_codes", {})
        new_errors = new_json.get("error_codes", {})

        for error_name in new_errors:
            if error_name not in old_errors:
                changes["error_codes"]["added"].append({"name": error_name, "error_info": new_errors[error_name]})

        for error_name in old_errors:
            if error_name not in new_errors:
                changes["error_codes"]["removed"].append({"name": error_name, "error_info": old_errors[error_name]})

        for error_name in old_errors:
            if error_name in new_errors:
                if old_errors[error_name] != new_errors[error_name]:
                    changes["error_codes"]["modified"].append(
                        {"name": error_name, "old_info": old_errors[error_name], "new_info": new_errors[error_name]}
                    )

        # Compare methods
        old_methods = old_json.get("methods", {})
        new_methods = new_json.get("methods", {})

        for method_name in new_methods:
            if method_name not in old_methods:
                changes["methods"]["added"].append({"name": method_name, "method_info": new_methods[method_name]})

        for method_name in old_methods:
            if method_name not in new_methods:
                changes["methods"]["removed"].append({"name": method_name, "method_info": old_methods[method_name]})

        for method_name in old_methods:
            if method_name in new_methods:
                if old_methods[method_name] != new_methods[method_name]:
                    changes["methods"]["modified"].append(
                        {"name": method_name, "old_info": old_methods[method_name], "new_info": new_methods[method_name]}
                    )

        # Compare required fields
        old_required = old_json.get("required_fields", {})
        new_required = new_json.get("required_fields", {})

        for obj_name in new_required:
            if obj_name not in old_required:
                changes["required_fields"]["added"].append({"object": obj_name, "fields": new_required[obj_name]})
            elif set(new_required[obj_name]) != set(old_required[obj_name]):
                added_fields = set(new_required[obj_name]) - set(old_required[obj_name])
                removed_fields = set(old_required[obj_name]) - set(new_required[obj_name])

                if added_fields or removed_fields:
                    changes["required_fields"]["modified"].append(
                        {
                            "object": obj_name,
                            "added_fields": list(added_fields),
                            "removed_fields": list(removed_fields),
                            "old_fields": old_required[obj_name],
                            "new_fields": new_required[obj_name],
                        }
                    )

        for obj_name in old_required:
            if obj_name not in new_required:
                changes["required_fields"]["removed"].append({"object": obj_name, "fields": old_required[obj_name]})

        return changes

    def _generate_text_diff(self, old_text: str, new_text: str) -> str:
        """Generate a simple text diff summary."""
        # Simple implementation - could be enhanced with proper diff algorithms
        if len(new_text) > len(old_text):
            return f"Content expanded by {len(new_text) - len(old_text)} characters"
        if len(new_text) < len(old_text):
            return f"Content reduced by {len(old_text) - len(new_text)} characters"
        return "Content modified (same length)"

    def _generate_summary(self, comparison: Dict) -> Dict[str, Any]:
        """Generate summary statistics of changes."""
        md_changes = comparison["markdown_changes"]
        json_changes = comparison["json_changes"]

        return {
            "total_changes": (
                len(md_changes["requirements"]["added"])
                + len(md_changes["requirements"]["removed"])
                + len(md_changes["sections"]["added"])
                + len(md_changes["sections"]["removed"])
                + len(md_changes["sections"]["modified"])
                + len(json_changes["definitions"]["added"])
                + len(json_changes["definitions"]["removed"])
                + len(json_changes["definitions"]["modified"])
                + len(json_changes["error_codes"]["added"])
                + len(json_changes["error_codes"]["removed"])
                + len(json_changes["methods"]["added"])
                + len(json_changes["methods"]["removed"])
            ),
            "requirement_changes": {
                "added": len(md_changes["requirements"]["added"]),
                "removed": len(md_changes["requirements"]["removed"]),
                "modified": len(md_changes["requirements"]["modified"]),
            },
            "section_changes": {
                "added": len(md_changes["sections"]["added"]),
                "removed": len(md_changes["sections"]["removed"]),
                "modified": len(md_changes["sections"]["modified"]),
            },
            "definition_changes": {
                "added": len(json_changes["definitions"]["added"]),
                "removed": len(json_changes["definitions"]["removed"]),
                "modified": len(json_changes["definitions"]["modified"]),
            },
            "method_changes": {
                "added": len(json_changes["methods"]["added"]),
                "removed": len(json_changes["methods"]["removed"]),
                "modified": len(json_changes["methods"]["modified"]),
            },
        }
