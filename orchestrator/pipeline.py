"""Pipeline orchestrator for the multi-agent software development system.

The orchestrator runs each agent in sequence inside a shared run
directory. Every agent gets:
  - its own ClaudeSDKClient session
  - the same `cwd` (the run directory), so artifacts written by earlier
    agents are visible to later ones
  - a tightly scoped `allowed_tools` list
  - a system prompt that tells it exactly what to read and what to write

The orchestrator does not interpret the agents' work. It just feeds the
project request in, runs the agents in order, captures their outputs,
and returns a structured result.
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# We import the SDK lazily inside run_pipeline so that `python -m
# orchestrator.pipeline --help`-style introspection works without the
# SDK being installed. anyio is imported lazily for the same reason, so
# `python build.py --help` works before dependencies are installed.


@dataclass
class AgentRun:
    """Result of running a single agent in the pipeline."""

    name: str
    started_at: float
    finished_at: float
    transcript_path: Path
    output_text: str
    succeeded: bool
    error: str | None = None

    @property
    def duration_s(self) -> float:
        return self.finished_at - self.started_at


@dataclass
class PipelineResult:
    """Aggregate result of the full pipeline."""

    run_dir: Path
    request: str
    agent_runs: list[AgentRun] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return all(r.succeeded for r in self.agent_runs)

    def summary(self) -> str:
        lines = [
            f"Run directory: {self.run_dir}",
            f"Request: {self.request[:100]}{'...' if len(self.request) > 100 else ''}",
            "",
            "Agent results:",
        ]
        for r in self.agent_runs:
            status = "OK " if r.succeeded else "FAIL"
            lines.append(f"  [{status}] {r.name:<18} ({r.duration_s:5.1f}s)")
            if not r.succeeded and r.error:
                lines.append(f"         error: {r.error}")
        lines.append("")
        lines.append("Overall: " + ("SUCCESS" if self.succeeded else "FAILURE"))
        return "\n".join(lines)


def _build_user_prompt(agent_module: Any, project_request: str) -> str:
    """Compose the per-agent user message.

    The agent's behavior is defined by its system prompt; this user
    message just hands it the original project request and reminds it of
    its inputs and expected output.
    """

    inputs = agent_module.INPUT_ARTIFACTS
    output = agent_module.OUTPUT_ARTIFACT

    parts = [
        "## Project request",
        project_request.strip(),
        "",
        f"You are running as the **{agent_module.NAME}** agent.",
    ]
    if inputs:
        parts.append("")
        parts.append("Inputs already in the working directory:")
        for art in inputs:
            parts.append(f"  - {art}")
    parts.append("")
    parts.append(f"Your expected output: `{output}`")
    parts.append("")
    parts.append(
        "Use your file tools to read inputs and write outputs. When you"
        " are finished, end your reply with a brief summary."
    )
    return "\n".join(parts)


async def _run_agent(
    agent_module: Any,
    project_request: str,
    run_dir: Path,
    transcripts_dir: Path,
    model: str,
) -> AgentRun:
    """Run a single agent against the shared run directory."""

    # Imports happen here so the SDK is only required when actually
    # running the pipeline.
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    started = time.time()
    transcript_path = transcripts_dir / f"{agent_module.NAME}.md"
    transcript_lines: list[str] = [
        f"# {agent_module.NAME} transcript",
        f"_started at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(started))}_",
        "",
    ]
    output_text_chunks: list[str] = []

    options = ClaudeAgentOptions(
        system_prompt=agent_module.SYSTEM_PROMPT,
        allowed_tools=list(agent_module.ALLOWED_TOOLS),
        cwd=str(run_dir),
        model=model,
        # Auto-approve tool use for unattended pipeline runs. Override
        # with permission_mode="ask" if you want a human in the loop.
        permission_mode="acceptEdits",
    )

    user_prompt = _build_user_prompt(agent_module, project_request)
    transcript_lines.append("## User prompt")
    transcript_lines.append("")
    transcript_lines.append("```")
    transcript_lines.append(user_prompt)
    transcript_lines.append("```")
    transcript_lines.append("")
    transcript_lines.append("## Agent reply")
    transcript_lines.append("")

    error: str | None = None
    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_prompt)
            async for message in client.receive_response():
                # The SDK yields heterogeneous Message objects. We just
                # want the human-readable text.
                text = _message_to_text(message)
                if text:
                    output_text_chunks.append(text)
                    transcript_lines.append(text)
        succeeded = True
    except Exception as exc:  # noqa: BLE001 — we want the message
        succeeded = False
        error = f"{type(exc).__name__}: {exc}"
        transcript_lines.append("")
        transcript_lines.append(f"**ERROR:** {error}")

    finished = time.time()
    transcript_path.write_text("\n".join(transcript_lines), encoding="utf-8")

    return AgentRun(
        name=agent_module.NAME,
        started_at=started,
        finished_at=finished,
        transcript_path=transcript_path,
        output_text="".join(output_text_chunks),
        succeeded=succeeded,
        error=error,
    )


def _message_to_text(message: Any) -> str:
    """Best-effort extraction of human-readable text from an SDK message.

    The SDK is still evolving; rather than depending on exact type names
    we walk common attributes.
    """

    # Direct .text attribute (text blocks)
    text = getattr(message, "text", None)
    if isinstance(text, str):
        return text

    # AssistantMessage typically carries .content as a list of blocks
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, Iterable):
        chunks: list[str] = []
        for block in content:
            block_text = getattr(block, "text", None)
            if isinstance(block_text, str):
                chunks.append(block_text)
        if chunks:
            return "\n".join(chunks)

    return ""


def _prepare_run_dir(base_dir: Path, project_name_hint: str) -> Path:
    """Create a uniquely named run directory and return its path."""

    base_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    safe_hint = "".join(
        c if c.isalnum() or c in ("-", "_") else "_"
        for c in project_name_hint.lower().strip()
    )[:40] or "run"
    run_dir = base_dir / f"{timestamp}-{safe_hint}"
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "specs").mkdir()
    (run_dir / "transcripts").mkdir()
    return run_dir


async def run_pipeline_async(
    project_request: str,
    output_root: Path,
    *,
    agents: list[Any] | None = None,
    model: str | None = None,
) -> PipelineResult:
    """Run the full pipeline asynchronously.

    Args:
        project_request: free-form description of the application to
            build, e.g. "A REST API for managing TODO items with users
            and labels".
        output_root: directory under which a fresh run directory will
            be created. The generated application lives under
            `<output_root>/<timestamp>-<hint>/app/`.
        agents: optional override of the agent pipeline; defaults to
            `agents.PIPELINE`.
        model: optional model override; defaults to env CLAUDE_MODEL or
            "claude-sonnet-4-5".
    """

    from agents import PIPELINE  # local import keeps top-level light

    pipeline = agents if agents is not None else PIPELINE
    chosen_model = (
        model
        or os.environ.get("CLAUDE_MODEL")
        or "claude-sonnet-4-5"
    )

    run_dir = _prepare_run_dir(output_root, _hint_from_request(project_request))
    transcripts_dir = run_dir / "transcripts"
    result = PipelineResult(run_dir=run_dir, request=project_request)

    # Persist the original request for debugging.
    (run_dir / "request.txt").write_text(project_request, encoding="utf-8")

    for agent_module in pipeline:
        print(f"\n=== {agent_module.NAME.upper()} ===")
        agent_run = await _run_agent(
            agent_module=agent_module,
            project_request=project_request,
            run_dir=run_dir,
            transcripts_dir=transcripts_dir,
            model=chosen_model,
        )
        result.agent_runs.append(agent_run)
        status = "OK" if agent_run.succeeded else "FAIL"
        print(f"[{status}] {agent_run.name} in {agent_run.duration_s:.1f}s")
        if not agent_run.succeeded:
            print(f"  error: {agent_run.error}")
            print("Stopping pipeline due to agent failure.")
            break

    # Write the final summary into the run directory.
    summary_path = run_dir / "RUN_SUMMARY.md"
    summary_path.write_text(result.summary(), encoding="utf-8")

    return result


def run_pipeline(
    project_request: str,
    output_root: Path,
    *,
    agents: list[Any] | None = None,
    model: str | None = None,
) -> PipelineResult:
    """Synchronous wrapper around `run_pipeline_async`.

    `anyio.run` does not forward keyword arguments, so we close over
    the kwargs in a small inner coroutine.
    """

    async def _wrapped() -> PipelineResult:
        return await run_pipeline_async(
            project_request,
            output_root,
            agents=agents,
            model=model,
        )

    import anyio

    return anyio.run(_wrapped)


def _hint_from_request(request: str) -> str:
    """Pull a short hint from the request for the run directory name."""

    first_line = request.strip().splitlines()[0] if request.strip() else "run"
    words = first_line.split()
    return "-".join(words[:5])


def cleanup_run_dir(run_dir: Path) -> None:
    """Remove a run directory. Safety guard against deleting elsewhere."""

    run_dir = run_dir.resolve()
    if not run_dir.exists():
        return
    if "runs" not in run_dir.parts and "generated_app" not in run_dir.parts:
        raise RuntimeError(
            f"Refusing to delete {run_dir}: not under a runs/ directory."
        )
    shutil.rmtree(run_dir)
