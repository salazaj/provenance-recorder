# prov/diff.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from rich.console import Console
from rich.table import Table

from .config import Defaults
from .indexdb import load_index
from .runstore import Run, load_run

console = Console()

FailOn = Literal["none", "truth", "any"]
OutFormat = Literal["text", "json"]


def _fingerprint_map(run: Run, key: str) -> Dict[str, str]:
    m = run.data.get(key) or {}
    out: Dict[str, str] = {}
    for p, meta in m.items():
        if isinstance(meta, dict) and "hash" in meta:
            out[p] = str(meta["hash"])
    return out


def _diff_hashmaps(a: Dict[str, str], b: Dict[str, str]) -> Dict[str, List[str]]:
    a_keys = set(a.keys())
    b_keys = set(b.keys())
    added = sorted(b_keys - a_keys)
    removed = sorted(a_keys - b_keys)
    common = sorted(a_keys & b_keys)
    changed: List[str] = []
    unchanged: List[str] = []
    for k in common:
        if a[k] != b[k]:
            changed.append(k)
        else:
            unchanged.append(k)
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
    }


def _params_fingerprint(run: Run) -> Optional[str]:
    p = run.data.get("params")
    if not p:
        return None
    if isinstance(p, dict) and "hash" in p:
        return str(p["hash"])
    return None


def _env_fingerprint(run: Run) -> Dict[str, str]:
    env = run.data.get("environment") or {}
    return {
        "python_version": str(env.get("python_version", "")),
        "platform": str(env.get("platform", "")),
    }


def _warnings_list(run: Run) -> List[str]:
    w = run.data.get("warnings") or []
    out: List[str] = []
    for item in w:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            msg = item.get("message") or item.get("code") or str(item)
            out.append(str(msg))
        else:
            out.append(str(item))
    return out


def _git_fingerprint(run: Run) -> Dict[str, Any]:
    if "git" not in run.data:
        return {"recorded": False}
    g = run.data.get("git") or {}
    return {
        "recorded": True,
        "is_repo": bool(g.get("is_repo", False)),
        "commit": g.get("commit"),
        "describe": g.get("describe"),
        "branch": g.get("branch"),
        "detached": g.get("detached"),
        "dirty": g.get("dirty"),
        "untracked": g.get("untracked"),
    }


def _git_changed(a: Dict[str, Any], b: Dict[str, Any]) -> Tuple[bool, List[str]]:
    a_rec = bool(a.get("recorded"))
    b_rec = bool(b.get("recorded"))

    # If either run doesn't have git metadata, do not treat as a diff.
    if not a_rec or not b_rec:
        reasons: List[str] = []
        if not a_rec and not b_rec:
            reasons.append("not recorded (A, B)")
        elif not a_rec:
            reasons.append("not recorded (A)")
        else:
            reasons.append("not recorded (B)")
        return False, reasons

    reasons: List[str] = []
    if a.get("is_repo") != b.get("is_repo"):
        reasons.append("repo status changed")
        return True, reasons

    if not a.get("is_repo") and not b.get("is_repo"):
        return False, reasons

    for k, label in [
        ("commit", "commit"),
        ("branch", "branch"),
        ("detached", "detached"),
        ("dirty", "dirty"),
        ("untracked", "untracked"),
    ]:
        if a.get(k) != b.get(k):
            reasons.append(f"{label} changed")
    return (len(reasons) > 0), reasons


def _truth_changed(diff_inputs: Dict[str, List[str]], params_changed: bool) -> bool:
    return bool(
        diff_inputs["added"]
        or diff_inputs["removed"]
        or diff_inputs["changed"]
        or params_changed
    )


def _any_changed(
    truth_changed: bool,
    diff_outputs: Dict[str, List[str]],
    env_changed: bool,
    warnings_changed: bool,
    git_changed: bool,
) -> bool:
    return (
        truth_changed
        or bool(
            diff_outputs["added"] or diff_outputs["removed"] or diff_outputs["changed"]
        )
        or env_changed
        or warnings_changed
        or git_changed
    )


def _fmt_path(p: str, abs_paths: bool) -> str:
    path = Path(p)
    if abs_paths:
        return str(path.resolve())
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        return str(path)


def diff_runs(
    prov_dir: Path,
    run_a: str,
    run_b: str,
    show_paths: bool = False,
    abs_paths: bool = False,
    show_warnings: bool = False,
    out_format: OutFormat = "text",
    fail_on: FailOn = "none",
) -> int:
    ra = load_run(prov_dir, run_a)
    rb = load_run(prov_dir, run_b)

    idx = load_index(prov_dir)
    a_tags = idx.tags_for_run(ra.run_id)
    b_tags = idx.tags_for_run(rb.run_id)

    a_inputs = _fingerprint_map(ra, "inputs")
    b_inputs = _fingerprint_map(rb, "inputs")
    a_outputs = _fingerprint_map(ra, "outputs")
    b_outputs = _fingerprint_map(rb, "outputs")

    diff_inputs = _diff_hashmaps(a_inputs, b_inputs)
    diff_outputs = _diff_hashmaps(a_outputs, b_outputs)

    a_params = _params_fingerprint(ra)
    b_params = _params_fingerprint(rb)
    params_changed = a_params != b_params

    a_env = _env_fingerprint(ra)
    b_env = _env_fingerprint(rb)
    env_changed = a_env != b_env

    a_warn = _warnings_list(ra)
    b_warn = _warnings_list(rb)
    warnings_changed = a_warn != b_warn

    a_git = _git_fingerprint(ra)
    b_git = _git_fingerprint(rb)
    git_changed, git_reasons = _git_changed(a_git, b_git)

    truth_changed = _truth_changed(diff_inputs, params_changed)
    any_changed = _any_changed(
        truth_changed, diff_outputs, env_changed, warnings_changed, git_changed
    )

    result_obj = {
        "run_a": {
            "run_id": ra.run_id,
            "name": ra.name,
            "path": str(ra.path),
            "tags": a_tags,
        },
        "run_b": {
            "run_id": rb.run_id,
            "name": rb.name,
            "path": str(rb.path),
            "tags": b_tags,
        },
        "warnings": {"a": a_warn, "b": b_warn, "changed": warnings_changed},
        "inputs": diff_inputs,
        "outputs": diff_outputs,
        "params": {"a": a_params, "b": b_params, "changed": params_changed},
        "environment": {"a": a_env, "b": b_env, "changed": env_changed},
        "git": {
            "a": a_git,
            "b": b_git,
            "recorded": {
                "a": a_git.get("recorded", False),
                "b": b_git.get("recorded", False),
            },
            "changed": git_changed,
            "reasons": git_reasons,
        },
        "summary": {"truth_changed": truth_changed, "any_changed": any_changed},
    }

    if out_format == "json":
        console.print_json(json.dumps(result_obj))
    else:

        def _tag_suffix(tags: List[str]) -> str:
            return f" ({', '.join(tags)})" if tags else ""

        console.print(f"[bold]Diff[/bold] {ra.run_id}  →  {rb.run_id}")
        console.print(f"A: {ra.name}{_tag_suffix(a_tags)}  ({ra.path})")
        console.print(f"B: {rb.name}{_tag_suffix(b_tags)}  ({rb.path})")
        console.print("")

        print_warn_details = show_paths or show_warnings
        console.print("[bold]Warnings[/bold]")
        if a_warn:
            console.print(f"- A: {len(a_warn)} warning(s)")
            if print_warn_details:
                for w in a_warn:
                    console.print(f"  - {w}")
        else:
            console.print("- A: (none)")
        if b_warn:
            console.print(f"- B: {len(b_warn)} warning(s)")
            if print_warn_details:
                for w in b_warn:
                    console.print(f"  - {w}")
        else:
            console.print("- B: (none)")
        console.print("")

        t = Table(title="Summary", show_lines=False)
        t.add_column("Section", style="bold")
        t.add_column("Changed?")
        t.add_column("Details")

        def _counts(d: Dict[str, List[str]]) -> str:
            return f"added {len(d['added'])}, removed {len(d['removed'])}, changed {len(d['changed'])}"

        t.add_row(
            "Inputs (truth)",
            "YES"
            if (
                diff_inputs["added"] or diff_inputs["removed"] or diff_inputs["changed"]
            )
            else "no",
            _counts(diff_inputs),
        )
        t.add_row(
            "Params (truth)",
            "YES" if params_changed else "no",
            "hash differs" if params_changed else "same",
        )
        t.add_row(
            "Outputs",
            "YES"
            if (
                diff_outputs["added"]
                or diff_outputs["removed"]
                or diff_outputs["changed"]
            )
            else "no",
            _counts(diff_outputs),
        )
        t.add_row(
            "Environment",
            "YES" if env_changed else "no",
            "python/platform differs" if env_changed else "same",
        )
        t.add_row(
            "Git",
            "YES" if git_changed else "no",
            ", ".join(git_reasons) if git_reasons else "same",
        )
        console.print(t)

        if show_paths:

            def _print_section(title: str, d: Dict[str, List[str]]) -> None:
                console.print("")
                console.print(f"[bold]{title}[/bold]")
                for k in ("added", "removed", "changed"):
                    if d[k]:
                        console.print(f"- {k}:")
                        for pth in d[k]:
                            console.print(f"  - {_fmt_path(pth, abs_paths)}")
                    else:
                        console.print(f"- {k}: (none)")

            _print_section("Inputs details", diff_inputs)
            _print_section("Outputs details", diff_outputs)

            if params_changed:
                console.print("")
                console.print("[bold]Params[/bold]")
                console.print(f"- A: {a_params}")
                console.print(f"- B: {b_params}")

            if env_changed:
                console.print("")
                console.print("[bold]Environment[/bold]")
                console.print(f"- A: {a_env}")
                console.print(f"- B: {b_env}")

            if git_changed or (
                git_reasons and any("not recorded" in r for r in git_reasons)
            ):
                console.print("")
                console.print("[bold]Git[/bold]")
                if git_reasons and any("not recorded" in r for r in git_reasons):
                    console.print(f"- {', '.join(git_reasons)}")
                console.print(
                    f"- A: {a_git if a_git.get('recorded') else '(not recorded)'}"
                )
                console.print(
                    f"- B: {b_git if b_git.get('recorded') else '(not recorded)'}"
                )

    if fail_on == "none":
        return 0
    if fail_on == "truth" and truth_changed:
        return 5
    if fail_on == "any" and any_changed:
        return 5
    return 0
