from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from .config import Defaults
from .runid import new_run_id
from .hashing import manifest_paths
from .env import capture_minimal_env
from datetime import datetime, timezone

console = Console()


def _append_to_index(prov_dir: Path, run_id: str, name: str) -> None:
    index_path = prov_dir / Defaults.index_file_name

    index = {
        "version": 1,
        "runs": [],
    }

    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))

    index["runs"].append(
        {
            "run_id": run_id,
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str((prov_dir / Defaults.runs_dir_name / run_id).resolve()),
        }
    )

    index_path.write_text(
        json.dumps(index, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def record_run(
    name: str,
    inputs: List[Path],
    outputs: List[Path],
    params: Optional[Path],
    prov_dir: Path,
) -> None:
    run_id = new_run_id()
    run_dir = prov_dir / Defaults.runs_dir_name / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    warnings = []

    # Inputs / outputs (truth-critical)
    inputs_manifest = manifest_paths(inputs)
    outputs_manifest = manifest_paths(outputs, recursive=True)

    # Params (optional but hashed if present)
    params_info = None
    if params:
        if not params.exists():
            raise FileNotFoundError(params)
        params_info = {
            "path": str(params),
            "bytes": params.stat().st_size,
            "hash": manifest_paths([params])[str(params)]["hash"],
        }

    env = capture_minimal_env()

    run_record = {
        "run_id": run_id,
        "name": name,
        "status": "recorded_only",
        "inputs": inputs_manifest,
        "outputs": outputs_manifest,
        "params": params_info,
        "environment": env,
        "warnings": warnings,
    }

    # Write artifacts
    (run_dir / "inputs.json").write_text(
        json.dumps(inputs_manifest, indent=2), encoding="utf-8"
    )
    (run_dir / "outputs.json").write_text(
        json.dumps(outputs_manifest, indent=2), encoding="utf-8"
    )
    (run_dir / "run.json").write_text(
        json.dumps(run_record, indent=2), encoding="utf-8"
    )

    # Human summary
    summary = [
        f"# Provenance record: {run_id}",
        "",
        f"Name: {name}",
        f"Artifacts stored at: {run_dir}",
        "",
        "## Warnings",
    ]

    if warnings:
        summary.extend(f"- {w}" for w in warnings)
    else:
        summary.append("- (none)")

    summary.extend(
        [
            "",
            "## Inputs",
            *[f"- {p}" for p in inputs_manifest.keys()],
            "",
            "## Outputs",
            *[f"- {p}" for p in outputs_manifest.keys()],
        ]
    )

    (run_dir / "RUN.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    _append_to_index(prov_dir, run_id, name)

    console.print(f"[bold green]Recorded run {run_id}[/bold green]")
    console.print(f"Artifacts: {run_dir}")
