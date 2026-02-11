# prov/record.py
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from .config import Defaults
from .env import capture_minimal_env
from .gitinfo import capture_git_info
from .hashing import manifest_paths
from .indexdb import load_index
from .runid import new_run_id

console = Console()


def _utc_timestamp() -> str:
    # ISO8601 UTC with Z, second precision
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _append_to_index(prov_dir: Path, run_id: str, name: str, timestamp: str) -> None:
    idx = load_index(prov_dir)
    run_rel = str(Path(Defaults.prov_dir_name) / Defaults.runs_dir_name / run_id)

    idx.data.setdefault("runs", [])
    idx.data["runs"].append(
        {
            "run_id": run_id,
            "name": name,
            "timestamp": timestamp,
            "path": run_rel,
        }
    )
    idx.write()


def record_run(
    name: str,
    inputs: List[Path],
    outputs: List[Path],
    params: Optional[Path],
    prov_dir: Path,
) -> None:
    run_id = new_run_id()
    ts = _utc_timestamp()

    run_dir = prov_dir / Defaults.runs_dir_name / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    warnings: list[str] = []

    git = capture_git_info(Path.cwd())
    if not git.is_repo:
        warnings.append("GIT_NOT_A_REPO: not inside a git repository")
    else:
        if git.detached:
            warnings.append("GIT_DETACHED_HEAD: HEAD is detached")
        if git.dirty:
            warnings.append("GIT_DIRTY: working tree has uncommitted changes")
        if (git.untracked or 0) > 0:
            warnings.append(f"GIT_UNTRACKED: {git.untracked} untracked file(s)")

    inputs_manifest = manifest_paths(inputs)
    outputs_manifest = manifest_paths(outputs, recursive=True)

    params_info = None
    if params:
        if not params.exists():
            raise FileNotFoundError(params)
        params_manifest = manifest_paths([params])
        params_info = {
            "path": str(params),
            "bytes": params.stat().st_size,
            "hash": params_manifest[str(params)]["hash"],
        }

    env = capture_minimal_env()

    run_record = {
        "run_id": run_id,
        "timestamp": ts,
        "name": name,
        "status": "recorded_only",
        "inputs": inputs_manifest,
        "outputs": outputs_manifest,
        "params": params_info,
        "environment": env,
        "warnings": warnings,
        "git": {
            "is_repo": git.is_repo,
            "root": git.root,
            "commit": git.commit,
            "branch": git.branch,
            "detached": git.detached,
            "dirty": git.dirty,
            "untracked": git.untracked,
            "describe": git.describe,
        },
    }

    (run_dir / "inputs.json").write_text(json.dumps(inputs_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "outputs.json").write_text(json.dumps(outputs_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "run.json").write_text(json.dumps(run_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = [
        f"# Provenance record: {run_id}",
        "",
        f"Name: {name}",
        f"Timestamp: {ts}",
        f"Artifacts stored at: {run_dir}",
        "",
        "## Warnings",
    ]
    summary.extend((f"- {w}" for w in warnings) if warnings else ["- (none)"])
    summary.extend(
        [
            "",
            "## Inputs",
            *[f"- {p}" for p in inputs_manifest.keys()],
            "",
            "## Outputs",
            *[f"- {p}" for p in outputs_manifest.keys()],
            "",
            "## Git",
        ]
    )
    if git.is_repo:
        summary.append(f"- commit: {git.commit}")
        summary.append(f"- describe: {git.describe}")
        summary.append(f"- branch: {git.branch if git.branch else '(detached)'}")
        summary.append(f"- dirty: {git.dirty}")
        summary.append(f"- untracked: {git.untracked}")
    else:
        summary.append("- (not a git repository)")

    (run_dir / "RUN.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    _append_to_index(prov_dir, run_id, name, ts)

    console.print(f"[bold green]Recorded run {run_id}[/bold green]")
    console.print(f"Artifacts: {run_dir}")

