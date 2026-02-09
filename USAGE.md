## CLI spec v1

### Global behavior

* All human-facing output goes to **stdout**.
* All warnings/errors go to **stderr**.
* Exit codes:

  * `0` success (warnings allowed)
  * `2` user/config error (missing required args, invalid paths, command failed pre-run)
  * `3` truth-critical capture failure (hashing required files failed, cannot write run record)
  * `4` wrapped command exit code is non-zero (but we still record provenance if possible)

### Common flags (available on all commands)

* `--prov-dir PATH` (default: `.prov`)
* `--config PATH` (default: `.prov/config.yaml` if present)
* `--format [text|json]` (default: `text`) for command outputs (not run artifacts)

---

## `prov init`

**Purpose:** Initialize provenance storage in the current project.

**Usage**

```bash
prov init
```

**Options**

* `--prov-dir PATH` (default `.prov`)
* `--force` overwrite existing structure (otherwise error)

**Creates**

```
.prov/
  runs/
  index.json
  config.yaml   (optional template)
```

**Failure (exit 2)**

* Cannot create directories / permission denied
* Existing `.prov` and not `--force`

---

## `prov run`

**Purpose:** Wrap a command and record a provenance run.

**Usage**

```bash
prov run --name NAME --inputs PATH... --outputs PATH... [--params PATH] -- COMMAND [ARGS...]
```

**Required**

* `--name TEXT` short run label (e.g., `case_rate_pipeline`)
* `--inputs PATH...` one or more input files or directories (explicit)
* `--outputs PATH...` one or more output files or directories (explicit)
* `-- COMMAND ...` the command to execute

**Options**

* `--params PATH` path to YAML/JSON/TOML params file (recorded + hashed)
* `--param KEY=VALUE` (repeatable) small inline params (stored in run.json)
* `--cwd PATH` working directory for the wrapped command (default: current)
* `--out-scan [true|false]` if an output entry is a directory, recursively manifest files (default: true)
* `--input-scan [true|false]` if an input entry is a directory, recursively manifest files (default: false in v1; explicit > magic)
* `--hash [sha256|blake3]` (default sha256; blake3 optional if installed)
* `--hash-mode [strict|fast]`

  * `strict`: hash full contents (default)
  * `fast`: metadata-only fingerprint (size+mtime) **must be labeled everywhere**
* `--store-env [full|minimal|none]` (default: minimal)

  * minimal: python+platform
  * full: also `pip freeze` (or `uv pip freeze`) if available
* `--git [auto|require|off]` (default: auto)
* `--redact-paths [true|false]` (default true)
* `--note TEXT` freeform note added to run record
* `--tags TAG` repeatable

**Artifacts created**

```
.prov/runs/<run_id>/
  run.json
  RUN.md
  inputs.json
  outputs.json
  env.txt            (if captured)
  pip-freeze.txt     (if captured)
  warnings.txt       (if any)
```
**.prov/ is added to .gitignore by default**

**Warnings banner requirement**

* If any contextual capture is incomplete, `RUN.md` begins with:

> ⚠ WARNINGS (contextual ambiguities)
>
> * Git metadata unavailable (not a git repo)
> * Package snapshot unavailable (`pip freeze` failed)
>   …
>   These warnings do **not** affect recorded input/output hashes.

Same banner is printed to stderr at run start/end.

**Truth-critical failures (exit 3)**

* Any required input path doesn’t exist or can’t be read
* Hashing a required input fails (I/O error)
* Cannot write `.prov/runs/<run_id>/run.json` (record is mandatory)
* If `--hash-mode strict` and hashing outputs fails after command, treat as truth-critical

**Contextual warnings (exit still 0 or 4 depending on command)**

* Not a git repo (auto mode)
* `git` not installed
* cannot run `pip freeze` / conda export
* hostname/user capture disabled or unavailable
* redaction applied

**Wrapped command failure**

* If the wrapped command returns non-zero:

  * still attempt to record everything available
  * set `run.json.status = "command_failed"`
  * exit `4`

---

## `prov record`

**Purpose:** Record provenance without executing a command (for notebooks / interactive sessions).

**Usage**

```bash
prov record --name NAME --inputs PATH... --outputs PATH... [--params PATH]
```

Same options as `prov run` except no `-- COMMAND ...`.
`run.json.command = null` and `status = "recorded_only"`.

Truth-critical + contextual behavior identical.

---

## `prov diff`

**Purpose:** Compare two runs and explain what changed.

**Usage**

```bash
prov diff RUN_ID_A RUN_ID_B
```

**Options**

* `--show [summary|full]` (default summary)
* `--format [text|json]` (default text)
* `--paths` include file lists (default: summary omits lists, shows counts)
* `--fail-on [none|truth|any]` (default none)

  * truth: exit non-zero if inputs/params hashes differ
  * any: also exit non-zero for contextual differences (git/env)

**Output (text summary)**

* Code: git commit/dirty changed (or “unknown”)
* Inputs: changed count + which (if `--paths`)
* Params: changed/unchanged
* Environment: changed/unknown
* Outputs: changed count + which (if `--paths`)
* Warnings: show warnings from each run at top

Exit code:

* `0` no differences (or only ignored)
* `5` differences found and `--fail-on` triggered
* `2` run ids not found / invalid

---

## The warnings policy (explicit + persisted)

In `run.json`, include:

```json
"warnings": [
  {"code":"GIT_UNAVAILABLE","message":"Git metadata unavailable (not a git repo).","severity":"context"},
  {"code":"PIP_FREEZE_FAILED","message":"Package snapshot unavailable: pip freeze failed.","severity":"context"}
],
"truth_mode": {"hash":"sha256","hash_mode":"strict"}
```

And in `RUN.md`, warnings appear at the very top, always.

---
