# prov/cli.py
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

import typer
from rich.console import Console
from rich.table import Table

from .diff import diff_runs
from .indexdb import load_index, validate_tag_name
from .initcmd import init_project
from .record import record_run
from .resolve import resolve_run_pair, resolve_user_ref # fixed
from .version import get_version
from .repair import repair_index
from .tagging import resolve_tag_args, TaggingError
from .runstore import load_run


app = typer.Typer(
    help="Record and compare provenance of analysis runs.", no_args_is_help=True
)
console = Console()


def _badparam(e: Exception | str) -> typer.BadParameter:
    return typer.BadParameter(str(e))


def _load_index_or_badparam(prov_dir: Path):
    try:
        return load_index(prov_dir)
    except ValueError as e:
        raise _badparam(e)


def _require_prov_dir(prov_dir: Path) -> None:
    if not prov_dir.exists():
        raise _badparam(f"{prov_dir} does not exist. Run `prov init` first.")


def _require_nonempty(s: str, opt: str) -> str:
    if not s.strip():
        raise typer.BadParameter(
            f"{opt} is required.\n\n"
            "Example:\n"
            "  prov record --name myrun --inputs data/ --outputs out/\n"
        )
    return s


def _looks_like_ordinal(x: str) -> bool:
    x = x.strip()
    return x.isdigit() or (x.startswith("#") and x[1:].isdigit())


def _resolve_to_run_id(prov_dir: Path, ref: str) -> str:
    """Resolve ref and return a run_id (never a filesystem path)."""
    try:
        resolved = resolve_user_ref(prov_dir, ref)
    except (ValueError, RuntimeError) as e:
        # ordinals out of range, missing index, etc.
        raise _badparam(e)
    p = Path(resolved)
    if p.exists():
        # if it's a file, use parent dir name; if it's a dir, use dir name
        return p.parent.name if p.is_file() else p.name
    return resolved


@app.callback(invoke_without_command=True)
def main() -> None:
    """Provenance Recorder: record runs and diff them."""
    return


@app.command("repair-index", help="Rebuild .prov/index.json from .prov/runs and backfill missing timestamps into run.json.")
def repair_index_cmd(
    prov_dir: Path = typer.Option(
        Path(".prov"), "--prov-dir", help="Provenance directory."
    ),
    backup: bool = typer.Option(
        True, "--backup/--no-backup", help="Backup existing index.json."
    ),
    keep_tags: bool = typer.Option(
        True, "--keep-tags/--drop-tags", help="Preserve tags if readable."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without writing."
    ),
) -> None:
    """Rebuild index.json from disk; optionally back up and keep tags."""
    _require_prov_dir(prov_dir)
    try:
        _, res = repair_index(
            prov_dir=prov_dir, backup=backup, keep_tags=keep_tags, dry_run=dry_run
        )
        console.print(f"- timestamps added to run.json: {res.timestamps_added}")
    except Exception as e:
        raise _badparam(e)

    if res.backup_path:
        console.print(f"[dim]Backed up index to[/dim] {res.backup_path}")
    console.print(
        f"[bold green]Repaired index[/bold green] ({'dry-run' if dry_run else 'written'})"
    )
    console.print(f"- runs: {res.runs_count}")
    console.print(f"- tags kept: {res.tags_kept} (from {res.tags_total_before})")
    if res.warnings:
        console.print("[bold yellow]Warnings[/bold yellow]")
        for w in res.warnings:
            console.print(f"- {w}")


@app.command("repair", help="Alias for repair-index.")
def repair_alias(
    prov_dir: Path = typer.Option(Path(".prov"), "--prov-dir", help="Provenance directory."),
    backup: bool = typer.Option(True, "--backup/--no-backup", help="Backup existing index.json."),
    keep_tags: bool = typer.Option(True, "--keep-tags/--drop-tags", help="Preserve tags if readable."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change without writing."),
) -> None:
    """Alias for `prov repair-index`."""
    repair_index_cmd(prov_dir=prov_dir, backup=backup, keep_tags=keep_tags, dry_run=dry_run)


@app.command()
def show(
    ref: Optional[str] = typer.Argument(
        None,
        help="Run ID, tag, ordinal, or path. Defaults to latest run.",
    ),
    paths: bool = typer.Option(False, "--paths", help="Show inputs/outputs paths"),
    abs_paths: bool = typer.Option(False, "--abs-paths", help="Show absolute paths (implies --paths)"),
    warnings: bool = typer.Option(False, "--warnings", help="Show warning messages"),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
    prov_dir: Path = typer.Option(Path(".prov"), "--prov-dir", help="Provenance directory."),
    hashes: bool = typer.Option(False, "--hashes", help="Show inputs/outputs hashes (implies --paths)."),
    raw: bool = typer.Option(False, "--raw", help="Print the raw run.json and exit (implies --format json)."),
) -> None:
    """Show details for a single run."""
    _require_prov_dir(prov_dir)
    if abs_paths and not paths:
        paths = True

    fmt = format.lower()
    if fmt not in ("text", "json"):
        raise _badparam("format must be 'text' or 'json'")

    if hashes and not paths:
        paths = True

    if raw:
        # raw overrides formatting; keep it dead-simple
        fmt = "json"

    idx = _load_index_or_badparam(prov_dir)
    ordered = idx.ordered_run_ids()
    if not ordered:
        if fmt == "json":
            console.print_json(json.dumps({"run": None}))
        else:
            console.print("(no runs)")
        return

    run_ref = ref if ref is not None else ordered[-1]
    run_id = _resolve_to_run_id(prov_dir, run_ref)

    try:
        run = load_run(prov_dir, run_id)
    except Exception as e:
        raise _badparam(e)

    if raw:
        console.print_json(json.dumps(run.data))
        return

    tags = idx.tags_for_run(run.run_id)
    data = run.data

    inputs = data.get("inputs") or {}
    outputs = data.get("outputs") or {}
    params = data.get("params")
    warn = data.get("warnings") or []
    env = data.get("environment") or {}
    git = data.get("git") if "git" in data else None

    def _hash_map(obj: object) -> dict[str, str]:
        if not isinstance(obj, dict):
            return {}
        out: dict[str, str] = {}
        for p, meta in obj.items():
            if isinstance(meta, dict) and "hash" in meta:
                out[str(p)] = str(meta["hash"])
        return out

    inputs_map = _hash_map(data.get("inputs") or {})
    outputs_map = _hash_map(data.get("outputs") or {})

    def _fmt_path(p: str) -> str:
        pp = Path(p)
        if abs_paths:
            return str(pp.resolve())
        try:
            return str(pp.resolve().relative_to(Path.cwd().resolve()))
        except Exception:
            return str(pp)

    obj = {
        "run": {
            "run_id": run.run_id,
            "name": str(data.get("name", run.name or "")),
            "timestamp": str(data.get("timestamp", "")),
            "path": str(run.path),
            "tags": tags,
        },
        "counts": {
            "inputs": len(inputs) if isinstance(inputs, dict) else 0,
            "outputs": len(outputs) if isinstance(outputs, dict) else 0,
            "warnings": len(warn) if isinstance(warn, list) else 0,
            "has_params": bool(params),
        },
        "environment": {
            "python_version": str(env.get("python_version", "")),
            "platform": str(env.get("platform", "")),
        },
        "git": None if git is None else dict(git),
    }

    if fmt == "json":
        if paths:
            if hashes:
                obj["paths"] = {"inputs": inputs_map, "outputs": outputs_map}
            else:
                obj["paths"] = {"inputs": sorted(inputs_map.keys()), "outputs": sorted(outputs_map.keys())}
        if warnings:
            obj["warnings"] = warn if isinstance(warn, list) else []
        console.print_json(json.dumps(obj))
        return

    console.print(f"[bold]Run[/bold] {obj['run']['run_id']}")
    if obj["run"]["name"]:
        console.print(f"Name: {obj['run']['name']}")
    if obj["run"]["timestamp"]:
        console.print(f"Timestamp: {obj['run']['timestamp']}")
    console.print(f"Path: {obj['run']['path']}")
    if tags:
        console.print(f"Tags: {', '.join(tags)}")

    t = Table(title="Summary", show_lines=False)
    t.add_column("Field", style="bold")
    t.add_column("Value")
    t.add_row("Inputs", str(obj["counts"]["inputs"]))
    t.add_row("Outputs", str(obj["counts"]["outputs"]))
    t.add_row("Params", "present" if obj["counts"]["has_params"] else "none")
    t.add_row("Warnings", str(obj["counts"]["warnings"]))
    t.add_row("Python", obj["environment"]["python_version"] or "(unknown)")
    t.add_row("Platform", obj["environment"]["platform"] or "(unknown)")
    t.add_row("Git", "recorded" if git is not None else "not recorded")
    console.print(t)

    if warnings and isinstance(warn, list):
        console.print("")
        console.print("[bold]Warnings[/bold]")
        if warn:
            for w in warn:
                console.print(f"- {w.get('message', w.get('code', w))}" if isinstance(w, dict) else f"- {w}")
        else:
            console.print("(none)")

    if paths:
        console.print("")
        console.print("[bold]Inputs[/bold]")
        if inputs_map:
            for p in sorted(inputs_map.keys()):
                if hashes:
                    console.print(f"- {_fmt_path(p)}  [dim]{inputs_map[p]}[/dim]")
                else:
                    console.print(f"- {_fmt_path(p)}")
        else:
            console.print("(none)")

        console.print("")
        console.print("[bold]Outputs[/bold]")
        if outputs_map:
            for p in sorted(outputs_map.keys()):
                if hashes:
                    console.print(f"- {_fmt_path(p)}  [dim]{outputs_map[p]}[/dim]")
                else:
                    console.print(f"- {_fmt_path(p)}")
        else:
            console.print("(none)")


@app.command()
def diff(
    run_a: Optional[str] = typer.Argument(
        None, help="Run ID, tag, ordinal, or path (A). Optional."
    ),
    run_b: Optional[str] = typer.Argument(
        None, help="Run ID, tag, ordinal, or path (B). Optional."
    ),
    paths: bool = typer.Option(False, "--paths", help="Show path-level details"),
    abs_paths: bool = typer.Option(
        False, "--abs-paths", help="Show absolute paths (implies --paths)"
    ),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
    fail_on: str = typer.Option(
        "none", "--fail-on", help="Exit non-zero if changes: none|truth|any"
    ),
    prov_dir: Path = typer.Option(
        Path(".prov"), "--prov-dir", help="Provenance directory."
    ),
    warnings: bool = typer.Option(False, "--warnings", help="Show warning messages"),
) -> None:
    """Compare two runs and explain what changed."""
    _require_prov_dir(prov_dir)
    fmt = format.lower()
    fo = fail_on.lower()
    if fmt not in ("text", "json"):
        raise _badparam("format must be 'text' or 'json'")
    if fo not in ("none", "truth", "any"):
        raise _badparam("fail-on must be one of: none, truth, any")
    if abs_paths and not paths:
        paths = True

    try:
        a, b = resolve_run_pair(prov_dir, run_a, run_b)
    except (RuntimeError, ValueError) as e:
        raise _badparam(e)


    if fmt == "text":
        if run_a is None and run_b is None:
            console.print(f"[dim]Using last two runs:[/dim] {a} → {b}")
        elif run_a is not None and run_b is None:
            console.print(f"[dim]Comparing:[/dim] {a} → {b}")

    try:
        code = diff_runs(
            prov_dir=prov_dir,
            run_a=a,
            run_b=b,
            show_paths=paths,
            abs_paths=abs_paths,
            show_warnings=warnings,
            out_format=fmt,  # type: ignore[arg-type]
            fail_on=fo,  # type: ignore[arg-type]
        )
    except FileNotFoundError as e:
        raise _badparam(e)
    except json.JSONDecodeError as e:
        raise _badparam(f"Invalid JSON in run record: {e}")
    raise typer.Exit(code=code)


@app.command()
def tag(
    a: str = typer.Argument(..., help="Run ref or tag name (either order)."),
    b: str = typer.Argument(..., help="Tag name or run ref (either order)."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing tag."),
    prov_dir: Path = typer.Option(
        Path(".prov"), "--prov-dir", help="Provenance directory."
    ),
) -> None:
    """Add tag to a run."""
    _require_prov_dir(prov_dir)
    idx = _load_index_or_badparam(prov_dir)

    def _tag_ok(x: str) -> bool:
        try:
            validate_tag_name(x)
            return True
        except ValueError:
            return False

    def _run_ok(x: str) -> bool:
        try:
            rid = _resolve_to_run_id(prov_dir, x)
        except typer.BadParameter:
            return False
        return (prov_dir / "runs" / rid).exists()

    try:
        run_ref, tag_name = resolve_tag_args(
            a,
            b,
            existing_tags=idx.tags,
            tag_ok=_tag_ok,
            run_ok=_run_ok,
        )
    except TaggingError as e:
        raise _badparam(e)

    run_id = _resolve_to_run_id(prov_dir, run_ref)
    run_path = prov_dir / "runs" / run_id
    if not run_path.exists():
        raise _badparam(
            f"Run '{run_id}' does not exist at {run_path}. "
            "Your index/tag may be stale; run `prov runs` to inspect."
        )

    try:
        validate_tag_name(tag_name)
    except ValueError as e:
        raise _badparam(e)

    try:
        idx.set_tag(tag_name, run_id, force=force)
    except ValueError as e:
        raise _badparam(e)

    idx.write()
    console.print(f"[bold green]Tagged[/bold green] {tag_name} → {run_id}")


@app.command()
def runs(
    limit: int = typer.Option(
        25, "--limit", help="How many runs to show (most recent first)."
    ),
    latest: bool = typer.Option(
        False, "--latest", help="Print only the latest run id and exit."
    ),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
    prov_dir: Path = typer.Option(
        Path(".prov"), "--prov-dir", help="Provenance directory."
    ),
) -> None:
    """List runs with ordinals (oldest=1) and any tags pointing at them."""
    fmt = format.lower()
    if fmt not in ("text", "json"):
        raise _badparam("format must be 'text' or 'json'")
    _require_prov_dir(prov_dir)

    idx = _load_index_or_badparam(prov_dir)
    ordered = idx.ordered_run_ids()
    if not ordered:
        if fmt == "json":
            console.print_json(json.dumps({"runs": []}))
        else:
            console.print("(no runs)")
        return

    latest_id = ordered[-1]

    if latest:
        if fmt == "json":
            console.print_json(json.dumps({"run_id": latest_id}))
        else:
            console.print(latest_id)
        return

    # Map run_id -> (name, timestamp) from index entries
    meta: dict[str, tuple[str, str]] = {}
    for r in idx.runs:
        if isinstance(r, dict) and r.get("run_id"):
            meta[str(r["run_id"])] = (
                str(r.get("name", "")),
                str(r.get("timestamp", "")),
            )

    # Most recent first
    show = list(reversed(ordered))[: max(1, limit)]

    if fmt == "json":
        rows = []
        # precompute ordinal mapping (oldest=1)
        ord_map = {rid: i + 1 for i, rid in enumerate(ordered)}
        for rid in show:
            name, ts = meta.get(rid, ("", ""))
            rows.append(
                {
                    "ordinal": ord_map[rid],
                    "run_id": rid,
                    "name": name,
                    "timestamp": ts,
                    "tags": idx.tags_for_run(rid),
                }
            )
        console.print_json(json.dumps({"runs": rows}))
        return

    t = Table(title="Runs", show_lines=False)
    t.add_column("#", style="bold")
    t.add_column("Run ID")
    t.add_column("Name")
    t.add_column("Timestamp")
    t.add_column("Tags")

    ord_map = {rid: i + 1 for i, rid in enumerate(ordered)}
    for rid in show:
        name, ts = meta.get(rid, ("", ""))
        t.add_row(
            str(ord_map[rid]),
            rid,
            name,
            ts,
            ", ".join(idx.tags_for_run(rid)),
        )
    console.print(t)


@app.command()
def untag(
    tag: str = typer.Argument(..., help="Tag name to remove."),
    prov_dir: Path = typer.Option(
        Path(".prov"), "--prov-dir", help="Provenance directory."
    ),
) -> None:
    """Remove a tag."""
    _require_prov_dir(prov_dir)
    idx = _load_index_or_badparam(prov_dir)
    try:
        idx.del_tag(tag)
    except KeyError as e:
        raise _badparam(e)
    idx.write()
    console.print(f"[bold green]Removed tag[/bold green] {tag}")


@app.command("tags")
def list_tags(
    prov_dir: Path = typer.Option(
        Path(".prov"), "--prov-dir", help="Provenance directory."
    ),
) -> None:
    """List tags."""
    _require_prov_dir(prov_dir)
    idx = _load_index_or_badparam(prov_dir)
    tags = idx.tags
    if not tags:
        console.print("(no tags)")
        return
    t = Table(title="Tags", show_lines=False)
    t.add_column("Tag", style="bold")
    t.add_column("Run ID")
    for k in sorted(tags.keys()):
        t.add_row(k, tags[k])
    console.print(t)


@app.command()
def init(
    prov_dir: Path = typer.Option(
        Path(".prov"), "--prov-dir", help="Where to store provenance artifacts."
    ),
    force: bool = typer.Option(
        False, "--force", help="Allow init even if prov dir exists."
    ),
    no_config: bool = typer.Option(
        False, "--no-config", help="Do not create a default config.yaml."
    ),
) -> None:
    """Initialize a .prov directory and defaults in the current project."""
    init_project(prov_dir=prov_dir, force=force, write_config=(not no_config))


@app.command()
def record(
    stray: Optional[str] = typer.Argument(
        None,
        help="(Do not use) If you pass a path here, you probably meant to use --inputs/--outputs.",
        show_default=False,
    ),
    name: str = typer.Option(..., "--name", help="Short name for this run.",
        callback=lambda v: _require_nonempty(v, "--name"),
    ),
    inputs: List[Path] = typer.Option(
        ..., "--inputs", help="Input files or directories.",
    ),
    outputs: List[Path] = typer.Option(
        ..., "--outputs", help="Output files or directories.",
    ),
    params: Optional[Path] = typer.Option(
        None, "--params", help="Params file (YAML/JSON)."
    ),
    prov_dir: Path = typer.Option(
        Path(".prov"), "--prov-dir", help="Provenance directory."
    ),
) -> None:
    """Record provenance after an analysis has been run."""
    if stray is not None:
        raise _badparam(
            "Unexpected argument.\n\n"
            "Did you mean:\n"
            "  prov record --name myrun --inputs <input paths...> --outputs <output paths...>\n"
            f"You passed: {stray}\n"
        )
    record_run(name=name, inputs=inputs, outputs=outputs, params=params, prov_dir=prov_dir)


@app.command()
def version(
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Show verbose version details."
    ),
) -> None:
    """Print version and exit."""
    console.print(get_version(verbose=verbose))


if __name__ == "__main__":
    app()
