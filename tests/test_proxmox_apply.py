from __future__ import annotations

import unittest
from unittest.mock import patch

from hermes.proxmox.client import apply_metadata_plan


class FakeConfigEndpoint:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def put(self, **payload: object) -> None:
        self.calls.append(payload)


class FakeGuest:
    def __init__(self, endpoint: FakeConfigEndpoint) -> None:
        self.config = endpoint


class FakeGuestCollection:
    def __init__(self, endpoint: FakeConfigEndpoint) -> None:
        self.endpoint = endpoint

    def __call__(self, vmid: int) -> FakeGuest:
        return FakeGuest(self.endpoint)


class FakeNode:
    def __init__(self, endpoint: FakeConfigEndpoint) -> None:
        self.qemu = FakeGuestCollection(endpoint)
        self.lxc = FakeGuestCollection(endpoint)


class FakeNodeCollection:
    def __init__(self, endpoint: FakeConfigEndpoint) -> None:
        self.endpoint = endpoint

    def __call__(self, node: str) -> FakeNode:
        return FakeNode(self.endpoint)


class FakeApi:
    def __init__(self, endpoint: FakeConfigEndpoint) -> None:
        self.nodes = FakeNodeCollection(endpoint)


class ProxmoxApplyTest(unittest.TestCase):
    def test_apply_metadata_plan_only_updates_reviewed_metadata_payloads(self) -> None:
        endpoint = FakeConfigEndpoint()
        actions = [
            {
                "action": "update-tags",
                "vmid": 240,
                "node": "pve01",
                "type": "qemu",
                "tags": ["dns", "mgmt"],
            },
            {
                "action": "update-description",
                "vmid": 240,
                "node": "pve01",
                "type": "qemu",
                "description": "Recursive DNS server",
            },
        ]

        with patch("hermes.proxmox.client._connect", return_value=FakeApi(endpoint)):
            result = apply_metadata_plan({}, actions)

        self.assertTrue(result["ok"])
        self.assertEqual(result["applied"], 2)
        self.assertEqual(
            endpoint.calls, [{"tags": "dns;mgmt"}, {"description": "Recursive DNS server"}]
        )


if __name__ == "__main__":
    unittest.main()
