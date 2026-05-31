## Hermes の責務

Hermes は「監視」ではなく、**稼働中の基盤を扱う運用操作レイヤ**です。

```text
Hermes = infrastructure operation gateway
```

含めるもの:

| 領域          | 例                                                    |
| ----------- | ---------------------------------------------------- |
| Proxmox     | 現状取得、VM/LXC inventory export、Cataloga との差分、限定同期      |
| DNS / NSD   | zone 生成、record upsert、zone check、reload              |
| Cataloga    | import/export、resource normalize、sync plan 作成        |
| Drift       | desired と actual の比較、report                          |
| Maintenance | one-shot repair、migration helper、backup、sanity check |
| Reports     | JSON/YAML/text 形式の運用レポート                             |

含めないもの:

| 含めないもの                           | 理由                                            |
| -------------------------------- | --------------------------------------------- |
| OS baseline 適用                   | `daedalus` 側                                  |
| Ansible role/playbook            | `daedalus` 側                                  |
| Atlas runtime 実装                 | `atlas` 側                                     |
| Cataloga 本体の schema / API server | `cataloga` 側                                  |
| 常駐 daemon                        | Atlas の責務外。必要なら systemd timer / cron / CI で起動 |
| Scheduler                        | 同上                                            |
| Secret store                     | Bitwarden / env / host-local credentials 側    |

---

## `daedalus` との境界

```text
daedalus:
  desired state をホストやサービスへ適用する

hermes:
  actual state を取得し、catalog / DNS / Proxmox / operator 間の操作をつなぐ
```

具体例:

| 作業                                        | repo       |
| ----------------------------------------- | ---------- |
| Debian baseline                           | `daedalus` |
| SSH / sudo / package / systemd service 設定 | `daedalus` |
| Zabbix agent 構成                           | `daedalus` |
| DNS resolver 構成                           | `daedalus` |
| Proxmox VM 一覧取得                           | `hermes`   |
| Cataloga と Proxmox の差分検知                  | `hermes`   |
| NSD zone file 生成                          | `hermes`   |
| NSD reload                                | `hermes`   |
| DNS record upsert                         | `hermes`   |
| 移行補助スクリプト                                 | `hermes`   |
| repair / one-shot 操作                      | `hermes`   |

重要なのは、Hermes は「構成を継続的に収束させる」ものではなく、**運用者が明示的に呼び出す操作ツール**であることです。

---

## Atlas script release としての形

Atlas の script release は `VERSION` と `commands/` を持つディレクトリで、`modules/` と requirements は任意です。`commands/` 配下の `.py` は相対パスからコマンド名へ変換されます。([atlas-docs.jp0.workers.dev][2])
また `modules/` が存在する場合、Atlas は対象 release の `modules/` を `PYTHONPATH` の先頭に追加します。([atlas-docs.jp0.workers.dev][2])

Hermes はコマンドを大量に `commands/proxmox/collect.py` のように分けるより、まずは **単一 entrypoint** がよいです。

```text
commands/hermes.py
```

こうすると、shim 生成後に以下のように使えます。

```bash
hermes proxmox collect
hermes proxmox diff
hermes dns render-zone
hermes dns apply-zone --apply
```

Atlas 経由でも同じです。

```bash
atlas run hermes proxmox collect
atlas run hermes dns render-zone --zone alflag.internal
```

`commands/proxmox/collect.py` にすると Atlas command は `proxmox-collect` になります。これは単純ですが、Hermes という統合 CLI の名前が見えなくなります。今回は repo / CLI 名として `hermes` を育てたいので、**`commands/hermes.py` + subcommand 構成**が適切です。

---

## repo 構成案

```text
hermes/
  VERSION
  README.md
  pyproject.toml
  requirements.txt
  requirements.lock

  commands/
    hermes.py

  modules/
    hermes/
      __init__.py
      cli.py
      context.py
      config.py
      output.py
      errors.py
      confirm.py
      plan.py

      cataloga/
        __init__.py
        client.py
        dataset.py
        normalize.py
        models.py

      proxmox/
        __init__.py
        client.py
        collect.py
        normalize.py
        diff.py
        plan.py

      dns/
        __init__.py
        zone.py
        records.py
        nsd.py
        render.py
        apply.py

      inventory/
        __init__.py
        site.py
        network.py

      report/
        __init__.py
        drift.py
        inventory.py

  schemas/
    hermes-config.v1.schema.json
    proxmox-state.v1.schema.json
    dns-zone-plan.v1.schema.json
    sync-plan.v1.schema.json

  examples/
    hermes.yml
    proxmox-state.json
    dns-zone-plan.json

  tests/
    test_dns_render.py
    test_dns_apply_plan.py
    test_proxmox_normalize.py
    test_sync_plan.py
```

`modules/hermes/` に本体を置き、`commands/hermes.py` は薄い entrypoint にします。

---

## CLI 設計

基本形:

```bash
hermes <domain> <action> [options]
```

Domain はこの程度に絞ります。

```text
host
cataloga
proxmox
dns
report
maintenance
```

### host

```bash
hermes host show
hermes host check
```

Atlas の `/etc/atlas/host.yml` を確認するためのコマンドです。Atlas は host profile として `name`, `site`, `zone`, `role`, `environment`, `runtime_kind`, `tags` を scripts に渡せます。([atlas-docs.jp0.workers.dev][3])

### cataloga

```bash
hermes cataloga validate --file catalog.yaml
hermes cataloga export --format yaml
hermes cataloga import --file resources.yaml --dry-run
hermes cataloga normalize --file resources.yaml
```

初期は API 直結より、YAML / JSON dataset の normalize と validate を優先します。

### proxmox

```bash
hermes proxmox collect --site kanagawa01 --format json
hermes proxmox diff --site kanagawa01 --desired catalog.yaml
hermes proxmox sync-plan --site kanagawa01 --desired catalog.yaml
hermes proxmox sync --plan plan.json --apply
```

Proxmox VE は REST-like API を持ち、JSON を主要データ形式として使います。([pve.proxmox.com][4])
Python 実装では `proxmoxer` を使うのが自然です。`proxmoxer` は Proxmox REST API v2 の Python wrapper です。([GitHub][5])

### dns

```bash
hermes dns render-zone --zone alflag.internal --source catalog.yaml
hermes dns check-zone --zone alflag.internal --file out/alflag.internal.zone
hermes dns diff-zone --zone alflag.internal --file out/alflag.internal.zone
hermes dns apply-zone --zone alflag.internal --file out/alflag.internal.zone --apply
hermes dns upsert-record --zone alflag.internal --name foo --type A --value 10.10.10.10 --dry-run
```

NSD の `nsd-control reload [zone]` は zone file を読み直す操作なので、Hermes の DNS apply は「render → check → backup → atomic replace → reload → verify」の一連の安全 wrapper にします。([NLnet Labs][6])

### report

```bash
hermes report drift --site kanagawa01
hermes report inventory --site kanagawa01
hermes report dns --zone alflag.internal
```

人間向け text と機械向け JSON を必ず分けます。

```bash
hermes report drift --format text
hermes report drift --format json
```

---

## 設定ファイル

Hermes 固有設定は `/etc/hermes/config.yml` ではなく、まずは Atlas 配下に寄せる方がよいです。

```text
/etc/atlas/hermes.yml
```

Atlas の既定ディレクトリは `/etc/atlas`, `/opt/atlas`, `/var/lib/atlas` です。([atlas-docs.jp0.workers.dev][7])
Hermes は Atlas の script release なので、設定も `/etc/atlas` 配下に寄せる方が運用上まとまります。

例:

```yaml
site: kanagawa01

cataloga:
  mode: file
  dataset: /etc/atlas/data/cataloga/resources.yaml

proxmox:
  endpoint: https://pve.example.internal:8006
  token_id_env: HERMES_PROXMOX_TOKEN_ID
  token_secret_env: HERMES_PROXMOX_TOKEN_SECRET
  verify_tls: true

dns:
  zones:
    alflag.internal:
      zone_file: /etc/nsd/zones/alflag.internal.zone
      check_command: nsd-checkzone
      reload_command: nsd-control reload alflag.internal
      backup_dir: /var/lib/atlas/hermes/dns-backups

defaults:
  site: kanagawa01
  format: text
  dry_run: true
```

secret は config file に直接書かず、env 名だけを持たせます。

---

## 状態保存

Hermes は原則 stateless にします。必要なものだけ `/var/lib/atlas/hermes/` に置きます。

```text
/var/lib/atlas/hermes/
  cache/
    proxmox/
      latest-state.json
    cataloga/
      latest-export.yaml

  plans/
    20260531-120000-proxmox-sync-plan.json
    20260531-121000-dns-zone-plan.json

  backups/
    dns/
      alflag.internal/
        20260531-120000.zone

  reports/
    drift/
      20260531-120000.json
```

Atlas は実行ログを `/var/lib/atlas/logs/runs.jsonl` に JSONL で記録し、timestamp、release、script、args、version、exit_code、duration_ms などを残します。secret/token/key/password 系の引数値もマスクされます。([atlas-docs.jp0.workers.dev][2])
したがって Hermes 側で過剰な監査ログを実装する必要はありません。Hermes は **plan / backup / report** だけを保存すればよいです。

---

## 安全設計

Hermes の破壊的操作はすべて以下を必須にします。

```text
dry-run default
plan first
explicit --apply
backup before mutation
post-apply verify
machine-readable result
```

### 禁止事項

```text
--force を安易に作らない
暗黙 apply しない
複数 domain をまたぐ apply を最初から実装しない
自動修復 daemon にしない
secret を argv に載せない
```

### Apply の型

`apply` は各 domain ごとに閉じます。

```bash
hermes dns apply-zone --apply
hermes proxmox sync --apply
```

いきなり以下は作らない方がよいです。

```bash
hermes apply-all
hermes sync-all
hermes repair-all
```

事故範囲が大きすぎます。

---

## データモデル

Hermes の内部では、少なくとも以下の中間表現を持ちます。

### Actual State

外部システムから取得した現状。

```json
{
  "kind": "proxmox-state",
  "version": "v1",
  "site": "kanagawa01",
  "collected_at": "2026-05-31T12:00:00+09:00",
  "guests": []
}
```

### Desired Dataset

Cataloga export / YAML snapshot / local fixture。

```json
{
  "kind": "desired-dataset",
  "version": "v1",
  "resources": []
}
```

### Plan

適用可能な変更案。

```json
{
  "kind": "sync-plan",
  "version": "v1",
  "site": "kanagawa01",
  "domain": "dns",
  "actions": [
    {
      "action": "upsert-record",
      "zone": "alflag.internal",
      "name": "kng01-recursive-dns-01",
      "type": "A",
      "value": "10.10.10.240"
    }
  ]
}
```

### Result

実行結果。

```json
{
  "kind": "apply-result",
  "version": "v1",
  "ok": true,
  "applied": 1,
  "failed": 0,
  "details": []
}
```

ポイントは、**diff と apply を直接つながない**ことです。

```text
collect -> normalize -> diff -> plan -> apply -> verify
```

この分離があると、人間確認・テスト・ロールバックが容易になります。

---

## KANAGAWA01 への初期対応

初期 target は `kanagawa01` でよいです。現在の VLAN は `CLIENT`, `MGMT`, `DMZ`, `TRANSIT`, `UNUSED_NATIVE` に集約され、旧 `INTERNAL / STORAGE`, `OVERLAY`, `IOT` は廃止扱いです。

Hermes はこの情報を **hardcode しない**方がよいです。
ただし、初期実装の fixture としては持ってよいです。

```yaml
site: kanagawa01
networks:
  client:
    vlan: 100
    cidr: 10.10.0.0/24
  mgmt:
    vlan: 110
    cidr: 10.10.10.0/24
  dmz:
    vlan: 130
    cidr: 10.10.30.0/24
  transit:
    vlan: 901
    cidr: 10.255.255.0/29
```

最終的には Cataloga を source of truth に寄せます。

---

## 実装順

### Phase 0: skeleton

目的は Atlas script release として動くことの確認。

```text
VERSION
commands/hermes.py
modules/hermes/
requirements.txt
tests/
```

実装:

```bash
hermes host show
hermes host check
```

### Phase 1: DNS read-only

DNS は副作用が分かりやすく、テストしやすいので最初に向いています。

```bash
hermes dns render-zone
hermes dns check-zone
hermes dns diff-zone
```

ここでは reload しない。

### Phase 2: Proxmox collect

```bash
hermes proxmox collect
hermes proxmox normalize
```

ここでも Proxmox は絶対に変更しない。

### Phase 3: Cataloga adapter

```bash
hermes cataloga validate
hermes cataloga normalize
hermes proxmox diff --desired catalog.yaml
```

最初は file-based export/import でよいです。API 書き込みは後でよいです。

### Phase 4: DNS apply

```bash
hermes dns apply-zone --apply
```

安全条件:

```text
zone check 成功
current zone backup 成功
diff 表示
atomic replace
nsd-control reload <zone>
post-query verify
```

### Phase 5: Proxmox sync plan

```bash
hermes proxmox sync-plan
```

ここでもまだ apply は限定的にします。最初の apply 対象は tag / description / notes 程度に絞るべきです。VM 作成・削除・network 変更は後回しです。

---

## Python 実装方針

`Fire` を使うなら、CLI はこの構造で十分です。

```python
# commands/hermes.py
from hermes.cli import main

if __name__ == "__main__":
    main()
```

```python
# modules/hermes/cli.py
import fire

from hermes.commands.host import HostCommands
from hermes.commands.dns import DnsCommands
from hermes.commands.proxmox import ProxmoxCommands
from hermes.commands.cataloga import CatalogaCommands
from hermes.commands.report import ReportCommands


class Hermes:
    host = HostCommands()
    dns = DnsCommands()
    proxmox = ProxmoxCommands()
    cataloga = CatalogaCommands()
    report = ReportCommands()


def main() -> None:
    fire.Fire(Hermes)
```

Atlas scripts からは `atlas` 内部 package ではなく、安定 API の `atlas_core` を使います。Atlas docs でも、インストール済み scripts は `atlas_core` を import し、host-side CLI 実装の `atlas` package を直接 import しない方針です。([atlas-docs.jp0.workers.dev][8])

[1]: https://github.com/alflag-org/ansible "GitHub - alflag-org/ansible · GitHub"
[2]: https://atlas-docs.jp0.workers.dev/script-releases.html "スクリプトリリース - Atlas ドキュメント"
[3]: https://atlas-docs.jp0.workers.dev/configuration.html "設定 - Atlas ドキュメント"
[4]: https://pve.proxmox.com/wiki/Proxmox_VE_API?utm_source=chatgpt.com "Proxmox VE API"
[5]: https://github.com/proxmoxer/proxmoxer?utm_source=chatgpt.com "A Python wrapper for Proxmox REST API"
[6]: https://www.nlnetlabs.nl/documentation/nsd/nsd-control/?utm_source=chatgpt.com "NLnet Labs Documentation - NSD - nsd-control.8"
[7]: https://atlas-docs.jp0.workers.dev/concepts.html "設計と概念 - Atlas ドキュメント"
[8]: https://atlas-docs.jp0.workers.dev/api.html "Python API - Atlas ドキュメント"
