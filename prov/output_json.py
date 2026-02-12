# prov/output_json.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict


def counts_for_diff(d: Dict[str, List[str]]) -> Dict[str, int]:
    return {
        "added": len(d.get("added", [])),
        "removed": len(d.get("removed", [])),
        "changed": len(d.get("changed", [])),
    }


def build_diff_json(
    *,
    a: Dict[str, Any],
    b: Dict[str, Any],
    diff_inputs: Dict[str, List[str]],
    diff_outputs: Dict[str, List[str]],
    params: Dict[str, Any],
    environment: Dict[str, Any],
    git: Dict[str, Any],
    warnings: Optional[Dict[str, Any]],
    truth_changed: bool,
    any_changed: bool,
    include_paths: bool,
) -> Dict[str, Any]:
    obj: Dict[str, Any] = {
        "a": {"run_id": a["run_id"], "name": a.get("name", ""), "tags": a.get("tags", [])},
        "b": {"run_id": b["run_id"], "name": b.get("name", ""), "tags": b.get("tags", [])},
        "summary": {
            "truth_changed": truth_changed,
            "any_changed": any_changed,
            "counts": {
                "inputs": counts_for_diff(diff_inputs),
                "outputs": counts_for_diff(diff_outputs),
                "params_changed": bool(params.get("changed", False)),
                "env_changed": bool(environment.get("changed", False)),
                "git_changed": bool(git.get("changed", False)),
                "warnings_changed": bool(warnings.get("changed", False)) if warnings else False,
            },
        },
        "params": params,
        "environment": environment,
        "git": git,
    }

    if include_paths:
        obj["inputs"] = {k: diff_inputs.get(k, []) for k in ("added", "removed", "changed")}
        obj["outputs"] = {k: diff_outputs.get(k, []) for k in ("added", "removed", "changed")}

    if warnings is not None:
        obj["warnings"] = warnings

    return obj


def build_show_json(
    *,
    run: Dict[str, Any],
    counts: Dict[str, Any],
    environment: Dict[str, Any],
    git: Optional[Dict[str, Any]],
    paths: Optional[Dict[str, Any]],
    warnings: Optional[List[Any]],
) -> Dict[str, Any]:
    obj: Dict[str, Any] = {
        "run": {
            "run_id": run.get("run_id", ""),
            "name": run.get("name", ""),
            "timestamp": run.get("timestamp", ""),
            "tags": run.get("tags", []),
        },
        "counts": counts,
        "environment": environment,
        "git": git,
    }
    if paths is not None:
        obj["paths"] = paths
    if warnings is not None:
        obj["warnings"] = warnings
    return obj

