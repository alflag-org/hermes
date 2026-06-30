from __future__ import annotations

import re

ACTIVE_ZONES = ("client", "mgmt", "dmz", "transit", "unused_native")
DEPRECATED_ZONES = ("internal", "storage", "overlay", "iot")
KNOWN_LIFECYCLES = ("active", "planned", "inactive", "retired")
KNOWN_PROVIDER_TYPES = ("proxmox", "static")
KNOWN_PLATFORM_TYPES = ("vm", "lxc", "baremetal", "linux", "container")
ZABBIX_VALUES = ("zabbix", "svc_zabbix", "zabbix_agent", "zabbix_server", "zabbix_template")

SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def is_normalized_slug(value: str | None) -> bool:
    return bool(value and SLUG_RE.match(value))


def normalized_tag(value: str) -> str:
    return value.replace("_", "-")
