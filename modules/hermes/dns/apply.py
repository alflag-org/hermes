from __future__ import annotations

import shutil
import shlex
import subprocess
from pathlib import Path
from typing import Any

from hermes.dns.records import record_tuple
from hermes.dns.zone import parse_zone_records, validate_zone_text
from hermes.errors import ExternalCommandError, UsageError
from hermes.io import read_text
from hermes.plan import apply_result, now_iso


def diff_zone_text(zone: str, desired_text: str, current_text: str | None) -> dict[str, Any]:
    desired_records = {record_tuple(record): record for record in parse_zone_records(desired_text)}
    current_records = {
        record_tuple(record): record for record in parse_zone_records(current_text or "")
    }
    actions: list[dict[str, Any]] = []
    for key, record in sorted(desired_records.items()):
        if key not in current_records:
            actions.append({"action": "upsert-record", "zone": zone, **record})
    for key, record in sorted(current_records.items()):
        if key not in desired_records:
            actions.append({"action": "delete-record", "zone": zone, **record})
    return {
        "kind": "dns-zone-diff",
        "version": "v1",
        "zone": zone,
        "actions": actions,
    }


def apply_zone_file(
    zone: str, desired_file: str, zone_config: dict[str, Any], apply: bool
) -> dict[str, Any]:
    desired = read_text(desired_file)
    check = validate_zone_text(zone, desired)
    if not check["ok"]:
        return apply_result(False, 0, 1, dry_run=not apply, details=[check])
    check_command = zone_config.get("check_command")
    if apply and check_command:
        _run_zone_check(str(check_command), zone, desired_file)
    zone_file = zone_config.get("zone_file")
    if not zone_file:
        raise UsageError(f"dns.zones.{zone}.zone_file is required")
    current_path = Path(zone_file)
    current_text = current_path.read_text(encoding="utf-8") if current_path.exists() else ""
    diff = diff_zone_text(zone, desired, current_text)
    if not apply:
        return apply_result(True, len(diff["actions"]), 0, dry_run=True, details=[diff])

    backup_path = _backup_current(zone, current_path, zone_config)
    tmp_path = current_path.with_suffix(current_path.suffix + ".tmp")
    current_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(desired, encoding="utf-8")
    tmp_path.replace(current_path)
    reload_command = zone_config.get("reload_command")
    if reload_command:
        _run_command(str(reload_command))
    verify = validate_zone_text(zone, current_path.read_text(encoding="utf-8"))
    return apply_result(
        verify["ok"],
        len(diff["actions"]),
        0 if verify["ok"] else 1,
        details=[diff, {"backup": str(backup_path) if backup_path else None}, verify],
    )


def _backup_current(zone: str, current_path: Path, zone_config: dict[str, Any]) -> Path | None:
    if not current_path.exists():
        return None
    backup_dir = Path(zone_config.get("backup_dir") or current_path.parent / ".hermes-backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_iso().replace(":", "").replace("-", "")
    backup_path = backup_dir / f"{zone}.{stamp}.zone"
    shutil.copy2(current_path, backup_path)
    return backup_path


def _run_command(command: str) -> None:
    completed = subprocess.run(command, shell=True, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise ExternalCommandError(
            f"command failed ({completed.returncode}): {command}\n{completed.stderr.strip()}"
        )


def _run_zone_check(command: str, zone: str, zone_file: str) -> None:
    if "{zone}" in command or "{file}" in command:
        rendered = command.format(zone=shlex.quote(zone), file=shlex.quote(zone_file))
    else:
        rendered = f"{command} {shlex.quote(zone)} {shlex.quote(zone_file)}"
    _run_command(rendered)
