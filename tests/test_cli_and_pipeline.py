import argparse
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import build
from orchestrator.pipeline import PipelineResult, _hint_from_request, _prepare_run_dir


class CliAndPipelineTests(unittest.TestCase):
    def test_build_help_runs_without_optional_runtime_dependencies(self):
        result = subprocess.run(
            [sys.executable, "build.py", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Run the multi-agent software development pipeline", result.stdout)

    def test_resolve_request_accepts_exactly_one_source(self):
        args = argparse.Namespace(
            request="Build a small API",
            request_file=None,
            example=None,
        )

        self.assertEqual(build.resolve_request(args), "Build a small API")

    def test_resolve_request_rejects_multiple_sources(self):
        args = argparse.Namespace(
            request="Build a small API",
            request_file=Path("examples/todo_api.txt"),
            example=None,
        )

        with self.assertRaises(SystemExit):
            build.resolve_request(args)

    def test_run_directory_uses_timestamp_and_safe_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _prepare_run_dir(Path(tmp), "Build a TODO API!")

            self.assertTrue(run_dir.exists())
            self.assertTrue((run_dir / "specs").exists())
            self.assertTrue((run_dir / "transcripts").exists())
            self.assertIn("build_a_todo_api", run_dir.name)

    def test_pipeline_summary_reports_success(self):
        result = PipelineResult(
            run_dir=Path("runs/example"),
            request="Build a TODO API",
            agent_runs=[],
        )

        self.assertTrue(result.succeeded)
        self.assertIn("Overall: SUCCESS", result.summary())

    def test_hint_from_request_is_short_and_filesystem_safe(self):
        self.assertEqual(_hint_from_request("Build a TODO API with users"), "Build-a-TODO-API-with")


if __name__ == "__main__":
    unittest.main()
