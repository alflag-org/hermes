# Hermes Examples

The examples below use the repository fixture workspace:

```text
tests/fixtures/daedalus-simple
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
