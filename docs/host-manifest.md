# Host Manifest

Host manifests live outside Ansible `host_vars`:

```text
manifests/
  hosts/
    kanagawa01/
      web01.yml
```

Hermes loads manifests from `manifests/hosts/<site>/*.yml` or a single manifest file.

## Schema

```yaml
version: 1
kind: host

metadata:
  name: web01
  site: kanagawa01
  lifecycle: active

spec:
  zone: dmz
  address: 10.10.30.21
  provider:
    type: proxmox
  platform:
    type: vm
  services:
    - web
  capabilities:
    - public_http

catalog:
  resource_id: host-web01
  display_name: web01
  description: Public-facing web host
  tags:
    managed_by: daedalus
    site: kanagawa01
    zone: dmz
```

## Validation Policy

`hermes manifest check` validates:

- `version: 1` and `kind: host`
- `metadata.name` matches the filename
- `metadata.site` matches the parent site directory
- lifecycle, zone, provider, platform, service, and capability values are normalized
- active zones are limited to `client`, `mgmt`, `dmz`, `transit`, and `unused_native`
- active hosts do not use deprecated zones: `internal`, `storage`, `overlay`, `iot`
- `spec.address` belongs to the active zone CIDR
- host names, addresses, and `catalog.resource_id` values are unique
- active Zabbix-related values are rejected

Warnings include missing descriptions, empty services, empty capabilities, and
non-active lifecycle values. `--strict` promotes warnings to command failure.

## Projection Mapping

Daedalus:

```text
metadata.name      -> inventory hostname
spec.address       -> ansible_host
spec.zone          -> zone group
spec.provider.type -> provider_<type>
spec.platform.type -> platform_<type>
spec.services[]    -> svc_<service>
spec.capabilities[] -> cap_<capability>
```

Catalaga:

```text
catalog.resource_id -> resource id
catalog.display_name -> resource name
catalog.description -> resource description
metadata.lifecycle -> resource lifecycle
spec.address/provider/platform/services/capabilities -> resource spec
metadata.site and spec.zone -> resource tags
```

Atlas:

```text
metadata.name -> name
metadata.site -> site
spec.zone -> zone
first service -> role
spec.platform.type -> runtime_kind
services/capabilities -> tags
```
