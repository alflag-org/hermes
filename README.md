# Hermes

Hermes is an Atlas script release for operator-triggered infrastructure operations.
It is an operation gateway, not a daemon and not a convergence engine.

```text
Hermes = infrastructure operation gateway
```

It connects actual infrastructure state, Cataloga-style desired datasets, DNS zone
files, Proxmox inventory, and operator-readable reports. Mutating commands are dry-run
by default and require an explicit `--apply`.

## Atlas Release Layout

Hermes follows the Atlas script release shape:

```text
VERSION
commands/hermes.py
modules/hermes/
requirements.txt
```

Atlas adds the release `modules/` directory to `PYTHONPATH`, while
`commands/hermes.py` also inserts it for local execution.

## Installation

Install Hermes as a named Atlas script release, then regenerate shims when needed:

```bash
atlas scripts install git+https://github.com/alflag-org/hermes.git#master --name hermes
atlas runtime install
atlas scripts shims
```

For a local checkout:

```bash
atlas scripts install . --name hermes
atlas runtime install
atlas scripts shims
```

Atlas maps `commands/hermes.py` to the command name `hermes`. Operators should run
Hermes through Atlas:

```bash
atlas run hermes host check
```

Or add `/opt/atlas/shims` to `PATH` and use the generated shim:

```bash
export PATH="/opt/atlas/shims:$PATH"
hermes host check
```

The direct `commands/hermes.py` entrypoint exists for release-local development and
smoke tests only. Production execution should go through `atlas run` or the shim so
Atlas can provide the scripts runtime, `atlas_core`, host context, and JSONL run log.

## Configuration

Hermes config belongs under Atlas-owned configuration:

```text
/etc/atlas/hermes.yml
```

Set `HERMES_CONFIG` or pass `--config` to use a different path. Keep secrets out of
the file; store only environment variable names such as `token_id_env` and
`token_secret_env`.

See [examples/hermes.yml](examples/hermes.yml).

## CLI

Basic shape:

```bash
hermes <domain> <action> [options]
atlas run hermes <domain> <action> [options]
```

Host:

```bash
hermes host show --format yaml
hermes host check
```

Cataloga file datasets:

```bash
hermes cataloga validate --file examples/resources.yaml
hermes cataloga normalize --file examples/resources.yaml --format yaml
hermes --config examples/hermes.yml cataloga export --format yaml
hermes cataloga import --file examples/resources.yaml --format json
```

DNS:

```bash
hermes dns render-zone --zone alflag.internal --source examples/resources.yaml --output /tmp/alflag.internal.zone
hermes dns check-zone --zone alflag.internal --file /tmp/alflag.internal.zone
hermes --config examples/hermes.yml dns diff-zone --zone alflag.internal --file /tmp/alflag.internal.zone
hermes --config examples/hermes.yml dns apply-zone --zone alflag.internal --file /tmp/alflag.internal.zone
hermes --config examples/hermes.yml dns apply-zone --zone alflag.internal --file /tmp/alflag.internal.zone --apply
```

DNS apply performs:

```text
check -> backup current zone -> atomic replace -> reload command -> verify
```

Without `--apply`, it returns a machine-readable apply result with `dry_run: true`.

Proxmox:

```bash
hermes proxmox collect --site kanagawa01 --raw-file examples/proxmox-state.json
hermes proxmox normalize --site kanagawa01 --file examples/proxmox-state.json
hermes proxmox diff --site kanagawa01 --actual examples/proxmox-state.json --desired examples/resources.yaml
hermes proxmox sync-plan --site kanagawa01 --actual examples/proxmox-state.json --desired examples/resources.yaml
```

Live Proxmox collection and `sync --apply` require `proxmox.endpoint`,
`token_id_env`, and `token_secret_env`. Apply is limited to metadata actions from a
reviewed plan: `update-tags` and `update-description`.

Reports:

```bash
hermes report drift --site kanagawa01 --actual examples/proxmox-state.json --desired examples/resources.yaml
hermes report inventory --site kanagawa01 --actual examples/proxmox-state.json --format json
hermes report dns --zone alflag.internal --source examples/resources.yaml
```

## State

Hermes is stateless by default. Persist only reviewable artifacts:

```text
/var/lib/atlas/hermes/cache/
/var/lib/atlas/hermes/plans/
/var/lib/atlas/hermes/backups/
/var/lib/atlas/hermes/reports/
```

Atlas already records script runs, arguments, duration, and exit codes, so Hermes
does not implement a separate audit log.

## Verification

The test suite uses standard library `unittest`:

```bash
PYTHONPATH=modules python3 -m unittest discover -s tests -v
```
