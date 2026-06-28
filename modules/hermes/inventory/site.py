from __future__ import annotations

from hermes.inventory.network import active_networks

KANAGAWA01_FIXTURE = {"site": "kanagawa01", "networks": active_networks()}


def site_fixture(site: str) -> dict:
    if site == "kanagawa01":
        return KANAGAWA01_FIXTURE
    return {"site": site, "networks": {}}
