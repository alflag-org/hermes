# Hermes Commands

Safety categories:

- `read-only`: reads local or discovered state and prints a report.
- `plan/diff`: produces reviewable artifacts without mutation.
- `dry-run default mutation`: has an apply path, but defaults to `dry_run: true`.
- `transitional mutation`: retained existing low-risk mutation path, gated by `--apply`.
- `experimental`: present but not primary documented workflow.
- `future Ares candidate`: dangerous operation that does not belong in Hermes.

## Required Commands

| Command | Safety | Options | Example |
| --- | --- | --- | --- |
| `hermes --help` | read-only | | `hermes --help` |
| `hermes --version` | read-only | | `hermes --version` |
| `hermes context` | read-only | `--workspace`, `--site`, `--format`, `--output` | `hermes context --workspace tests/fixtures/daedalus-simple` |
| `hermes network summary` | read-only | `--site`, `--format`, `--output` | `hermes network summary --format markdown` |
| `hermes host show` | read-only | `--format` | `hermes host show --format yaml` |
| `hermes host check` | read-only | `--format` | `hermes host check` |
| `hermes host list` | read-only | `--workspace`, `--site`, `--zone`, `--group`, `--service`, `--format`, `--output` | `hermes host list --zone mgmt --workspace tests/fixtures/daedalus-simple` |
| `hermes host summary` | read-only | `--workspace`, `--site`, `--format`, `--output` | `hermes host summary --workspace tests/fixtures/daedalus-simple` |
| `hermes dns report` | read-only | `--workspace`, `--site`, `--format`, `--output` | `hermes dns report --workspace tests/fixtures/daedalus-simple` |
| `hermes report inventory` | read-only | `--workspace`, `--site`, `--actual`, `--format` | `hermes report inventory --workspace tests/fixtures/daedalus-simple` |
| `hermes report drift` | plan/diff | `--site`, `--actual`, `--desired`, `--format` | `hermes report drift --actual examples/proxmox-state.json --desired examples/resources.yaml` |
| `hermes report summary` | read-only | `--workspace`, `--site`, `--format`, `--output` | `hermes report summary --workspace tests/fixtures/daedalus-simple --format json` |
| `hermes maintenance sanity-check` | read-only | `--format` | `hermes maintenance sanity-check` |

## Cataloga

| Command | Safety | Notes |
| --- | --- | --- |
| `hermes cataloga validate --file PATH` | read-only | Validates a file dataset. |
| `hermes cataloga normalize --file PATH` | plan/diff | Prints normalized data, or writes only with `--output`. |
| `hermes cataloga export` | read-only | Reads file dataset configured in Hermes config. |
| `hermes cataloga import --file PATH` | plan/diff | Produces an import plan. It does not become a database service. |

## DNS

| Command | Safety | Notes |
| --- | --- | --- |
| `hermes dns report` | read-only | Inventory and file discovery only. It does not query live DNS, reload services, or modify zone files. |
| `hermes dns render-zone` | plan/diff | Renders a desired zone from a dataset. Writes only with `--output`. |
| `hermes dns check-zone` | read-only | Validates zone text with Hermes' parser. |
| `hermes dns diff-zone` | plan/diff | Compares desired zone text to a current file or configured zone file. |
| `hermes dns apply-zone` | dry-run default mutation / transitional mutation | Returns `dry_run: true` by default. `--apply` is required for replace/reload behavior. |
| `hermes dns upsert-record` | plan/diff | Produces a sync plan for a record upsert. |

DNS cutover workflows are future Ares candidates and are not implemented.

## Proxmox

| Command | Safety | Notes |
| --- | --- | --- |
| `hermes proxmox collect` | read-only | Reads live Proxmox only when explicit config and credentials are present. Captured files can be passed with `--raw-file`. |
| `hermes proxmox normalize` | read-only | Normalizes captured Proxmox state. |
| `hermes proxmox diff` | plan/diff | Compares actual and desired state. |
| `hermes proxmox sync-plan` | plan/diff | Produces reviewable metadata update actions. |
| `hermes proxmox sync` | dry-run default mutation / transitional mutation | Returns `dry_run: true` by default. `--apply` is limited to `update-tags` and `update-description`. |

Proxmox provisioning, lifecycle operations, rollback, and failover are not Hermes
commands.

## Unsupported Active Integrations

Zabbix, Prometheus management, Alertmanager management, Grafana management, Cloudflare
write operations, daemon mode, scheduler mode, and web UI are out of scope.
