from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HERMES = REPO_ROOT / "commands" / "hermes.py"


class CliContractTest(unittest.TestCase):
    def run_hermes(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(HERMES), *args],
            cwd=REPO_ROOT,
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
