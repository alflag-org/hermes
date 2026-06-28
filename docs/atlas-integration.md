# Atlas Integration

Hermes is packaged as an Atlas script release.

## Release Layout

```text
VERSION
commands/hermes.py
modules/hermes/
requirements.txt
```

`commands/hermes.py` stays thin. It inserts the release-local `modules/` directory and
then calls `hermes.cli.main`.

## Install

From Git:

```bash
atlas scripts install git+https://github.com/alflag-org/hermes.git#master --name hermes
atlas runtime install
atlas scripts shims
```

From a checkout:

```bash
atlas scripts install . --name hermes
atlas runtime install
atlas scripts shims
```

## Run

Atlas-run examples:

```bash
atlas run hermes context
atlas run hermes network summary
atlas run hermes host list --workspace tests/fixtures/daedalus-simple
atlas run hermes dns report --workspace tests/fixtures/daedalus-simple
atlas run hermes report summary --workspace tests/fixtures/daedalus-simple --format markdown
```

Shim examples:

```bash
export PATH="/opt/atlas/shims:$PATH"
hermes context
hermes network summary
hermes report summary --format markdown
```

When Atlas provides `atlas_core`, Hermes uses it only through public host-context APIs.
Hermes still runs without Atlas, which keeps local tests and CI independent from a live
Atlas installation.

## Local Development

```bash
PYTHONPATH=modules python3 commands/hermes.py --help
PYTHONPATH=modules python3 -m hermes --help
PYTHONPATH=modules python3 -m unittest discover -s tests -v
pytest
```

Editable install is supported:

```bash
pip install -e .
hermes --help
```
