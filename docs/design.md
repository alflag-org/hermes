# Hermes Design

Hermes is an Atlas-compatible read-only CLI for manifest-centered auditing and
projection planning. It is operator-triggered and stateless by default.

The core invariant is:

```text
host manifest = source of truth
Hermes = read-only verifier / reporter / projection planner
```

## System Boundaries

```text
Atlas    = runtime / release install / shim / host context / run log
Daedalus = Ansible convergence projection
Catalaga = catalog projection
Hermes   = manifest auditor, reporter, and projection planner
Themis   = future strict read-only checks/probes/preflight validation
Ares     = future dangerous operations: cutover, failover, rollback, break-glass
```

Hermes reads host manifests, Daedalus inventory, Cataloga export snapshots, Atlas host
context files, and captured actual-state files. It does not run Ansible, apply
convergence, or own desired state. It may generate projections, plans, diffs, and
reports for operators to review.

Strict read-only probes and preflight validation belong to future Themis scope.
Dangerous operational flows belong to future Ares scope.

## Source of Truth

Managed hosts are mastered by YAML manifests under:

```text
manifests/hosts/<site>/<host>.yml
```

Projection flow:

```text
host manifest -> Daedalus inventory projection
host manifest -> Cataloga dataset projection
host manifest -> Atlas host.yml projection
```

Daedalus inventory, Cataloga datasets, and Atlas host context must not become the
master of managed host identity. Hermes can render the expected projection and compare
it with supplied files, but it does not edit those files.

## Module Boundaries

```text
hermes.manifest  = load, schema policy, validation, manifest reports
hermes.daedalus  = inventory projection and inventory diff
hermes.cataloga  = dataset projection, dataset diff, import-plan artifact
hermes.atlas     = host context projection and host context diff
hermes.report    = operator-facing host and projection reports
```

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

The v0.1 manifest projection surface does not provide `--apply`. Hermes does not
provision Proxmox guests, cut over DNS, perform failover, run rollback, edit host
manifests, edit Ansible inventory, write Cataloga DB records, or make break-glass SSH
changes.

## Zabbix Retirement

Zabbix has been retired. Hermes does not implement Zabbix sync, host/item/template
management, or active monitoring integration. Historical mentions should be avoided
unless they are clearly marked as retired.

## Data Flow

Hermes reads:

- host manifests
- Cataloga export or snapshot YAML when passed explicitly
- Atlas host context YAML when passed explicitly
- Atlas host context when `atlas_core` is available
- `/etc/atlas/hermes.yml` or the path from `--config` / `HERMES_CONFIG`
- workspace roots from `--workspace`, `HERMES_WORKSPACE`, upward discovery, or config
- Daedalus-like YAML inventory files
- local DNS zone and Proxmox capture files when explicitly passed

Hermes writes only when an explicit output path is passed, or when an old transitional
`--apply` command is requested. The manifest, Daedalus, Cataloga, Atlas, and projection
report commands are read-only except for `hermes cataloga plan --output`, which writes a
local review artifact.
