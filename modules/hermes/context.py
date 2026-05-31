from __future__ import annotations

import os
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class HostProfile:
    name: str
    site: str | None = None
    zone: str | None = None
    role: str | None = None
    environment: str | None = None
    runtime_kind: str | None = None
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tags"] = list(self.tags)
        return data


@dataclass(frozen=True)
class AtlasPaths:
    home: str
    etc: str
    var: str
    runtime: str
    scripts_current_root: str
    logs: str
    cache: str
    config_file: str
    host_file: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def get_host_profile() -> HostProfile:
    try:
        from atlas_core import get_host

        host = get_host()
        return HostProfile(
            name=host.name,
            site=host.site,
            zone=host.zone,
            role=host.role,
            environment=host.environment,
            runtime_kind=host.runtime_kind,
            tags=tuple(host.tags or ()),
        )
    except Exception:
        return _load_host_from_file()


def get_paths() -> AtlasPaths:
    etc = os.environ.get("ATLAS_ETC_DIR", "/etc/atlas")
    home = os.environ.get("ATLAS_HOME", "/opt/atlas")
    var = os.environ.get("ATLAS_VAR_DIR", "/var/lib/atlas")
    runtime = os.environ.get("ATLAS_RUNTIME_DIR", str(Path(home) / "runtime"))
    current = os.environ.get("ATLAS_SCRIPTS_CURRENT_DIR", str(Path(home) / "scripts/current"))
    return AtlasPaths(
        home=home,
        etc=etc,
        var=var,
        runtime=runtime,
        scripts_current_root=current,
        logs=str(Path(var) / "logs"),
        cache=str(Path(var) / "cache"),
        config_file=str(Path(etc) / "config.yml"),
        host_file=os.environ.get("ATLAS_HOST_FILE", str(Path(etc) / "host.yml")),
    )


def _load_host_from_file() -> HostProfile:
    host_file = Path(os.environ.get("ATLAS_HOST_FILE", "/etc/atlas/host.yml"))
    if host_file.exists():
        data = yaml.safe_load(host_file.read_text(encoding="utf-8")) or {}
        tags = data.get("tags") or ()
        return HostProfile(
            name=str(data.get("name") or socket.gethostname()),
            site=_optional_string(data.get("site")),
            zone=_optional_string(data.get("zone")),
            role=_optional_string(data.get("role")),
            environment=_optional_string(data.get("environment")),
            runtime_kind=_optional_string(data.get("runtime_kind")),
            tags=tuple(str(tag) for tag in tags),
        )
    return HostProfile(name=socket.gethostname())


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
