from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HERMES = REPO_ROOT / "commands" / "hermes.py"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "daedalus-simple"


class CliContractTest(unittest.TestCase):
    def run_hermes(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PYTHONPATH"] = "modules" + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        return subprocess.run(
            [str(HERMES), *args],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_host_check_returns_machine_readable_success(self) -> None:
        completed = self.run_hermes("host", "check", "--format", "json")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["kind"], "host-check")
        self.assertTrue(payload["ok"])

    def test_help_and_version_work(self) -> None:
        help_result = self.run_hermes("--help")
        version_result = self.run_hermes("--version")

        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("context", help_result.stdout)
        self.assertEqual(version_result.returncode, 0, version_result.stderr)
        self.assertIn("hermes", version_result.stdout)

    def test_unknown_command_fails_clearly(self) -> None:
        completed = self.run_hermes("unknown")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("invalid choice", completed.stderr)

    def test_new_report_commands_emit_parseable_json(self) -> None:
        commands = [
            ("context", "--workspace", str(FIXTURE), "--format", "json"),
            ("network", "summary", "--format", "json"),
            ("host", "list", "--workspace", str(FIXTURE), "--format", "json"),
            ("host", "summary", "--workspace", str(FIXTURE), "--format", "json"),
            ("dns", "report", "--workspace", str(FIXTURE), "--format", "json"),
            ("report", "summary", "--workspace", str(FIXTURE), "--format", "json"),
        ]
        for command in commands:
            with self.subTest(command=command):
                completed = self.run_hermes(*command)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                payload = json.loads(completed.stdout)
                self.assertIn("kind", payload)

    def test_markdown_report_has_stable_headings(self) -> None:
        completed = self.run_hermes(
            "report",
            "summary",
            "--workspace",
            str(FIXTURE),
            "--format",
            "markdown",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("# Hermes Operations Summary", completed.stdout)
        self.assertIn("## Suggested Manual Checks", completed.stdout)

    def test_dns_apply_cli_defaults_to_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            desired = root / "desired.zone"
            current = root / "current.zone"
            config = root / "hermes.yml"
            render = self.run_hermes(
                "dns",
                "render-zone",
                "--zone",
                "alflag.internal",
                "--source",
                "examples/resources.yaml",
                "--output",
                str(desired),
            )
            self.assertEqual(render.returncode, 0, render.stderr)
            current.write_text(
                """
$ORIGIN alflag.internal.
$TTL 300
@ IN SOA ns1.alflag.internal. hostmaster.alflag.internal. (
  2026053101 ; serial
  3600 ; refresh
  900 ; retry
  1209600 ; expire
  300 ; minimum
)
@ IN NS ns1
old IN A 10.0.0.1
""".lstrip(),
                encoding="utf-8",
            )
            config.write_text(
                f"""
dns:
  zones:
    alflag.internal:
      zone_file: {current}
      reload_command: "true"
""".lstrip(),
                encoding="utf-8",
            )

            completed = self.run_hermes(
                "--config",
                str(config),
                "dns",
                "apply-zone",
                "--zone",
                "alflag.internal",
                "--file",
                str(desired),
                "--format",
                "json",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["kind"], "apply-result")
            self.assertTrue(payload["dry_run"])
            self.assertIn("old IN A 10.0.0.1", current.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
