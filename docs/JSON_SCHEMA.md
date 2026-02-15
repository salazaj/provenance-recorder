# JSON Schemas (Contracts)

This document defines the stable JSON contracts for provenance-recorder.

## Global invariants

### No absolute paths
No JSON field may contain an absolute filesystem path.

- **Manifest keys** (inputs/outputs) must be **relative or non-absolute** strings.
- `params.path` must be **relative or non-absolute**.
- The index must not store absolute paths.
- Git `root` must not be stored (and currently is not part of the contract).

A “non-absolute” path may include `..` segments (e.g. `../data/in.txt`) if the user passed an absolute path that was converted to a cwd-relative form.

### Versioning
- `index.json.version` is `1`
- `run.json.version` is `1`
- CLI JSON outputs are versionless but follow the contracts below.

---

## `.prov/index.json`

### Purpose
A lightweight index of recorded runs + a tag map.

### Schema (v1)
```json
{
  "version": 1,
  "runs": [
    {
      "run_id": "2026-02-11T16-08-36Z_bbbbbb",
      "name": "my_run_name",
      "timestamp": "2026-02-11T16:08:36Z"
    }
  ],
  "tags": {
    "baseline": "2026-02-11T16-08-36Z_bbbbbb"
  }
}
````

### Notes

* `runs[*]` must **not** contain a `path` field.
* `timestamp` is ISO8601 UTC (recommended: `...Z`).
* `tags` values are run IDs.

---

## `.prov/runs/<run_id>/run.json`

### Purpose

The canonical run record written by `prov record`.

### Schema (v1)

#### Required top-level fields

```json
{
  "version": 1,
  "run_id": "2026-02-11T16-08-36Z_bbbbbb",
  "timestamp": "2026-02-11T16:08:36Z",
  "name": "my_run_name",
  "status": "recorded_only",
  "inputs": { "...": { "...": "..." } },
  "outputs": { "...": { "...": "..." } },
  "environment": { "...": "..." },
  "warnings": [ "..." ]
}
```

#### `inputs` / `outputs` manifests

Manifests are objects keyed by **non-absolute** path strings.

Each manifest entry has:

```json
{
  "bytes": 1234,
  "mtime_epoch": 1700000000,
  "mtime_utc": "2026-02-11T16:08:36+00:00",
  "hash": "sha256hex..."
}
```

Example:

```json
"inputs": {
  "data/in.txt": {
    "bytes": 12,
    "mtime_epoch": 1760000000,
    "mtime_utc": "2026-02-11T16:08:36+00:00",
    "hash": "abcd..."
  }
}
```

#### Optional `params`

`params` is **omitted** when not provided.

When present:

```json
"params": {
  "path": "params.yaml",
  "bytes": 456,
  "hash": "sha256hex..."
}
```

Constraints:

* `params.path` must be **non-absolute**
* `params.hash` is the hash of the params file contents

#### Optional `git`

`git` is **omitted** when git is not recorded (e.g. not in a repo).

When present:

```json
"git": {
  "is_repo": true,
  "commit": "deadbeef",
  "branch": "main",
  "detached": false,
  "dirty": false,
  "untracked": 0,
  "describe": "v0.1.0"
}
```

Constraints:

* `git.is_repo` is always `true` if this object is present.

#### `environment`

Minimal environment snapshot, currently:

```json
"environment": {
  "python_version": "3.12.0",
  "platform": "linux-x86_64"
}
```

#### `warnings`

Array of strings.
Example:

```json
"warnings": [
  "GIT_DIRTY: working tree has uncommitted changes",
  "GIT_UNTRACKED: 3 untracked file(s)"
]
```

---

## CLI JSON: `prov show --format json`

### Minimal contract (default flags)

Keys:

```json
{
  "run": { "...": "..." },
  "counts": { "...": "..." },
  "environment": { "...": "..." },
  "git": { "...": "..." }  // may be null if not recorded in run.json
}
```

`run`:

```json
"run": {
  "run_id": "2026-02-11T16-08-36Z_bbbbbb",
  "name": "t",
  "timestamp": "2026-02-11T16:08:36Z",
  "tags": ["baseline", "t"]
}
```

`counts`:

```json
"counts": {
  "inputs": 2,
  "outputs": 1,
  "warnings": 0,
  "has_params": false
}
```

`paths` (optional)
Only present when `--paths` is set.

If `--paths` without `--hashes`:

```json
"paths": {
  "inputs": ["data/in.txt"],
  "outputs": ["out/result.txt"]
}
```

If `--paths --hashes`:

```json
"paths": {
  "inputs": { "data/in.txt": "sha256..." },
  "outputs": { "out/result.txt": "sha256..." }
}
```

`warnings` (optional)
Only present when `--warnings` is set:

```json
"warnings": [
  "some warning"
]
```

### Policy: `--abs-paths`

`--abs-paths` is **rejected** for JSON output.

---

## CLI JSON: `prov diff --format json`

### Minimal contract (default flags)

Top-level keys:

```json
{
  "a": { "...": "..." },
  "b": { "...": "..." },
  "summary": { "...": "..." },
  "params": { "...": "..." },
  "environment": { "...": "..." },
  "git": { "...": "..." }
}
```

`a` / `b`:

```json
"a": { "run_id": "A", "name": "abs_demo", "tags": ["baseline2"] }
"b": { "run_id": "B", "name": "t", "tags": ["baseline"] }
```

`summary`:

```json
"summary": {
  "truth_changed": true,
  "any_changed": true,
  "counts": {
    "inputs": { "added": 1, "removed": 0, "changed": 0 },
    "outputs": { "added": 0, "removed": 1, "changed": 0 },
    "params_changed": false,
    "env_changed": true,
    "git_changed": true,
    "warnings_changed": false
  }
}
```

`params`:

```json
"params": { "a": "sha256...", "b": "sha256...", "changed": false }
```

* `a`/`b` may be `null` when params not recorded on that side.

`environment`:

```json
"environment": {
  "a": { "python_version": "3.11.0", "platform": "linux-x86_64" },
  "b": { "python_version": "3.12.0", "platform": "linux-x86_64" },
  "changed": true
}
```

`git`:

```json
"git": {
  "a": { "recorded": true, "is_repo": true, "commit": "...", "describe": "...", "branch": "main", "detached": false, "dirty": false, "untracked": 0 },
  "b": { "recorded": false },
  "changed": false,
  "reasons": ["not recorded (B)"],
  "recorded": { "a": true, "b": false }
}
```

### Optional `inputs` / `outputs` sections

Only included when `--paths` is set.

```json
"inputs": { "added": ["..."], "removed": ["..."], "changed": ["..."] },
"outputs": { "added": ["..."], "removed": ["..."], "changed": ["..."] }
```

### Optional `warnings` section

Only included when `--warnings` is set.

```json
"warnings": {
  "a": ["warning text", "..."],
  "b": ["warning text", "..."],
  "changed": true
}
```

### Policy: `--abs-paths`

`--abs-paths` is **rejected** for JSON output.

---

## Record-side JSON artifacts

`prov record` writes:

* `.prov/runs/<run_id>/run.json` (canonical; schema above)
* `.prov/runs/<run_id>/inputs.json` (same shape as `run.json.inputs`)
* `.prov/runs/<run_id>/outputs.json` (same shape as `run.json.outputs`)

`inputs.json` schema:

```json
{
  "data/in.txt": { "bytes": 1, "mtime_epoch": 0, "mtime_utc": "...", "hash": "..." }
}
```

`outputs.json` schema:

```json
{
  "out/result.txt": { "bytes": 1, "mtime_epoch": 0, "mtime_utc": "...", "hash": "..." }
}
```

All keys must be non-absolute paths.

