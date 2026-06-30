# Hermes Source of Truth

Hermes uses host manifest YAML as the managed-host source of truth.

```text
host manifest = source of truth
Daedalus inventory = convergence projection
Catalaga dataset = catalog projection
Atlas host.yml = runtime context projection
Hermes = read-only auditor / reporter / planner
```

Hermes is not the inventory master and does not own desired state. It reads manifests
and local snapshots, renders the expected projections, and reports drift for human
review.

## Ownership

| Field | Master | Projection |
| --- | --- | --- |
| hostname | host manifest | Daedalus, Cataloga, Atlas |
| site | host manifest | Daedalus, Cataloga, Atlas |
| lifecycle | host manifest | Cataloga, reports |
| zone | host manifest | Daedalus group, Cataloga tag, Atlas context |
| address | host manifest | Daedalus `ansible_host`, Cataloga spec |
| provider | host manifest | Daedalus `provider_*`, Cataloga spec |
| platform | host manifest | Daedalus `platform_*`, Cataloga spec, Atlas `runtime_kind` |
| services | host manifest | Daedalus `svc_*`, Cataloga spec, Atlas tags |
| capabilities | host manifest | Daedalus `cap_*`, Cataloga spec, Atlas tags |
| catalog resource id | host manifest | Cataloga resource id |
| display name | host manifest | Cataloga resource name |
| description | host manifest | Cataloga resource description |

Actual VM, DNS, Cloudflare, and probe results are report-only inputs. They do not become
the master of managed host identity.

## Projection Flow

```text
host manifest -> Daedalus projection
host manifest -> Cataloga projection
host manifest -> Atlas host context projection

Hermes reads all of them, reports drift, and generates reviewable artifacts.
Hermes does not apply changes.
```

Daedalus remains responsible for Ansible convergence. Cataloga remains the catalog UI
and dataset consumer. Atlas remains runtime and script release substrate. Themis owns
future strict live validation, and Ares owns dangerous operational changes.
