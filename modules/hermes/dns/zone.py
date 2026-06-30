from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from hermes.dns.records import SUPPORTED_TYPES, record_key


def render_zone(
    zone: str,
    records: list[dict[str, Any]],
    *,
    ttl: int = 300,
    serial: int | None = None,
    nameserver: str = "ns1",
    contact: str = "hostmaster",
) -> str:
    selected_serial = serial or int(datetime.now(timezone.utc).strftime("%Y%m%d%H"))
    ns_fqdn = _fqdn(nameserver, zone)
    contact_fqdn = _fqdn(contact, zone)
    lines = [
        f"$ORIGIN {zone.rstrip('.')}.",
        f"$TTL {ttl}",
        f"@ IN SOA {ns_fqdn} {contact_fqdn} (",
        f"  {selected_serial} ; serial",
        "  3600 ; refresh",
        "  900 ; retry",
        "  1209600 ; expire",
        "  300 ; minimum",
        ")",
        f"@ IN NS {_relative_target(nameserver, zone)}",
    ]
    for record in sorted(records, key=record_key):
        lines.append(format_record(record))
    return "\n".join(lines) + "\n"


def format_record(record: dict[str, Any]) -> str:
    name = str(record.get("name") or "@")
    ttl = f"{int(record['ttl'])} " if record.get("ttl") is not None else ""
    record_type = str(record.get("type") or "A").upper()
    value = str(record.get("value") or "")
    if record_type == "TXT" and not (value.startswith('"') and value.endswith('"')):
        value = '"' + value.replace('"', '\\"') + '"'
    if record_type in {"MX", "SRV"} and record.get("priority") is not None:
        value = f"{int(record['priority'])} {value}"
    return f"{name} {ttl}IN {record_type} {value}"


def validate_zone_text(zone: str, text: str) -> dict[str, Any]:
    errors: list[str] = []
    has_soa = False
    in_soa_block = False
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split(";", 1)[0].strip()
        if in_soa_block:
            if ")" in line:
                in_soa_block = False
            continue
        if not line or line.startswith("$") or line in {"(", ")"}:
            continue
        if " SOA " in f" {line} ":
            has_soa = True
            if "(" in line and ")" not in line:
                in_soa_block = True
            continue
        if line.startswith(")") or line.startswith("("):
            continue
        parts = line.split()
        if len(parts) < 4:
            errors.append(f"line {line_number}: expected '<name> [ttl] IN <type> <value>'")
            continue
        if "IN" not in parts:
            errors.append(f"line {line_number}: missing IN class")
            continue
        record_type = (
            parts[parts.index("IN") + 1].upper() if parts.index("IN") + 1 < len(parts) else ""
        )
        if record_type and record_type not in SUPPORTED_TYPES and record_type not in {"SOA", "NS"}:
            errors.append(f"line {line_number}: unsupported record type {record_type}")
    if not has_soa:
        errors.append("missing SOA record")
    return {
        "kind": "dns-zone-check",
        "version": "v1",
        "zone": zone,
        "ok": not errors,
        "errors": errors,
    }


def parse_zone_records(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    in_soa_block = False
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if in_soa_block:
            if ")" in line:
                in_soa_block = False
            continue
        if not line or line.startswith("$") or line in {"(", ")"}:
            continue
        if " SOA " in f" {line} ":
            if "(" in line and ")" not in line:
                in_soa_block = True
            continue
        parts = line.split()
        if "IN" not in parts:
            continue
        in_index = parts.index("IN")
        name = parts[0]
        ttl = None
        if in_index == 2:
            try:
                ttl = int(parts[1])
            except ValueError:
                ttl = None
        record_type = parts[in_index + 1].upper()
        if record_type in {"NS", "SOA"}:
            continue
        value_parts = parts[in_index + 2 :]
        record: dict[str, Any] = {"name": name, "type": record_type, "value": " ".join(value_parts)}
        if ttl is not None:
            record["ttl"] = ttl
        records.append(record)
    return records


def _fqdn(name: str, zone: str) -> str:
    if name.endswith("."):
        return name
    if "." in name:
        return name + "."
    return f"{name}.{zone.rstrip('.')}."


def _relative_target(name: str, zone: str) -> str:
    if name.endswith("."):
        suffix = "." + zone.rstrip(".") + "."
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name
