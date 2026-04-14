"""Java code emitter for Jakarta EE / WildFly A2A SDK.

Generates a complete runnable WildFly project from parsed Scenario objects
using Jinja2 templates stored in ``codegen/a2a-jakarta/``.
"""

from __future__ import annotations

import os

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from codegen.java_emitter import _DEFAULT_A2A_JAVA_SDK_VERSION, _build_handlers, _render
from codegen.model import Scenario, StreamingMessageTrigger


_TEMPLATES_DIR = Path(__file__).parent / "a2a-jakarta"

_DEFAULT_A2A_JAKARTA_SDK_VERSION = "1.0.0.Alpha4-SNAPSHOT"
_DEFAULT_WILDFLY_VERSION = "39.0.1.Final"
_DEFAULT_GRPC_FEATURE_PACK_VERSION = "0.1.16.Final"

_JAVA_PACKAGE = "org.a2aproject.jakarta.sdk.sut"
_JAVA_PACKAGE_DIR = _JAVA_PACKAGE.replace(".", "/")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit_jakarta_project(scenarios: list[Scenario], output_dir: Path) -> list[Path]:
    """Generate a complete WildFly + Jakarta A2A project under *output_dir*.

    Returns the list of generated file paths.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    handlers = _build_handlers(scenarios)
    has_streaming = any(
        isinstance(s.trigger, StreamingMessageTrigger) for s in scenarios
    )

    a2a_jakarta_sdk_version = os.environ.get(
        "A2A_JAKARTA_SDK_VERSION", _DEFAULT_A2A_JAKARTA_SDK_VERSION,
    )
    wildfly_version = os.environ.get(
        "WILDFLY_VERSION", _DEFAULT_WILDFLY_VERSION,
    )
    grpc_feature_pack_version = os.environ.get(
        "WILDFLY_GRPC_VERSION", _DEFAULT_GRPC_FEATURE_PACK_VERSION,
    )
    a2a_java_sdk_version = os.environ.get(
        "A2A_JAVA_SDK_VERSION", _DEFAULT_A2A_JAVA_SDK_VERSION,
    )

    context = {
        "handlers": handlers,
        "has_streaming": has_streaming,
        "package": _JAVA_PACKAGE,
        "a2a_jakarta_sdk_version": a2a_jakarta_sdk_version,
        "a2a_java_sdk_version": a2a_java_sdk_version,
        "wildfly_version": wildfly_version,
        "grpc_feature_pack_version": grpc_feature_pack_version,
    }

    generated: list[Path] = []

    # Java sources
    java_src = output_dir / "src" / "main" / "java" / _JAVA_PACKAGE_DIR
    java_src.mkdir(parents=True, exist_ok=True)

    for template_name, filename in [
        ("TckAgentExecutorProducer.java.j2", "TckAgentExecutorProducer.java"),
        ("TckAgentCardProducer.java.j2", "TckAgentCardProducer.java"),
        ("TckApplication.java.j2", "TckApplication.java"),
    ]:
        generated.append(_render(env, template_name, context, java_src / filename))

    # WEB-INF resources
    web_inf = output_dir / "src" / "main" / "resources" / "META-INF"
    web_inf.mkdir(parents=True, exist_ok=True)
    generated.append(
        _render(env, "beans.xml.j2", context, web_inf / "beans.xml"),
    )

    # Build file
    generated.append(_render(env, "pom.xml.j2", context, output_dir / "pom.xml"))

    return generated
