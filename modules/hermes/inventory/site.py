from __future__ import annotations


KANAGAWA01_FIXTURE = {
    "site": "kanagawa01",
    "networks": {
        "client": {"vlan": 100, "cidr": "10.10.0.0/24"},
        "mgmt": {"vlan": 110, "cidr": "10.10.10.0/24"},
        "dmz": {"vlan": 130, "cidr": "10.10.30.0/24"},
        "transit": {"vlan": 901, "cidr": "10.255.255.0/29"},
    },
}


def site_fixture(site: str) -> dict:
    if site == "kanagawa01":
        return KANAGAWA01_FIXTURE
    return {"site": site, "networks": {}}
