"""
A2A Compliance Levels for SDK Validation

Defines the different levels of A2A specification compliance with detailed
requirements and badges for each level.
"""

COMPLIANCE_LEVELS = {
    "MANDATORY": {
        "name": "MANDATORY",
        "badge": "🟡 A2A Core Compliant",
        "description": "Minimum requirements for A2A compliance",
        "color": "#FFA500",
        "requirements": [
            "All JSON-RPC 2.0 mandatory tests pass",
            "All A2A protocol mandatory tests pass",
            "Agent Card has all required fields with correct types",
            "Core methods (message/send, tasks/get, tasks/cancel) work correctly",
            "Proper error handling for invalid requests",
            "No mandatory test failures",
        ],
        "thresholds": {
            "mandatory_success_rate": 100,
            "capability_success_rate": 50,  # Low bar for core compliance
            "quality_success_rate": 50,
            "feature_success_rate": 30,
        },
        "business_value": "SDK can be used for basic A2A integrations",
        "target_audience": "Development and testing environments",
    },
    "RECOMMENDED": {
        "name": "RECOMMENDED",
        "badge": "🟢 A2A Recommended Compliant",
        "description": "Includes SHOULD requirements from specification",
        "color": "#32CD32",
        "requirements": [
            "All MANDATORY requirements met",
            "Declared capabilities work correctly (no false advertising)",
            "Proper implementation of SHOULD requirements",
            "Good error messages with specification references",
            "Handles edge cases gracefully",
            "Basic quality standards met",
        ],
        "thresholds": {
            "mandatory_success_rate": 100,
            "capability_success_rate": 85,
            "quality_success_rate": 75,
            "feature_success_rate": 60,
        },
        "business_value": "SDK ready for staging and pre-production use",
        "target_audience": "Staging environments and careful production use",
    },
    "FULL_FEATURED": {
        "name": "FULL_FEATURED",
        "badge": "🏆 A2A Fully Compliant",
        "description": "Implements optional capabilities correctly",
        "color": "#FFD700",
        "requirements": [
            "All RECOMMENDED requirements met",
            "Declared capabilities work perfectly",
            "No capability is declared but unimplemented",
            "Quality tests pass (concurrency, resilience, edge cases)",
            "Comprehensive feature implementation",
            "Production-ready quality standards",
        ],
        "thresholds": {
            "mandatory_success_rate": 100,
            "capability_success_rate": 95,
            "quality_success_rate": 90,
            "feature_success_rate": 80,
        },
        "business_value": "SDK ready for full production deployment",
        "target_audience": "Production environments with confidence",
    },
    "NON_COMPLIANT": {
        "name": "NON_COMPLIANT",
        "badge": "🔴 Not A2A Compliant",
        "description": "Fails mandatory A2A specification requirements",
        "color": "#DC143C",
        "requirements": [
            "Must fix mandatory test failures",
            "Must implement core A2A methods correctly",
            "Must have valid Agent Card with required fields",
            "Must handle basic JSON-RPC requirements",
        ],
        "thresholds": {
            "mandatory_success_rate": 99,  # Any mandatory failure = non-compliant
            "capability_success_rate": 0,
            "quality_success_rate": 0,
            "feature_success_rate": 0,
        },
        "business_value": "SDK cannot be used for A2A integrations",
        "target_audience": "Development only - not suitable for any deployment",
    },
}


def get_compliance_level(mandatory_rate, capability_rate, quality_rate, feature_rate):
    """
    Determine compliance level based on success rates.

    Args:
        mandatory_rate: Success rate for mandatory tests (0-100)
        capability_rate: Success rate for capability tests (0-100)
        quality_rate: Success rate for quality tests (0-100)
        feature_rate: Success rate for feature tests (0-100)

    Returns:
        Dict with compliance level information
    """
    # Must pass all mandatory tests for any compliance
    if mandatory_rate < 100:
        return COMPLIANCE_LEVELS["NON_COMPLIANT"]

    # Check for full featured compliance
    full_featured = COMPLIANCE_LEVELS["FULL_FEATURED"]["thresholds"]
    if (
        capability_rate >= full_featured["capability_success_rate"]
        and quality_rate >= full_featured["quality_success_rate"]
        and feature_rate >= full_featured["feature_success_rate"]
    ):
        return COMPLIANCE_LEVELS["FULL_FEATURED"]

    # Check for recommended compliance
    recommended = COMPLIANCE_LEVELS["RECOMMENDED"]["thresholds"]
    if capability_rate >= recommended["capability_success_rate"] and quality_rate >= recommended["quality_success_rate"]:
        return COMPLIANCE_LEVELS["RECOMMENDED"]

    # Basic compliance
    return COMPLIANCE_LEVELS["MANDATORY"]


def get_compliance_badge_html(level_name):
    """Generate HTML badge for compliance level."""
    level = COMPLIANCE_LEVELS.get(level_name, COMPLIANCE_LEVELS["NON_COMPLIANT"])

    return f"""
    <div style="display: inline-block; padding: 8px 16px; background-color: {level["color"]}; 
                color: white; border-radius: 6px; font-weight: bold; font-family: Arial, sans-serif;">
        {level["badge"]}
    </div>
    """


def get_compliance_badge_markdown(level_name):
    """Generate Markdown badge for compliance level."""
    level = COMPLIANCE_LEVELS.get(level_name, COMPLIANCE_LEVELS["NON_COMPLIANT"])
    color = level["color"].replace("#", "")

    return f"![{level['badge']}](https://img.shields.io/badge/{level['badge'].replace(' ', '%20')}-{color})"


def get_next_level_requirements(current_level, mandatory_rate, capability_rate, quality_rate, feature_rate):
    """
    Get requirements to reach the next compliance level.

    Returns:
        Dict with next level information and specific requirements to meet
    """
    if current_level == "NON_COMPLIANT":
        next_level = COMPLIANCE_LEVELS["MANDATORY"]
        gaps = []
        if mandatory_rate < 100:
            gaps.append(f"Fix {100 - mandatory_rate:.1f}% of mandatory test failures")
        return {"next_level": next_level, "gaps": gaps, "priority": "CRITICAL"}

    elif current_level == "MANDATORY":
        next_level = COMPLIANCE_LEVELS["RECOMMENDED"]
        thresholds = next_level["thresholds"]
        gaps = []

        if capability_rate < thresholds["capability_success_rate"]:
            gap = thresholds["capability_success_rate"] - capability_rate
            gaps.append(f"Improve capability test success rate by {gap:.1f}%")

        if quality_rate < thresholds["quality_success_rate"]:
            gap = thresholds["quality_success_rate"] - quality_rate
            gaps.append(f"Improve quality test success rate by {gap:.1f}%")

        return {"next_level": next_level, "gaps": gaps, "priority": "HIGH"}

    elif current_level == "RECOMMENDED":
        next_level = COMPLIANCE_LEVELS["FULL_FEATURED"]
        thresholds = next_level["thresholds"]
        gaps = []

        if capability_rate < thresholds["capability_success_rate"]:
            gap = thresholds["capability_success_rate"] - capability_rate
            gaps.append(f"Improve capability test success rate by {gap:.1f}%")

        if quality_rate < thresholds["quality_success_rate"]:
            gap = thresholds["quality_success_rate"] - quality_rate
            gaps.append(f"Improve quality test success rate by {gap:.1f}%")

        if feature_rate < thresholds["feature_success_rate"]:
            gap = thresholds["feature_success_rate"] - feature_rate
            gaps.append(f"Improve feature test success rate by {gap:.1f}%")

        return {"next_level": next_level, "gaps": gaps, "priority": "MEDIUM"}

    # Already at highest level
    return {"next_level": None, "gaps": ["Maintain current compliance level"], "priority": "LOW"}


def generate_compliance_summary(mandatory_rate, capability_rate, quality_rate, feature_rate):
    """Generate a comprehensive compliance summary."""
    current_level = get_compliance_level(mandatory_rate, capability_rate, quality_rate, feature_rate)
    next_requirements = get_next_level_requirements(
        current_level["name"], mandatory_rate, capability_rate, quality_rate, feature_rate
    )

    return {
        "current_level": current_level,
        "next_requirements": next_requirements,
        "scores": {"mandatory": mandatory_rate, "capability": capability_rate, "quality": quality_rate, "feature": feature_rate},
        "overall_score": (mandatory_rate * 0.50 + capability_rate * 0.25 + quality_rate * 0.15 + feature_rate * 0.10),
    }
