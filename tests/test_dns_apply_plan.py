from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hermes.dns.apply import apply_zone_file, diff_zone_text
from hermes.dns.zone import render_zone


class DnsApplyPlanTest(unittest.TestCase):
    def test_diff_zone_text_returns_upsert_and_delete_actions(self) -> None:
        desired = render_zone(
            "alflag.internal", [{"name": "new", "type": "A", "value": "10.0.0.2"}]
        )
        current = render_zone(
            "alflag.internal", [{"name": "old", "type": "A", "value": "10.0.0.1"}]
        )

        diff = diff_zone_text("alflag.internal", desired, current)

        self.assertEqual(
            [action["action"] for action in diff["actions"]], ["upsert-record", "delete-record"]
        )

    def test_apply_zone_file_is_dry_run_without_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            desired = root / "desired.zone"
            current = root / "current.zone"
            desired.write_text(
                render_zone("alflag.internal", [{"name": "new", "type": "A", "value": "10.0.0.2"}]),
                encoding="utf-8",
            )
            current.write_text(
                render_zone("alflag.internal", [{"name": "old", "type": "A", "value": "10.0.0.1"}]),
                encoding="utf-8",
            )

            result = apply_zone_file(
                "alflag.internal",
                str(desired),
                {"zone_file": str(current), "backup_dir": str(root / "backups")},
                apply=False,
            )

            self.assertTrue(result["ok"])
            self.assertTrue(result["dry_run"])
            self.assertIn("old IN A 10.0.0.1", current.read_text(encoding="utf-8"))

    def test_apply_zone_file_backs_up_replaces_reloads_and_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            desired = root / "desired.zone"
            current = root / "current.zone"
            backup_dir = root / "backups"
            reload_marker = root / "reloaded"
            desired.write_text(
                render_zone("alflag.internal", [{"name": "new", "type": "A", "value": "10.0.0.2"}]),
                encoding="utf-8",
            )
            current.write_text(
                render_zone("alflag.internal", [{"name": "old", "type": "A", "value": "10.0.0.1"}]),
                encoding="utf-8",
            )

            result = apply_zone_file(
                "alflag.internal",
                str(desired),
                {
                    "zone_file": str(current),
                    "backup_dir": str(backup_dir),
                    "check_command": "true",
                    "reload_command": f"touch {reload_marker}",
                },
                apply=True,
            )

            self.assertTrue(result["ok"])
            self.assertFalse(result["dry_run"])
            self.assertIn("new IN A 10.0.0.2", current.read_text(encoding="utf-8"))
            self.assertTrue(reload_marker.exists())
            backups = list(backup_dir.glob("alflag.internal.*.zone"))
            self.assertEqual(len(backups), 1)
            self.assertIn("old IN A 10.0.0.1", backups[0].read_text(encoding="utf-8"))

    def test_external_check_failure_prevents_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            desired = root / "desired.zone"
            current = root / "current.zone"
            desired.write_text(
                render_zone("alflag.internal", [{"name": "new", "type": "A", "value": "10.0.0.2"}]),
                encoding="utf-8",
            )
            original = render_zone(
                "alflag.internal", [{"name": "old", "type": "A", "value": "10.0.0.1"}]
            )
            current.write_text(original, encoding="utf-8")

            with self.assertRaisesRegex(Exception, "command failed"):
                apply_zone_file(
                    "alflag.internal",
                    str(desired),
                    {"zone_file": str(current), "check_command": "false"},
                    apply=True,
                )

            self.assertEqual(current.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
