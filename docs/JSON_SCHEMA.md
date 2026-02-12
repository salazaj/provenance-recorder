# Provenance Recorder JSON Schema

This document describes the JSON output contracts for `prov show` and `prov diff`.

Goals:
- Stable, script-friendly output.
- Minimal by default.
- Optional payload sections are gated by explicit flags.
- Avoid machine-specific data (e.g. absolute paths) unless explicitly requested.

Notes:
- JSON is emitted when `--format json` is used (or when a command’s `--raw` implies JSON).
- Field order is not guaranteed; treat objects as maps.

---

## Common conventions

### Runs & references
- `run_id` is the canonical run directory name.
- Tags are strings (user-controlled names), surfaced as arrays on objects where relevant.

### Gating
- `--paths` adds path-level detail in JSON.
- `--hashes` implies `--paths` and changes the shape of `paths` in `prov show`.
- `--warnings` adds warnings detail in JSON.
- `--raw` prints the underlying stored `run.json` (unmodified) and exits.

### Paths
- JSON output should not include run directory paths by default.
- If you add a future flag for paths (e.g. `--include-run-path`), document it here.

---

## `prov show --format json`

### Default JSON (no flags)
Top-level keys MUST be exactly:

- `run`
- `counts`
- `environment`
- `git`

#### Shape

```jsonc
{
  "run": {
    "run_id": "2026-02-11T16-08-36Z_bbbbbb",
    "name": "myrun",
    "timestamp": "2026-02-11T16:08:36Z",
    "tags": ["baseline", "t"]
  },
  "counts": {
    "inputs": 2,
    "outputs": 10,
    "warnings": 1,
    "has_params": true
  },
  "environment": {
    "python_version": "3.12.0",
    "platform": "linux-x86_64"
  },
  "git": {
    // null when not recorded
  }
}
````

### `run`

Required keys:

* `run_id` (string)
* `name` (string; may be empty)
* `timestamp` (string; may be empty)
* `tags` (array of strings; may be empty)

### `counts`

Required keys:

* `inputs` (int)
* `outputs` (int)
* `warnings` (int)
* `has_params` (bool)

### `environment`

Required keys:

* `python_version` (string; may be empty)
* `platform` (string; may be empty)

### `git`

* `git` is `null` if git metadata is not recorded in `run.json`.
* If present, it is an object copied from `run.json` (no normalization required), but MUST remain JSON-serializable.

---

### `prov show --format json --paths`

Adds a top-level `paths` key.

Top-level keys MUST be exactly:

* `run`
* `counts`
* `environment`
* `git`
* `paths`

`paths` shape depends on `--hashes`.

#### Without `--hashes`:

```jsonc
{
  "paths": {
    "inputs": ["data/in.txt", "data/new.txt"],
    "outputs": ["out/result.txt"]
  }
}
```

#### With `--hashes` (implies `--paths`):

```jsonc
{
  "paths": {
    "inputs": {"data/in.txt": "h_in_1"},
    "outputs": {"out/result.txt": "h_out_1"}
  }
}
```

---

### `prov show --format json --warnings`

Adds a top-level `warnings` key.

Top-level keys MUST be exactly:

* `run`
* `counts`
* `environment`
* `git`
* `warnings`

`warnings` is always an array. Elements are passthrough from `run.json` and may be:

* strings
* objects
* other JSON-serializable values (discouraged, but tolerated)

---

### `prov show --raw`

`--raw` prints the underlying stored `run.json` exactly as recorded and exits.

* Output MUST be the raw run JSON object (whatever keys exist in the stored file).
* No gating rules apply.
* `--raw` implies JSON output.

---

## `prov diff --format json`

### Default JSON (no flags)

Top-level keys MUST be exactly:

* `a`
* `b`
* `summary`
* `params`
* `environment`
* `git`

#### Shape

```jsonc
{
  "a": {
    "run_id": "2026-02-09T14-06-45Z_aaaaaa",
    "name": "abs_demo",
    "tags": ["baseline2"]
  },
  "b": {
    "run_id": "2026-02-11T16-08-36Z_bbbbbb",
    "name": "t",
    "tags": ["baseline", "t"]
  },
  "summary": {
    "truth_changed": true,
    "any_changed": true,
    "counts": {
      "inputs": {"added": 1, "removed": 0, "changed": 0},
      "outputs": {"added": 0, "removed": 1, "changed": 0},
      "params_changed": false,
      "env_changed": true,
      "git_changed": true,
      "warnings_changed": true
    }
  },
  "params": {"a": "h_params", "b": "h_params", "changed": false},
  "environment": {
    "a": {"python_version": "3.11.0", "platform": "linux-x86_64"},
    "b": {"python_version": "3.12.0", "platform": "linux-x86_64"},
    "changed": true
  },
  "git": {
    "a": { "recorded": true, "...": "..." },
    "b": { "recorded": true, "...": "..." },
    "recorded": { "a": true, "b": true },
    "changed": true,
    "reasons": ["commit changed", "dirty changed"]
  }
}
```

### `a` / `b`

Required keys:

* `run_id` (string)
* `name` (string; may be empty)
* `tags` (array of strings; may be empty)

### `summary`

Required keys:

* `truth_changed` (bool)
* `any_changed` (bool)
* `counts` (object)

`counts` required keys:

* `inputs`: `{added:int, removed:int, changed:int}`
* `outputs`: `{added:int, removed:int, changed:int}`
* `params_changed` (bool)
* `env_changed` (bool)
* `git_changed` (bool)
* `warnings_changed` (bool)

### `params`

Required keys:

* `a` (string or null)
* `b` (string or null)
* `changed` (bool)

### `environment`

Required keys:

* `a` (object)
* `b` (object)
* `changed` (bool)

Where `a` and `b` contain:

* `python_version` (string; may be empty)
* `platform` (string; may be empty)

### `git`

Required keys:

* `a` (object)
* `b` (object)
* `recorded` (object with keys `a`, `b` as booleans)
* `changed` (bool)
* `reasons` (array of strings)

If a run does not record git metadata, its side SHOULD include `{ "recorded": false }`.

---

### `prov diff --format json --paths`

Adds top-level keys:

* `inputs`
* `outputs`

Top-level keys MUST be exactly:

* `a`
* `b`
* `summary`
* `params`
* `environment`
* `git`
* `inputs`
* `outputs`

`inputs` / `outputs` shape:

```jsonc
{
  "inputs": {
    "added": ["data/new.txt"],
    "removed": [],
    "changed": ["data/in.txt"]
  },
  "outputs": {
    "added": [],
    "removed": ["out/result.txt"],
    "changed": []
  }
}
```

---

### `prov diff --format json --warnings`

Adds a top-level `warnings` key.

Top-level keys MUST be exactly:

* `a`
* `b`
* `summary`
* `params`
* `environment`
* `git`
* `warnings`

`warnings` shape:

```jsonc
{
  "warnings": {
    "a": ["...", {"code":"W001","message":"..."}],
    "b": ["..."],
    "changed": true
  }
}
```

---

## Compatibility & versioning

This schema is a contract. If it must change:

* Prefer adding new optional keys behind new flags.
* If a breaking change is required, bump the tool’s major version and update this document.

