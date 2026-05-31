from __future__ import annotations

from typing import Any

from hermes.cataloga.dataset import normalize_dataset
from hermes.dns.records import records_from_dataset
from hermes.dns.zone import render_zone
from hermes.io import load_data


def render_zone_from_source(zone: str, source: str, ttl: int = 300) -> str:
    data = load_data(source)
    dataset = normalize_dataset(data) if "resources" in data or isinstance(data, list) else data
    records = records_from_dataset(dataset, zone)
    return render_zone(zone, records, ttl=ttl)
