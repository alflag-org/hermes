# Hermes

Hermes is a small read-only CLI for auditing host manifest YAML and the projections
derived from it. The host manifest is the source of truth; Daedalus inventory,
Catalaga datasets, and Atlas host context are projections that Hermes can render,
diff, and report.

Hermes is not an operations gateway, daemon, monitoring system, scheduler,
convergence engine, or dangerous operations runner.

```text
host manifest = source of truth
Daedalus inventory = Ansible convergence projection
Catalaga dataset = catalog projection
Atlas host.yml = runtime context projection
Hermes = read-only auditor / reporter / projection planner

Atlas    = runtime / release install / shim / host context / run log
Daedalus = Ansible convergence projection
Hermes   = manifest auditor, reporter, and projection planner
Themis   = future strict read-only checks/probes/preflight validation
Ares     = future dangerous operations: cutover, failover, rollback, break-glass
```

Zabbix has been retired. Hermes does not include Zabbix sync, host/item/template logic,
or any active monitoring integration.

## Safety Model

Default Hermes behavior is read, inspect, report, plan, or diff. Mutation is never
implicit. Transitional mutation commands require explicit `--apply` and remain dry-run
by default.

Allowed by default:

- local file reads
- host manifest validation
- Daedalus, Cataloga, and Atlas projection rendering
- projection diff and report generation
- Daedalus inventory reads
- KANAGAWA01 network model reads
- JSON, YAML, Markdown, and text report generation
- DNS zone render, check, and diff
- Proxmox state normalization from captured files
- dry-run plans
- output file writes only when `--output` is passed

Out of scope:

- editing host manifests
- editing Daedalus inventory or Ansible host_vars
- writing Cataloga DB records or calling Cataloga write APIs
- Ansible apply or converge
- daemon or scheduler behavior
- monitoring sync
- Zabbix integration
- Cloudflare write operations
- Proxmox VM/LXC provisioning
- DNS cutover workflows
- failover, rollback, or break-glass SSH changes

## KANAGAWA01 Networks

Active:

| VLAN | Name | CIDR | Gateway | Purpose |
| ---: | --- | --- | --- | --- |
| 100 | CLIENT | 10.10.0.0/24 | 10.10.0.1 | home client devices |
| 110 | MGMT | 10.10.10.0/24 | 10.10.10.1 | management plane |
| 130 | DMZ | 10.10.30.0/24 | 10.10.30.1 | public-facing / external-entry systems |
| 901 | TRANSIT | 10.255.255.0/29 | 10.255.255.1 | IX2215 VRRP transit |
| 999 | UNUSED_NATIVE | | | isolated unused native VLAN |

Deprecated networks are historical only and are not active: `INTERNAL`, `STORAGE`,
`OVERLAY`, and `IOT`.

## Atlas Release Layout

Hermes keeps the Atlas script release shape:

```text
VERSION
commands/hermes.py
modules/hermes/
requirements.txt
```

`commands/hermes.py` is a thin entrypoint. Atlas adds `modules/` to `PYTHONPATH`; the
entrypoint also inserts it for checkout-local smoke tests.

## Quick Start

Install from the repository as a named Atlas script release:

```bash
atlas scripts install git+https://github.com/alflag-org/hermes.git#master --name hermes
atlas runtime install
atlas scripts shims
```

Run through Atlas:

```bash
atlas run hermes context
atlas run hermes network summary
atlas run hermes host list --workspace tests/fixtures/daedalus-simple
atlas run hermes manifest check --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01
atlas run hermes daedalus render --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01
atlas run hermes dns report --workspace tests/fixtures/daedalus-simple
atlas run hermes report summary --workspace tests/fixtures/daedalus-simple --format markdown
```

Or use the generated shim:

```bash
export PATH="/opt/atlas/shims:$PATH"
hermes context
hermes network summary
hermes report summary --format markdown
```

## Configuration

Hermes config belongs under Atlas-owned configuration:

```text
/etc/atlas/hermes.yml
```

Set `HERMES_CONFIG` or pass `--config` to use a different path. Keep secrets out of
the file; store only environment variable names such as `token_id_env` and
`token_secret_env`.

See [examples/hermes.yml](examples/hermes.yml).

## Command Categories

Read-only:

- `hermes --help`
- `hermes --version`
- `hermes context`
- `hermes manifest list`
- `hermes manifest summary`
- `hermes manifest check`
- `hermes network summary`
- `hermes host show`
- `hermes host check`
- `hermes host list`
- `hermes host summary`
- `hermes dns report`
- `hermes report hosts`
- `hermes report inventory`
- `hermes report summary`
- `hermes maintenance sanity-check`

Plan/diff:

- `hermes daedalus render`
- `hermes daedalus diff`
- `hermes cataloga render`
- `hermes cataloga diff`
- `hermes cataloga plan`
- `hermes atlas render-host`
- `hermes atlas diff-host`
- `hermes report projections`
- `hermes dns render-zone`
- `hermes dns check-zone`
- `hermes dns diff-zone`
- `hermes proxmox normalize`
- `hermes proxmox diff`
- `hermes proxmox sync-plan`
- `hermes report drift`

Dry-run default transitional mutation:

- `hermes dns apply-zone`
- `hermes proxmox sync`

Cataloga file dataset commands remain file-oriented:

- `hermes cataloga render`
- `hermes cataloga diff`
- `hermes cataloga plan`
- `hermes cataloga validate`
- `hermes cataloga normalize`
- `hermes cataloga export`
- `hermes cataloga import`

## Common Examples

```bash
hermes --help
hermes --version
hermes context
hermes context --workspace tests/fixtures/daedalus-simple

hermes manifest list --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01
hermes manifest summary --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01 --format markdown
hermes manifest check --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01

hermes daedalus render --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01
hermes daedalus diff --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01 --inventory tests/fixtures/manifest-goal/ansible/inventories/default/hosts.yml

hermes cataloga render --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01
hermes cataloga diff --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01 --catalog tests/fixtures/manifest-goal/catalog/cataloga-hosts.yaml
hermes cataloga plan --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01 --catalog tests/fixtures/manifest-goal/catalog/cataloga-hosts.yaml --output /tmp/cataloga-host-import.yaml

hermes atlas render-host --manifest tests/fixtures/manifest-goal/manifests/hosts/kanagawa01/web01.yml
hermes atlas diff-host --manifest tests/fixtures/manifest-goal/manifests/hosts/kanagawa01/web01.yml --host-file tests/fixtures/manifest-goal/atlas/web01-host.yml

hermes report hosts --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01 --format markdown
hermes report projections --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01 --inventory tests/fixtures/manifest-goal/ansible/inventories/default/hosts.yml --catalog tests/fixtures/manifest-goal/catalog/cataloga-hosts.yaml

hermes network summary
hermes network summary --format json
hermes network summary --format markdown

hermes host show
hermes host check
hermes host list --workspace tests/fixtures/daedalus-simple
hermes host list --zone mgmt --workspace tests/fixtures/daedalus-simple
hermes host summary --workspace tests/fixtures/daedalus-simple

hermes dns report --workspace tests/fixtures/daedalus-simple

hermes report summary --workspace tests/fixtures/daedalus-simple
hermes report summary --workspace tests/fixtures/daedalus-simple --format markdown
hermes report summary --workspace tests/fixtures/daedalus-simple --format json
```

Existing plan-first examples:

```bash
hermes cataloga validate --file examples/resources.yaml
hermes cataloga normalize --file examples/resources.yaml --format yaml

hermes dns render-zone --zone alflag.internal --source examples/resources.yaml --output /tmp/alflag.internal.zone
hermes dns check-zone --zone alflag.internal --file /tmp/alflag.internal.zone
hermes dns diff-zone --zone alflag.internal --file /tmp/alflag.internal.zone
hermes --config examples/hermes.yml dns apply-zone --zone alflag.internal --file /tmp/alflag.internal.zone

hermes proxmox normalize --file examples/proxmox-state.json
hermes proxmox diff --actual examples/proxmox-state.json --desired examples/resources.yaml
hermes proxmox sync-plan --actual examples/proxmox-state.json --desired examples/resources.yaml
```

Without `--apply`, `dns apply-zone` and `proxmox sync` return `dry_run: true`.

## Local Development

Hermes must work without Atlas for tests and checkout-local smoke checks:

```bash
mise exec python@3.11 -- python -m pip install -e '.[dev]'
mise exec python@3.11 -- ruff check .
mise exec python@3.11 -- ruff format --check .
mise exec python@3.11 -- pytest

PYTHONPATH=modules python3 commands/hermes.py --help
PYTHONPATH=modules python3 -m hermes --help
PYTHONPATH=modules python3 -m unittest discover -s tests -v
pytest
```

CI runs dependency install, editable install, `ruff check .`, and `pytest`.

## More Documentation

- [docs/design.md](docs/design.md)
- [docs/source-of-truth.md](docs/source-of-truth.md)
- [docs/host-manifest.md](docs/host-manifest.md)
- [docs/commands.md](docs/commands.md)
- [docs/atlas-integration.md](docs/atlas-integration.md)
- [docs/examples.md](docs/examples.md)
