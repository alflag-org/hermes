# Hermes Examples

The examples below use the repository fixture workspace:

```text
tests/fixtures/daedalus-simple
tests/fixtures/manifest-goal
```

## Manifest Check

```bash
hermes manifest check --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01
```

```text
ok: true
hosts: 2
```

## Daedalus Projection

```bash
hermes daedalus render --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01
```

```yaml
all:
  children:
    default:
      children:
        dmz:
          hosts:
            web01:
              ansible_host: 10.10.30.21
```

```bash
hermes daedalus diff \
  --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01 \
  --inventory tests/fixtures/manifest-goal/ansible/inventories/default/hosts.yml \
  --format markdown
```

## Cataloga Projection

```bash
hermes cataloga render --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01
```

```yaml
version: 1
resources:
  - id: host-control01
    type: host
    name: control01
```

```bash
hermes cataloga plan \
  --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01 \
  --catalog tests/fixtures/manifest-goal/catalog/cataloga-hosts.yaml \
  --output /tmp/cataloga-host-import.yaml
```

The plan command writes only the requested local artifact and does not call Cataloga.

## Atlas Projection

```bash
hermes atlas render-host --manifest tests/fixtures/manifest-goal/manifests/hosts/kanagawa01/web01.yml
```

```yaml
name: web01
site: kanagawa01
zone: dmz
role: web
environment: home
runtime_kind: vm
tags:
  - cap-public-http
  - managed-daedalus
  - svc-web
```

## Projection Report

```bash
hermes report projections \
  --manifests tests/fixtures/manifest-goal/manifests/hosts/kanagawa01 \
  --inventory tests/fixtures/manifest-goal/ansible/inventories/default/hosts.yml \
  --catalog tests/fixtures/manifest-goal/catalog/cataloga-hosts.yaml \
  --format markdown
```

```markdown
# Projection Report

## Status

## Recommended Next Review Actions
```

## Context

```bash
hermes context --workspace tests/fixtures/daedalus-simple
```

```text
workspace: /path/to/hermes/tests/fixtures/daedalus-simple
site: kanagawa01
inventory_path: /path/to/hermes/tests/fixtures/daedalus-simple/ansible/inventory/sites/kanagawa01
atlas_context_available: false
config_path: /etc/atlas/hermes.yml
mode: local
```

## Network Summary

```bash
hermes network summary --format markdown
```

```markdown
# KANAGAWA01 Network Summary

## Active Networks

| Name | VLAN | CIDR | Gateway | Purpose | Status | Reason |
| --- | ---: | --- | --- | --- | --- | --- |
| CLIENT | 100 | 10.10.0.0/24 | 10.10.0.1 | home client devices | active |  |
| MGMT | 110 | 10.10.10.0/24 | 10.10.10.1 | management plane | active |  |
```

Deprecated networks are rendered in a separate section and are not active.

## Host List

```bash
hermes host list --workspace tests/fixtures/daedalus-simple --zone mgmt
```

```text
hosts: 1
- kng01-mgmt-recursive-dns-01 zone=mgmt ansible_host=10.10.10.240 groups=dns,recursive,zone_mgmt services=dns,linux,recursive_dns,unbound
```

## DNS Report

```bash
hermes dns report --workspace tests/fixtures/daedalus-simple
```

```text
authoritative_hosts: kng01-dmz-authoritative-dns-01
recursive_hosts: kng01-mgmt-recursive-dns-01
dns_groups: dns, dns_authoritative, recursive
zone_files: /path/to/hermes/tests/fixtures/daedalus-simple/ansible/dns/zones/alflag.internal.zone
```

The command does not modify zone files, reload services, or query live DNS.

## Operations Summary

```bash
hermes report summary --workspace tests/fixtures/daedalus-simple --format markdown
```

```markdown
# Hermes Operations Summary

## Context

## Networks

## Hosts

## DNS

## Deprecated Concepts

## Warnings

## Suggested Manual Checks
```

JSON is stable and parseable:

```bash
hermes report summary --workspace tests/fixtures/daedalus-simple --format json
```
