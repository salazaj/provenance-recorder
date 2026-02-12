# provenance-recorder

A minimal, local-first CLI tool for recording and explaining execution provenance.

It captures:

- Inputs (with hashes)
- Parameters
- Code revision metadata
- Environment details
- Output references

And answers the operational question:

> “What changed between runs?”

---

## Who This Is For

This tool was built for small teams who need:

    Reproducibility without orchestration overhead

    Local-first auditability

    A clear answer to “what changed?”

It reflects the same philosophy used in my consulting work:
explicit systems, bounded scope, and recovery over heroics.

---

## Operational Context

In small teams and research environments:

- Outputs are generated without a reproducible record.
- Parameters drift silently.
- Code revisions alter results without trace.
- Environment differences go unnoticed.
- Reproducing a prior result requires guesswork.

When results change, debugging becomes narrative-driven instead of evidence-driven.

`provenance-recorder` provides a small, explicit provenance layer to reduce ambiguity.

---

## What This Demonstrates

This project reflects practical experience in:

- Reproducibility control
- Drift detection
- Structured metadata recording
- Git-aware execution tracking
- Audit-friendly JSON schema validation
- Local-first tooling without workflow lock-in

It is intentionally:

- Explicit over implicit
- Local over cloud-dependent
- Bounded in scope
- Data-oriented, not dashboard-oriented

---

## Core Capabilities

### Record

Capture:

- Executed command
- Input file hashes
- Parameter sets
- Git commit + branch + dirty state
- Environment snapshot
- Output references

All metadata is stored under:

```
.prov/runs/<run-id>/run.json

```

Validated against:


```
schemas/run.schema.json

```

---

### Diff

Compare two runs and surface:

- Code differences
- Input changes
- Parameter drift
- Environment variation
- Output reference differences

Designed for:

- Research reproducibility
- Model training comparison
- Data pipeline validation
- Audit preparation
- “Why did this change?” investigations

---

## What This Is Not

- Not a workflow orchestrator
- Not a CI system
- Not a dashboard
- Not a pipeline framework
- Not a cloud service

It is a small provenance control layer.

---

## Typical Engagement Context

This tool is useful in environments where:

- Results must be explainable
- Compliance requires traceability
- Teams need reproducibility without adopting heavy orchestration
- Execution transparency matters more than automation

---

## Status

Active development.

Core run recording and diff logic implemented.
CLI stabilization and documentation ongoing.

---

## License

MIT License.

This tool is intentionally simple, local-first, and permissive.
If you use it in research, internal infrastructure, or production environments, attribution is appreciated.
