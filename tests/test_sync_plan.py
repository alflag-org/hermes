from __future__ import annotations

import unittest

from hermes.proxmox.diff import diff_state, plan_from_diff


class SyncPlanTest(unittest.TestCase):
    def test_plan_contains_safe_metadata_updates(self) -> None:
        actual = {
            "guests": [
                {
                    "vmid": 240,
                    "name": "dns01",
                    "tags": ["dns"],
                    "description": "old",
                }
            ]
        }
        desired = {
            "resources": [
                {
                    "id": "dns01",
                    "type": "vm",
                    "proxmox": {"tags": ["dns", "mgmt"], "description": "new"},
                }
            ]
        }

        plan = plan_from_diff(diff_state(actual, desired, "kanagawa01"))

        self.assertEqual(plan["domain"], "proxmox")
        self.assertEqual(
            [action["action"] for action in plan["actions"]], ["update-tags", "update-description"]
        )


if __name__ == "__main__":
    unittest.main()
