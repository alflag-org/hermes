# Hermes Design

Hermes is an Atlas script release for daily infrastructure operations. It is
operator-triggered and stateless by default.

## System Boundaries

```text
Atlas    = runtime / release install / shim / host context / run log
Daedalus = desired state and Ansible convergence
Hermes   = daily operations helper, inventory/report/plan generator
Themis   = future strict read-only checks/probes/preflight validation
Ares     = future dangerous operations: cutover, failover, rollback, break-glass
```

Hermes reads Daedalus inventory but does not run Ansible, apply convergence, or own
desired state. It may generate plans, diffs, and reports for operators to review.

Strict read-only probes and preflight validation belong to future Themis scope.
Dangerous operational flows belong to future Ares scope.

## Plan-First Policy

The default operation is read, inspect, report, plan, or diff. Mutation must be explicit.

```text
default = read / inspect / report / plan / diff
mutation = never implicit
mutation = only allowed with explicit --apply
dangerous mutation = not Hermes
```

Existing mutating paths are transitional:

- `hermes dns apply-zone` checks, plans, and returns `dry_run: true` unless `--apply`
  is passed.
- `hermes proxmox sync` returns `dry_run: true` unless `--apply` is passed, and apply
  is limited to reviewed metadata updates.

Hermes does not provision Proxmox guests, cut over DNS, perform failover, run rollback,
or make break-glass SSH changes.

## Zabbix Retirement

Zabbix has been retired. Hermes does not implement Zabbix sync, host/item/template
management, or active monitoring integration. Historical mentions should be avoided
unless they are clearly marked as retired.

## Data Flow

Hermes reads:

- Atlas host context when `atlas_core` is available
- `/etc/atlas/hermes.yml` or the path from `--config` / `HERMES_CONFIG`
- workspace roots from `--workspace`, `HERMES_WORKSPACE`, upward discovery, or config
- Daedalus-like YAML inventory files
- local DNS zone and Proxmox capture files when explicitly passed

Hermes writes only when an explicit output path is passed, or when a transitional
`--apply` command is requested.
