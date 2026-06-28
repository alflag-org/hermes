from __future__ import annotations

import os
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from hermes.models import warning


WORKSPACE_MARKERS = (
    "ansible.cfg",
    "ansible/inventory",
    "inventory",
    "pyproject.toml",
    ".git",
)
PRIMARY_WORKSPACE_MARKERS = ("ansible.cfg", "ansible/inventory", "pyproject.toml", ".git")


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


def discover_context(
    *,
    workspace: str | None = None,
    site: str | None = None,
    config: dict[str, Any] | None = None,
    config_path: str | Path | None = None,
    cwd: str | Path | None = None,
) -> dict[str, Any]:
    selected_config = config or {}
    warnings: list[dict[str, Any]] = []
    workspace_path, workspace_warnings = discover_workspace(
        explicit=workspace,
        config=selected_config,
        cwd=Path(cwd) if cwd is not None else Path.cwd(),
    )
    warnings.extend(workspace_warnings)

    host = get_host_profile()
    selected_site = (
        site
        or _optional_string(selected_config.get("site"))
        or _optional_string((selected_config.get("defaults") or {}).get("site"))
        or host.site
        or _infer_site_from_workspace(workspace_path)
    )
    if selected_site is None:
        warnings.append(
            warning(
                "site-unknown",
                "site was not provided by --site, config, Atlas host context, or inventory layout",
            )
        )

    inventory_path = find_inventory_path(workspace_path, selected_site)
    if workspace_path is None:
        warnings.append(warning("workspace-not-found", "workspace could not be discovered"))
    elif inventory_path is None:
        warnings.append(
            warning(
                "inventory-not-found",
                "Daedalus inventory path was not found under the discovered workspace",
                source=str(workspace_path),
            )
        )

    atlas_available = atlas_context_available()
    return {
        "kind": "context",
        "version": "v1",
        "workspace": str(workspace_path) if workspace_path else None,
        "site": selected_site,
        "inventory_path": str(inventory_path) if inventory_path else None,
        "atlas_context_available": atlas_available,
        "config_path": str(config_path) if config_path else None,
        "mode": "atlas" if atlas_available else "local",
        "warnings": warnings,
    }


def discover_workspace(
    *,
    explicit: str | None = None,
    config: dict[str, Any] | None = None,
    cwd: Path | None = None,
) -> tuple[Path | None, list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.exists():
            warnings.append(warning("workspace-missing", "explicit workspace does not exist", source=str(path)))
        return path, warnings

    env_workspace = os.environ.get("HERMES_WORKSPACE")
    if env_workspace:
        path = Path(env_workspace).expanduser().resolve()
        if not path.exists():
            warnings.append(warning("workspace-missing", "HERMES_WORKSPACE does not exist", source=str(path)))
        return path, warnings

    search_from = (cwd or Path.cwd()).resolve()
    for candidate in (search_from, *search_from.parents):
        if any((candidate / marker).exists() for marker in PRIMARY_WORKSPACE_MARKERS):
            return candidate, warnings
    for candidate in (search_from, *search_from.parents):
        if any((candidate / marker).exists() for marker in WORKSPACE_MARKERS):
            return candidate, warnings

    selected_config = config or {}
    configured = selected_config.get("workspace") or (selected_config.get("defaults") or {}).get("workspace")
    if configured:
        path = Path(str(configured)).expanduser().resolve()
        if not path.exists():
            warnings.append(warning("workspace-missing", "configured workspace does not exist", source=str(path)))
        return path, warnings
    return None, warnings


def find_inventory_path(workspace: Path | None, site: str | None) -> Path | None:
    if workspace is None or not workspace.exists():
        return None
    candidates: list[Path] = []
    if site:
        candidates.extend(
            [
                workspace / "ansible" / "inventory" / "sites" / site,
                workspace / "inventory" / "sites" / site,
            ]
        )
    candidates.extend([workspace / "ansible" / "inventory", workspace / "inventory"])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def atlas_context_available() -> bool:
    try:
        import atlas_core  # noqa: F401

        return True
    except Exception:
        return False


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


def _infer_site_from_workspace(workspace: Path | None) -> str | None:
    if workspace is None or not workspace.exists():
        return None
    for base in (workspace / "ansible" / "inventory" / "sites", workspace / "inventory" / "sites"):
        if not base.exists() or not base.is_dir():
            continue
        sites = sorted(path.name for path in base.iterdir() if path.is_dir())
        if len(sites) == 1:
            return sites[0]
    return None
