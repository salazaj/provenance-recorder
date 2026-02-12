# prov/showcmd.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from .indexdb import load_index
from .output_json import build_show_json
from .runstore import load_run


def _hash_map(obj: object) -> dict[str, str]:
    if not isinstance(obj, dict):
        return {}
    out: dict[str, str] = {}
    for p, meta in obj.items():
        if isinstance(meta, dict) and "hash" in meta:
            out[str(p)] = str(meta["hash"])
    return out


def _fmt_text_path(p: str, *, abs_paths: bool) -> str:
    pp = Path(p)
    if abs_paths:
        return str(pp.resolve())
    try:
        return str(pp.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        return str(pp)


def show_cmd(
    *,
    ref: Optional[str],
    paths: bool,
    abs_paths: bool,
    warnings: bool,
    format: str,
    prov_dir: Path,
    hashes: bool,
    raw: bool,
    console: Console,
) -> None:
    # normalize flags
    if hashes and not paths:
        paths = True
    if abs_paths and not paths:
        paths = True

    fmt = format.lower()
    if fmt not in ("text", "json"):
        raise ValueError("format must be 'text' or 'json'")

    # raw forces json
    if raw:
        fmt = "json"

    if fmt == "json" and abs_paths:
        raise ValueError("--abs-paths is supported only for text output")

    idx = load_index(prov_dir)
    ordered = idx.ordered_run_ids()
    if not ordered:
        if fmt == "json":
            console.print_json(json.dumps({"run": None}))
        else:
            console.print("(no runs)")
        return

    run_ref = ref if ref is not None else ordered[-1]
    run = load_run(prov_dir, run_ref)

    if raw:
        console.print_json(json.dumps(run.data))
        return

    tags = idx.tags_for_run(run.run_id)
    data = run.data

    inputs_obj = data.get("inputs") or {}
    outputs_obj = data.get("outputs") or {}
    warn_obj = data.get("warnings") or []
    env_obj = data.get("environment") or {}
    params_obj = data.get("params")
    git_obj = data.get("git") if "git" in data else None

    inputs_map = _hash_map(inputs_obj)
    outputs_map = _hash_map(outputs_obj)

    counts = {
        "inputs": len(inputs_obj) if isinstance(inputs_obj, dict) else 0,
        "outputs": len(outputs_obj) if isinstance(outputs_obj, dict) else 0,
        "warnings": len(warn_obj) if isinstance(warn_obj, list) else 0,
        "has_params": bool(params_obj),
    }
    environment = {
        "python_version": str(env_obj.get("python_version", "")),
        "platform": str(env_obj.get("platform", "")),
    }

    # JSON output: abs paths intentionally NOT supported (text-only policy)
    if fmt == "json":
        paths_payload: Optional[Dict[str, Any]] = None
        if paths:
            if hashes:
                paths_payload = {"inputs": inputs_map, "outputs": outputs_map}
            else:
                paths_payload = {
                    "inputs": sorted(inputs_map.keys()),
                    "outputs": sorted(outputs_map.keys()),
                }

        warnings_payload: Optional[List[Any]] = None
        if warnings:
            warnings_payload = warn_obj if isinstance(warn_obj, list) else []

        obj = build_show_json(
            run={
                "run_id": run.run_id,
                "name": str(data.get("name", run.name or "")),
                "timestamp": str(data.get("timestamp", "")),
                "tags": tags,
            },
            counts=counts,
            environment=environment,
            git=None if git_obj is None else dict(git_obj),
            paths=paths_payload,
            warnings=warnings_payload,
        )
        console.print_json(json.dumps(obj))
        return

    # TEXT output
    console.print(f"[bold]Run[/bold] {run.run_id}")
    nm = str(data.get("name", run.name or ""))
    ts = str(data.get("timestamp", ""))
    if nm:
        console.print(f"Name: {nm}")
    if ts:
        console.print(f"Timestamp: {ts}")
    console.print(f"Path: {run.path}")
    if tags:
        console.print(f"Tags: {', '.join(tags)}")

    t = Table(title="Summary", show_lines=False)
    t.add_column("Field", style="bold")
    t.add_column("Value")
    t.add_row("Inputs", str(counts["inputs"]))
    t.add_row("Outputs", str(counts["outputs"]))
    t.add_row("Params", "present" if counts["has_params"] else "none")
    t.add_row("Warnings", str(counts["warnings"]))
    t.add_row("Python", environment["python_version"] or "(unknown)")
    t.add_row("Platform", environment["platform"] or "(unknown)")
    t.add_row("Git", "recorded" if git_obj is not None else "not recorded")
    console.print(t)

    if warnings and isinstance(warn_obj, list):
        console.print("")
        console.print("[bold]Warnings[/bold]")
        if warn_obj:
            for w in warn_obj:
                if isinstance(w, dict):
                    console.print(f"- {w.get('message', w.get('code', w))}")
                else:
                    console.print(f"- {w}")
        else:
            console.print("(none)")

    if paths:
        console.print("")
        console.print("[bold]Inputs[/bold]")
        if inputs_map:
            for p in sorted(inputs_map.keys()):
                shown = _fmt_text_path(p, abs_paths=abs_paths)
                if hashes:
                    console.print(f"- {shown}  [dim]{inputs_map[p]}[/dim]")
                else:
                    console.print(f"- {shown}")
        else:
            console.print("(none)")

        console.print("")
        console.print("[bold]Outputs[/bold]")
        if outputs_map:
            for p in sorted(outputs_map.keys()):
                shown = _fmt_text_path(p, abs_paths=abs_paths)
                if hashes:
                    console.print(f"- {shown}  [dim]{outputs_map[p]}[/dim]")
                else:
                    console.print(f"- {shown}")
        else:
            console.print("(none)")

