# Sample Output

This repository orchestrates agent runs. A full run requires Anthropic credentials and the Claude Code CLI, so this sample shows the expected output shape without committing generated application code.

```text
runs/20260427-181500-build-a-todo/
|-- request.txt
|-- RUN_SUMMARY.md
|-- specs/
|   |-- product_spec.md
|   |-- architecture.md
|   |-- test_report.md
|   |-- review.md
|   `-- devops_notes.md
|-- transcripts/
|   |-- product_manager.md
|   |-- architect.md
|   |-- coder.md
|   |-- tester.md
|   |-- reviewer.md
|   |-- devops.md
|   `-- documentation.md
|-- app/
|-- tests/
|-- Dockerfile
|-- .github/workflows/ci.yml
|-- scripts/run.sh
|-- scripts/test.sh
`-- README.md
```

Example summary:

```text
Run directory: runs/20260427-181500-build-a-todo
Request: Build a TODO REST API in Python

Agent results:
  [OK ] product_manager    ( 20.4s)
  [OK ] architect          ( 38.9s)
  [OK ] coder              (112.7s)
  [OK ] tester             ( 54.1s)
  [OK ] reviewer           ( 41.8s)
  [OK ] devops             ( 33.2s)
  [OK ] documentation      ( 29.5s)

Overall: SUCCESS
```
