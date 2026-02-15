# provenance-recorder

A minimal, local-first CLI tool for recording and comparing execution provenance.

It captures structured metadata about command execution and answers a practical operational question:

> What changed between runs?

Designed for environments where reproducibility, traceability, and explainability matter more than orchestration.

---

## Core Capabilities

### Record

Captures:

* Executed command
* Input file hashes
* Parameter sets
* Git commit + branch + dirty state
* Environment snapshot
* Output references

Metadata is stored locally:

```
.prov/runs/<run-id>/run.json
```

Validated against:

```
schemas/run.schema.json
```

---

### Diff

Compare two recorded runs and surface:

* Code differences
* Input file changes
* Parameter drift
* Environment variation
* Output reference differences

Useful for:

* Data pipeline validation
* Model training comparison
* Research reproducibility
* Compliance documentation
* Investigating unexpected output changes

---

## Architecture

* Local-first storage model
* JSON-based run metadata
* JSON schema validation
* Deterministic run identifiers
* Git metadata integration
* Explicit separation of record vs comparison logic

The tool intentionally avoids:

* Workflow orchestration
* CI/CD integration
* Dashboard layers
* Cloud dependencies

It operates as a focused provenance control layer.

---

## Design Constraints

* Explicit over implicit
* Bounded scope
* Verifiable structure
* Minimal surface area
* No hidden execution state

The goal is structured traceability without introducing workflow complexity.

---

## Example Use Case

1. Run an experiment or pipeline.
2. Record inputs, parameters, environment, and outputs.
3. Later, when results differ, run `diff` to identify structural drift instead of relying on memory.

This reduces narrative debugging and replaces it with explicit evidence.

---

## Intended Scope

Appropriate for:

* Small teams
* Research environments
* ML experimentation
* Compliance-sensitive workflows
* Local data pipelines

Not intended to replace CI/CD or workflow engines.

---

## Development

* Python-based CLI
* JSON schema validation
* Git integration
* Local filesystem storage
* Designed for deterministic behavior

---

## License

MIT License.

---

## Author

Alec
Systems-focused technical operator working on reproducible workflows, drift detection, and structured execution traceability.

