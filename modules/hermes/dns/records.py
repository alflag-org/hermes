from __future__ import annotations

from typing import Any


SUPPORTED_TYPES = {"A", "AAAA", "CNAME", "TXT", "MX", "SRV"}


def records_from_dataset(dataset: dict[str, Any], zone: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for entry in dataset.get("records", []):
        records.append(normalize_record(entry, zone))
    dns = dataset.get("dns") or {}
    for entry in dns.get("records", []):
        records.append(normalize_record(entry, zone))
    for resource in dataset.get("resources", []):
        records.extend(_records_from_resource(resource, zone))
    return sorted(records, key=record_key)


def normalize_record(record: dict[str, Any], zone: str) -> dict[str, Any]:
    name = _relative_name(str(record.get("name") or record.get("host") or "@"), zone)
    record_type = str(record.get("type") or "A").upper()
    value = str(record.get("value") or record.get("target") or record.get("address") or "")
    result: dict[str, Any] = {"name": name, "type": record_type, "value": value}
    if record.get("ttl") is not None:
        result["ttl"] = int(record["ttl"])
    if record.get("priority") is not None:
        result["priority"] = int(record["priority"])
    return result


def record_key(record: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(record.get("name") or ""),
        str(record.get("type") or ""),
        str(record.get("priority") or ""),
        str(record.get("value") or ""),
    )


def record_tuple(record: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(record.get("name") or ""),
        str(record.get("type") or "").upper(),
        str(record.get("value") or ""),
        str(record.get("ttl") or ""),
        str(record.get("priority") or ""),
    )


def _records_from_resource(resource: dict[str, Any], zone: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    dns = resource.get("dns") or {}
    for record in dns.get("records", []):
        result.append(normalize_record(record, zone))
    name = dns.get("name") or dns.get("fqdn") or resource.get("fqdn") or resource.get("name")
    address = (
        dns.get("address")
        or dns.get("ip")
        or resource.get("address")
        or resource.get("ip")
        or resource.get("ipv4")
    )
    if name and address:
        result.append(normalize_record({"name": name, "type": "A", "value": address}, zone))
    return result


def _relative_name(name: str, zone: str) -> str:
    normalized_zone = zone.rstrip(".")
    normalized = name.rstrip(".")
    if normalized in {"", normalized_zone}:
        return "@"
    suffix = "." + normalized_zone
    if normalized.endswith(suffix):
        return normalized[: -len(suffix)]
    return normalized
