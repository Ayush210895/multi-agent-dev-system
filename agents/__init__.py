"""Agent personas for the multi-agent software development system.

Each module exposes:
    NAME: short identifier
    DESCRIPTION: one-line summary used by the orchestrator
    SYSTEM_PROMPT: full instructions for the agent
    ALLOWED_TOOLS: list of tool names the agent may invoke
    INPUT_ARTIFACTS: filenames the agent reads from the run directory
    OUTPUT_ARTIFACT: filename the agent must produce
"""

from . import (
    architect,
    coder,
    devops,
    documentation,
    product_manager,
    reviewer,
    tester,
)

PIPELINE = [
    product_manager,
    architect,
    coder,
    tester,
    reviewer,
    devops,
    documentation,
]

__all__ = [
    "PIPELINE",
    "product_manager",
    "architect",
    "coder",
    "tester",
    "reviewer",
    "devops",
    "documentation",
]
