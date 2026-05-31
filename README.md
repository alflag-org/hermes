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
python3 commands/hermes.py host show --format yaml
python3 commands/hermes.py host check
```

Cataloga file datasets:

```bash
python3 commands/hermes.py cataloga validate --file examples/resources.yaml
python3 commands/hermes.py cataloga normalize --file examples/resources.yaml --format yaml
python3 commands/hermes.py --config examples/hermes.yml cataloga export --format yaml
python3 commands/hermes.py cataloga import --file examples/resources.yaml --format json
```

DNS:

```bash
python3 commands/hermes.py dns render-zone --zone alflag.internal --source examples/resources.yaml --output /tmp/alflag.internal.zone
python3 commands/hermes.py dns check-zone --zone alflag.internal --file /tmp/alflag.internal.zone
python3 commands/hermes.py --config examples/hermes.yml dns diff-zone --zone alflag.internal --file /tmp/alflag.internal.zone
python3 commands/hermes.py --config examples/hermes.yml dns apply-zone --zone alflag.internal --file /tmp/alflag.internal.zone
python3 commands/hermes.py --config examples/hermes.yml dns apply-zone --zone alflag.internal --file /tmp/alflag.internal.zone --apply
```

DNS apply performs:

```text
check -> backup current zone -> atomic replace -> reload command -> verify
```

Without `--apply`, it returns a machine-readable apply result with `dry_run: true`.

Proxmox:

```bash
python3 commands/hermes.py proxmox collect --site kanagawa01 --raw-file examples/proxmox-state.json
python3 commands/hermes.py proxmox normalize --site kanagawa01 --file examples/proxmox-state.json
python3 commands/hermes.py proxmox diff --site kanagawa01 --actual examples/proxmox-state.json --desired examples/resources.yaml
python3 commands/hermes.py proxmox sync-plan --site kanagawa01 --actual examples/proxmox-state.json --desired examples/resources.yaml
```

Live Proxmox collection and `sync --apply` require `proxmox.endpoint`,
`token_id_env`, and `token_secret_env`. Apply is limited to metadata actions from a
reviewed plan: `update-tags` and `update-description`.

Reports:

```bash
python3 commands/hermes.py report drift --site kanagawa01 --actual examples/proxmox-state.json --desired examples/resources.yaml
python3 commands/hermes.py report inventory --site kanagawa01 --actual examples/proxmox-state.json --format json
python3 commands/hermes.py report dns --zone alflag.internal --source examples/resources.yaml
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
