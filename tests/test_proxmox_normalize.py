from __future__ import annotations

import unittest

from hermes.proxmox.normalize import normalize_state


class ProxmoxNormalizeTest(unittest.TestCase):
    def test_normalize_nested_node_guests(self) -> None:
        state = normalize_state(
            {
                "nodes": [
                    {
                        "node": "pve01",
                        "guests": [
                            {
                                "vmid": "240",
                                "name": "dns01",
                                "type": "qemu",
                                "tags": "dns;mgmt",
                                "ip": "10.10.10.240",
                            }
                        ],
                    }
                ]
            },
            "kanagawa01",
        )

        self.assertEqual(state["kind"], "proxmox-state")
        self.assertEqual(state["guests"][0]["vmid"], 240)
        self.assertEqual(state["guests"][0]["node"], "pve01")
        self.assertEqual(state["guests"][0]["tags"], ["dns", "mgmt"])


if __name__ == "__main__":
    unittest.main()
