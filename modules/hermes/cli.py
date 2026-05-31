from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable

from hermes import version
from hermes.cataloga.client import import_plan, load_dataset_from_config
from hermes.cataloga.dataset import normalize_dataset, validate_dataset
from hermes.config import get_default_format, get_default_site, load_config
from hermes.context import get_host_profile, get_paths
from hermes.dns.apply import apply_zone_file, diff_zone_text
from hermes.dns.records import normalize_record
from hermes.dns.render import render_zone_from_source
from hermes.dns.zone import validate_zone_text
from hermes.errors import HermesError, UsageError
from hermes.inventory.site import site_fixture
from hermes.io import load_data, read_text, write_data, write_text
from hermes.output import emit
from hermes.plan import apply_result, sync_plan
from hermes.proxmox.client import apply_metadata_plan, collect as collect_proxmox
from hermes.proxmox.diff import diff_state, plan_from_diff
from hermes.proxmox.normalize import normalize_state
from hermes.report.drift import drift_report
from hermes.report.inventory import inventory_report


Handler = Callable[[argparse.Namespace, dict[str, Any]], Any]


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        result = args.handler(args, config)
        if result is not None:
            fmt = getattr(args, "format", None) or get_default_format(config)
            emit(result, fmt)
    except HermesError as exc:
        print(f"hermes: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes")
    parser.add_argument("--config", help="Path to /etc/atlas/hermes.yml compatible config")
    parser.add_argument("--version", action="version", version=f"%(prog)s {version()}")
    subparsers = parser.add_subparsers(dest="domain", required=True)
    _add_host(subparsers)
    _add_cataloga(subparsers)
    _add_dns(subparsers)
    _add_proxmox(subparsers)
    _add_report(subparsers)
    _add_maintenance(subparsers)
    return parser


def _add_host(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("host", help="Inspect Atlas host profile")
    actions = parser.add_subparsers(dest="action", required=True)
    show = actions.add_parser("show")
    _format_arg(show)
    show.set_defaults(handler=_host_show)
    check = actions.add_parser("check")
    _format_arg(check)
    check.set_defaults(handler=_host_check)


def _add_cataloga(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("cataloga", help="File-based Cataloga dataset operations")
    actions = parser.add_subparsers(dest="action", required=True)
    validate = actions.add_parser("validate")
    validate.add_argument("--file", required=True)
    _format_arg(validate, default="text")
    validate.set_defaults(handler=_cataloga_validate)
    normalize = actions.add_parser("normalize")
    normalize.add_argument("--file", required=True)
    normalize.add_argument("--output")
    _format_arg(normalize, default="yaml")
    normalize.set_defaults(handler=_cataloga_normalize)
    export = actions.add_parser("export")
    _format_arg(export, default="yaml")
    export.set_defaults(handler=_cataloga_export)
    import_cmd = actions.add_parser("import")
    import_cmd.add_argument("--file", required=True)
    import_cmd.add_argument("--dry-run", action="store_true", default=True)
    _format_arg(import_cmd, default="json")
    import_cmd.set_defaults(handler=_cataloga_import)


def _add_dns(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("dns", help="Render, check, diff, and safely apply NSD zones")
    actions = parser.add_subparsers(dest="action", required=True)
    render = actions.add_parser("render-zone")
    render.add_argument("--zone", required=True)
    render.add_argument("--source", required=True)
    render.add_argument("--output")
    render.add_argument("--ttl", type=int, default=300)
    _format_arg(render, default="text")
    render.set_defaults(handler=_dns_render_zone)
    check = actions.add_parser("check-zone")
    check.add_argument("--zone", required=True)
    check.add_argument("--file", required=True)
    _format_arg(check)
    check.set_defaults(handler=_dns_check_zone)
    diff = actions.add_parser("diff-zone")
    diff.add_argument("--zone", required=True)
    diff.add_argument("--file", required=True, help="Desired zone file")
    diff.add_argument("--current", help="Current zone file; defaults to config dns.zones.<zone>.zone_file")
    _format_arg(diff, default="json")
    diff.set_defaults(handler=_dns_diff_zone)
    apply = actions.add_parser("apply-zone")
    apply.add_argument("--zone", required=True)
    apply.add_argument("--file", required=True, help="Desired zone file")
    apply.add_argument("--apply", action="store_true")
    _format_arg(apply, default="json")
    apply.set_defaults(handler=_dns_apply_zone)
    upsert = actions.add_parser("upsert-record")
    upsert.add_argument("--zone", required=True)
    upsert.add_argument("--name", required=True)
    upsert.add_argument("--type", required=True)
    upsert.add_argument("--value", required=True)
    upsert.add_argument("--ttl", type=int)
    _format_arg(upsert, default="json")
    upsert.set_defaults(handler=_dns_upsert_record)


def _add_proxmox(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("proxmox", help="Collect and compare Proxmox inventory")
    actions = parser.add_subparsers(dest="action", required=True)
    collect = actions.add_parser("collect")
    collect.add_argument("--site")
    collect.add_argument("--raw-file", help="Use a captured API payload instead of live Proxmox")
    collect.add_argument("--output")
    _format_arg(collect, default="json")
    collect.set_defaults(handler=_proxmox_collect)
    normalize = actions.add_parser("normalize")
    normalize.add_argument("--file", required=True)
    normalize.add_argument("--site")
    _format_arg(normalize, default="json")
    normalize.set_defaults(handler=_proxmox_normalize)
    diff = actions.add_parser("diff")
    diff.add_argument("--site")
    diff.add_argument("--actual", required=True)
    diff.add_argument("--desired", required=True)
    _format_arg(diff, default="json")
    diff.set_defaults(handler=_proxmox_diff)
    sync_plan_cmd = actions.add_parser("sync-plan")
    sync_plan_cmd.add_argument("--site")
    sync_plan_cmd.add_argument("--actual", required=True)
    sync_plan_cmd.add_argument("--desired", required=True)
    sync_plan_cmd.add_argument("--output")
    _format_arg(sync_plan_cmd, default="json")
    sync_plan_cmd.set_defaults(handler=_proxmox_sync_plan)
    sync = actions.add_parser("sync")
    sync.add_argument("--plan", required=True)
    sync.add_argument("--apply", action="store_true")
    _format_arg(sync, default="json")
    sync.set_defaults(handler=_proxmox_sync)


def _add_report(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("report", help="Generate operator reports")
    actions = parser.add_subparsers(dest="action", required=True)
    drift = actions.add_parser("drift")
    drift.add_argument("--site")
    drift.add_argument("--actual", required=True)
    drift.add_argument("--desired", required=True)
    _format_arg(drift, default="text")
    drift.set_defaults(handler=_report_drift)
    inventory = actions.add_parser("inventory")
    inventory.add_argument("--site")
    inventory.add_argument("--actual", required=True)
    _format_arg(inventory, default="text")
    inventory.set_defaults(handler=_report_inventory)
    dns = actions.add_parser("dns")
    dns.add_argument("--zone", required=True)
    dns.add_argument("--source")
    dns.add_argument("--file")
    _format_arg(dns, default="text")
    dns.set_defaults(handler=_report_dns)


def _add_maintenance(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("maintenance", help="One-shot sanity checks and helpers")
    actions = parser.add_subparsers(dest="action", required=True)
    sanity = actions.add_parser("sanity-check")
    _format_arg(sanity)
    sanity.set_defaults(handler=_maintenance_sanity_check)


def _format_arg(parser: argparse.ArgumentParser, default: str | None = "text") -> None:
    parser.add_argument("--format", choices=("text", "json", "yaml"), default=default)


def _host_show(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "host-profile",
        "version": "v1",
        "host": get_host_profile().to_dict(),
        "paths": get_paths().to_dict(),
        "hermes_config_loaded": bool(config),
    }


def _host_check(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    host = get_host_profile()
    paths = get_paths()
    errors: list[str] = []
    checks = [f"host={host.name}", f"atlas_etc={paths.etc}", f"atlas_var={paths.var}"]
    if not host.name:
        errors.append("host.name is empty")
    return {"kind": "host-check", "version": "v1", "ok": not errors, "checks": checks, "errors": errors}


def _cataloga_validate(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    return validate_dataset(load_data(args.file))


def _cataloga_normalize(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any] | None:
    data = normalize_dataset(load_data(args.file))
    if args.output:
        write_data(args.output, data)
        return None
    return data


def _cataloga_export(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    return load_dataset_from_config(config)


def _cataloga_import(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    return import_plan(args.file)


def _dns_render_zone(args: argparse.Namespace, config: dict[str, Any]) -> str | None:
    text = render_zone_from_source(args.zone, args.source, args.ttl)
    if args.output:
        write_text(args.output, text)
        return None
    return text


def _dns_check_zone(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    return validate_zone_text(args.zone, read_text(args.file))


def _dns_diff_zone(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    current = _current_zone_text(args.zone, args.current, config)
    return diff_zone_text(args.zone, read_text(args.file), current)


def _dns_apply_zone(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    zone_config = _zone_config(config, args.zone)
    return apply_zone_file(args.zone, args.file, zone_config, args.apply)


def _dns_upsert_record(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    record = normalize_record(
        {"name": args.name, "type": args.type, "value": args.value, "ttl": args.ttl},
        args.zone,
    )
    return sync_plan(None, "dns", [{"action": "upsert-record", "zone": args.zone, **record}])


def _proxmox_collect(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any] | None:
    site = get_default_site(config, args.site)
    state = normalize_state(load_data(args.raw_file), site) if args.raw_file else collect_proxmox(config, site)
    if args.output:
        write_data(args.output, state, "json")
        return None
    return state


def _proxmox_normalize(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    return normalize_state(load_data(args.file), get_default_site(config, args.site))


def _proxmox_diff(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    return diff_state(load_data(args.actual), load_data(args.desired), get_default_site(config, args.site))


def _proxmox_sync_plan(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any] | None:
    plan = plan_from_diff(
        diff_state(load_data(args.actual), load_data(args.desired), get_default_site(config, args.site))
    )
    if args.output:
        write_data(args.output, plan, "json")
        return None
    return plan


def _proxmox_sync(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    plan = load_data(args.plan)
    actions = plan.get("actions", [])
    if not args.apply:
        return apply_result(True, len(actions), dry_run=True, details=[plan])
    unsupported = [action for action in actions if action.get("action") not in {"update-tags", "update-description"}]
    if unsupported:
        raise UsageError("Proxmox sync apply supports only tag/description actions")
    return apply_metadata_plan(config, actions)


def _report_drift(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    return drift_report(load_data(args.actual), load_data(args.desired), get_default_site(config, args.site))


def _report_inventory(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    return inventory_report(load_data(args.actual), get_default_site(config, args.site))


def _report_dns(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    if args.source:
        zone_text = render_zone_from_source(args.zone, args.source)
    elif args.file:
        zone_text = read_text(args.file)
    else:
        raise UsageError("report dns requires --source or --file")
    check = validate_zone_text(args.zone, zone_text)
    return {
        "kind": "dns-report",
        "version": "v1",
        "zone": args.zone,
        "ok": check["ok"],
        "errors": check["errors"],
    }


def _maintenance_sanity_check(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    host = get_host_profile()
    site = get_default_site(config, host.site)
    return {
        "kind": "maintenance-sanity-check",
        "version": "v1",
        "ok": True,
        "host": host.to_dict(),
        "site": site,
        "site_fixture": site_fixture(site or "kanagawa01"),
    }


def _zone_config(config: dict[str, Any], zone: str) -> dict[str, Any]:
    zones = ((config.get("dns") or {}).get("zones") or {})
    selected = zones.get(zone)
    if not isinstance(selected, dict):
        raise UsageError(f"dns.zones.{zone} is required in Hermes config")
    return selected


def _current_zone_text(zone: str, explicit_path: str | None, config: dict[str, Any]) -> str:
    path = explicit_path
    if path is None:
        zones = ((config.get("dns") or {}).get("zones") or {})
        path = (zones.get(zone) or {}).get("zone_file")
    if not path:
        return ""
    target = Path(path)
    return target.read_text(encoding="utf-8") if target.exists() else ""
