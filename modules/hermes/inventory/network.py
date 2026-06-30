from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class NetworkDefinition:
    name: str
    vlan_id: int | None
    cidr: str | None
    gateway: str | None
    purpose: str
    status: str
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


KANAGAWA01_NETWORKS: tuple[NetworkDefinition, ...] = (
    NetworkDefinition(
        name="CLIENT",
        vlan_id=100,
        cidr="10.10.0.0/24",
        gateway="10.10.0.1",
        purpose="home client devices",
        status="active",
    ),
    NetworkDefinition(
        name="MGMT",
        vlan_id=110,
        cidr="10.10.10.0/24",
        gateway="10.10.10.1",
        purpose="management plane",
        status="active",
    ),
    NetworkDefinition(
        name="DMZ",
        vlan_id=130,
        cidr="10.10.30.0/24",
        gateway="10.10.30.1",
        purpose="public-facing / external-entry systems",
        status="active",
    ),
    NetworkDefinition(
        name="TRANSIT",
        vlan_id=901,
        cidr="10.255.255.0/29",
        gateway="10.255.255.1",
        purpose="IX2215 VRRP transit",
        status="active",
    ),
    NetworkDefinition(
        name="UNUSED_NATIVE",
        vlan_id=999,
        cidr=None,
        gateway=None,
        purpose="isolated unused native VLAN",
        status="active",
    ),
    NetworkDefinition(
        name="INTERNAL",
        vlan_id=120,
        cidr=None,
        gateway=None,
        purpose="removed legacy internal network",
        status="deprecated",
        reason="removed; not an active KANAGAWA01 network",
    ),
    NetworkDefinition(
        name="STORAGE",
        vlan_id=120,
        cidr=None,
        gateway=None,
        purpose="removed legacy storage network",
        status="deprecated",
        reason="removed; not an active KANAGAWA01 network",
    ),
    NetworkDefinition(
        name="OVERLAY",
        vlan_id=140,
        cidr=None,
        gateway=None,
        purpose="overlay network that was not adopted",
        status="deprecated",
        reason="removed / not adopted; not an active KANAGAWA01 network",
    ),
    NetworkDefinition(
        name="IOT",
        vlan_id=150,
        cidr=None,
        gateway=None,
        purpose="removed IoT network",
        status="deprecated",
        reason="removed; not an active KANAGAWA01 network",
    ),
)


def network_summary(site: str | None = "kanagawa01") -> dict[str, Any]:
    active = [network.to_dict() for network in KANAGAWA01_NETWORKS if network.status == "active"]
    deprecated = [
        network.to_dict() for network in KANAGAWA01_NETWORKS if network.status == "deprecated"
    ]
    warnings: list[dict[str, Any]] = []
    selected_site = site or "kanagawa01"
    if selected_site != "kanagawa01":
        warnings.append(
            {
                "code": "site-model-unavailable",
                "message": "only the KANAGAWA01 network model is currently bundled",
                "severity": "warning",
                "source": selected_site,
            }
        )
    return {
        "kind": "network-summary",
        "version": "v1",
        "site": selected_site,
        "active_networks": active,
        "deprecated_networks": deprecated,
        "statement": "Deprecated networks are retained for history only and are not active.",
        "warnings": warnings,
    }


def active_networks() -> dict[str, dict[str, Any]]:
    return {
        network.name.lower(): {
            "vlan": network.vlan_id,
            "cidr": network.cidr,
            "gateway": network.gateway,
        }
        for network in KANAGAWA01_NETWORKS
        if network.status == "active"
    }
