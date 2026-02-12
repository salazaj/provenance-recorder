## 1) Make `prov tag` even harder to misuse

Right now you’ve solved the big footgun, but there are two more UX sharp edges worth smoothing:

* **Better errors when a “run ref” resolves to a tag** (e.g. user forgets they already have `t` and expects it to mean “latest run” or something). You can detect this *before* `_resolve_to_run_id()` by checking `ref in idx.tags` and tailoring the message (“`t` is a tag; did you mean `#N` or a run id?”).
* **Add `prov tag --help` examples that match the new ambiguity behavior** (people copy/paste help).

(These are tiny changes that pay off massively because tagging is a “muscle memory” command.)

## 2) Add `prov show <ref>` (or `prov inspect`)

You already have great primitives (`resolve_user_ref`, run.json reading in diff, tags in index). A `show` command would let users do:

* `prov show #8`
* `prov show baseline`
* `prov show <run_id>`

…and print:

* run id, name, timestamp
* tags pointing at it
* counts: inputs/outputs/params present, warnings count, git summary

This makes the tool feel “complete” and reduces the need for `cat run.json`.

## 3) Refactor shared “load run.json safely” into one place

You’ve got run loading logic in `diff.py` (`_load_run`) and you also resolve run ids in CLI. I’d extract:

* `prov/runsdb.py` (or `prov/runstore.py`)

  * `load_run(prov_dir, ref) -> Run`
  * `run_dir_from_ref(...)`
  * consistent “expected object got X” validation (you already improved this in diff)

Then both `diff` and the proposed `show` command reuse it.

## 4) Tighten JSON output stability (contract)

Your `diff --format json` is already useful. Next step is to make it *stable*:

* ensure keys always present (`added/removed/changed/unchanged`, even if empty)
* ensure run metadata always has `tags`, `name`, `timestamp` (empty string ok)
* add `"version": 1` at top of JSON outputs so you can evolve later without breaking consumers

This is huge if you ever want to pipe `prov diff --format json` into CI.

## 5) CLI polish / help coverage

A quick sweep that makes it feel pro:

* add `--no-color` / respect `NO_COLOR`
* normalize exit codes (you already have `5` for diff change detection; document it)
* ensure every command has at least one integration test (tag already does)

---

### 4) Stronger tag validation (optional)

Prevent footguns:

* disallow tags that look like `#12` or pure digits, since those collide with ordinals
* disallow whitespace
* maybe enforce `[a-zA-Z0-9._-]+`

### 5) Display tags in `diff` header

When the user diffs `baseline -> latest`, print:

* `A: test_run (baseline)`
* `B: abs_demo (final)`
  You already have tags in the index; just reverse-map run_id → tags.

### 7) Add `__all__` / minimal public API surface

If you ever expect library usage:

* `prov/__init__.py` can export only the stable stuff (e.g., `get_version`, `record_run`, `diff_runs`)

---
