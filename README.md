# provenance-recorder

A small, honest tool that records **what inputs, code, environment, and parameters** produced a set of outputs — and can tell you **what changed between runs**.

> Design goal: make it hard to lie to yourself about what you ran.

This project is intentionally boring, explicit, and local-first.

---

## Philosophy

* **Verification over automation** – explicit inputs/outputs beat magic.
* **Local-first** – everything lives in the repo; no servers required.
* **Plain truth** – hashes, timestamps, manifests; no opinions.
* **Bounded scope** – this records provenance; it does not manage workflows.

---

## Repo layout

```
provenance-recorder/
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
├── prov/
│   ├── __init__.py
│   ├── cli.py            # Typer/Click entrypoint
│   ├── config.py         # config loading + defaults
│   ├── record.py         # run + record logic
│   ├── diff.py           # compare two runs
│   ├── hashing.py        # file hashing strategies
│   ├── gitinfo.py        # git metadata helpers
│   ├── env.py            # environment capture
│   └── render.py         # human-readable reports
├── schemas/
│   └── run.schema.json   # JSON schema for run records
├── examples/
│   └── minimal-python/
│       ├── data/
│       ├── params.yaml
│       └── run.sh
└── tests/
    └── test_diff.py
```

---

## What this does (eventually)

* `prov init` – create a `.prov/` directory
* `prov run` – wrap a command and record provenance
* `prov record` – record provenance after an interactive run
* `prov diff` – explain what changed between two runs

---

## What this deliberately does *not* do

* No dashboards
* No cloud sync
* No auto-discovery magic
* No statistical opinions

---

## Status

Scaffolding only. CLI spec and first commands next.

---

## License

## License

This project is licensed under the GNU Affero General Public License v3 (AGPL-3.0).

The intent is to ensure that improvements and deployments of this tool remain
transparent and auditable, especially when offered as a service.

Commercial or alternative licensing may be available on a case-by-case basis
for organizations with specific needs. Please open an issue or contact the
maintainer to discuss.

