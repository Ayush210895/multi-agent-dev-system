# Multi-agent software development system

A pipeline of seven Claude agents that takes a free-form project request
("build me a TODO REST API in Python") and produces a working
application: spec, architecture, source code, tests, code review,
Docker/CI configuration, and a README.

Built on the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python).

## How it works

```
your request
     |
     v
+----------------+      +------------+      +-------+      +---------+
| Product Mgr    | -->  | Architect  | -->  | Coder | -->  | Tester  |
| (spec)         |      | (design)   |      | (app/) |     | (tests/) |
+----------------+      +------------+      +-------+      +---------+
                                                                |
                                                                v
                              +----------+    +--------+    +----------+
                              | Reviewer | -> | DevOps | -> | Docs     |
                              | (audit)  |    | (CI)   |    | (README) |
                              +----------+    +--------+    +----------+
```

Each agent gets its own `ClaudeSDKClient` session with a tightly scoped
system prompt and tool list. They share a working directory: earlier
agents write artifacts (spec docs, source files, test reports) that
later agents read. Nothing is passed agent-to-agent through the
orchestrator beyond the original request — all coordination happens
through the filesystem, which keeps the design simple and easy to
inspect.

The seven roles:

| Agent           | Reads                                        | Writes                                       |
|-----------------|----------------------------------------------|----------------------------------------------|
| Product Manager | the original request                         | `specs/product_spec.md`                      |
| Architect       | spec                                         | `specs/architecture.md`                      |
| Coder           | spec, architecture                           | `app/...`                                    |
| Tester          | spec, architecture, app                      | `tests/...`, `specs/test_report.md`          |
| Reviewer        | everything                                   | `specs/review.md`, fixes under `app/`        |
| DevOps          | architecture, review, app, tests             | `Dockerfile`, `.github/workflows/ci.yml`, scripts |
| Documentation   | everything                                   | `README.md`, `docs/CHANGELOG.md`             |

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
cp .env.example .env
$EDITOR .env   # paste your ANTHROPIC_API_KEY

# 3. Make sure the Claude Code CLI dependency is satisfied (the SDK
#    spawns the CLI under the hood). If you don't already have it:
npm install -g @anthropic-ai/claude-code
```

## Quick start

Build the included TODO API example end-to-end:

```bash
python build.py --example todo_api
```

Or describe your own project:

```bash
python build.py "A FastAPI service that exposes /shorten and /<slug> for URL shortening, persisted to SQLite."
```

Or read the request from a file:

```bash
python build.py --request-file ./examples/url_shortener.txt
```

A run produces a directory under `runs/<timestamp>-<hint>/` containing:

```
runs/20260427-181500-build-a-todo/
├── request.txt              # exactly what you asked for
├── RUN_SUMMARY.md           # which agents ran, how long, OK/FAIL
├── specs/                   # PM, architect, test, review, devops notes
│   ├── product_spec.md
│   ├── architecture.md
│   ├── test_report.md
│   ├── review.md
│   └── devops_notes.md
├── transcripts/             # full per-agent conversation logs
│   ├── product_manager.md
│   ├── architect.md
│   └── ...
├── app/                     # the generated application source
├── tests/                   # the generated test suite
├── Dockerfile
├── .github/workflows/ci.yml
├── scripts/run.sh
├── scripts/test.sh
└── README.md                # README for the *generated* app
```

## Configuration

| Variable            | Default                          | Purpose                                   |
|---------------------|----------------------------------|-------------------------------------------|
| `ANTHROPIC_API_KEY` | _(required)_                     | API key for the SDK                       |
| `CLAUDE_MODEL`      | `claude-sonnet-4-5`              | Model used by every agent                 |
| `OUTPUT_DIR`        | `./runs`                         | Where run directories are created         |

You can also override the model per-invocation with `--model
claude-opus-4-6`.

## Customizing the pipeline

Every agent is a small Python module under `agents/`. To change a
behavior, edit the agent's `SYSTEM_PROMPT`. To add a new role (say, a
"Security" agent that runs after Reviewer), drop a new module in
`agents/` exposing the same constants and add it to the `PIPELINE` list
in `agents/__init__.py`.

To run a subset of the pipeline programmatically:

```python
from pathlib import Path
from agents import architect, coder, tester
from orchestrator import run_pipeline

result = run_pipeline(
    "A library that parses cron expressions and yields the next N firings.",
    output_root=Path("./runs"),
    agents=[architect, coder, tester],   # skip PM, Reviewer, DevOps, Docs
)
print(result.summary())
```

## Layout

```
.
├── agents/              # one module per agent persona
├── orchestrator/        # pipeline runner around the Claude Agent SDK
├── examples/            # canned project requests
├── build.py             # CLI entry point
├── requirements.txt
├── .env.example
└── README.md
```

## Notes and gotchas

- Each agent runs **in sequence**. A 7-agent build of a small app
  typically takes 5-15 minutes and consumes significant tokens. Start
  with the smallest example to confirm your setup before pointing it
  at anything ambitious.
- The orchestrator runs with `permission_mode="acceptEdits"` so the
  pipeline does not stall waiting for a human. Audit the generated
  output before running it. If you'd rather approve every tool call,
  change the mode in `orchestrator/pipeline.py`.
- The pipeline stops at the first agent that fails (raises an
  exception). The partial output and full transcript are kept on disk
  so you can inspect what went wrong.
- The Reviewer is allowed to apply its own fixes. If you want a
  read-only review, remove `Edit` and `Write` from
  `agents/reviewer.py`'s `ALLOWED_TOOLS`.

## License

MIT.
