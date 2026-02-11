# prov/runstore.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from .config import Defaults


@dataclass(frozen=True)
class Run:
    run_id: str
    name: str
    path: Path
    data: Dict[str, Any]


def run_dir_from_ref(prov_dir: Path, run_ref: str) -> Path:
    """
    Accept either:
      - a run_id
      - a path to a run dir
      - a path to a file under a run dir (e.g. run.json)
    """
    p = Path(run_ref)
    if p.exists():
        return p.parent if p.is_file() else p
    return prov_dir / Defaults.runs_dir_name / run_ref


def load_run(prov_dir: Path, run_ref: str) -> Run:
    run_dir = run_dir_from_ref(prov_dir, run_ref)
    run_json = run_dir / "run.json"
    if not run_json.exists():
        raise FileNotFoundError(f"Could not find run.json at {run_json}")

    data = json.loads(run_json.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid run.json at {run_json}: expected object, got {type(data).__name__}"
        )

    return Run(
        run_id=str(data.get("run_id", run_dir.name)),
        name=str(data.get("name", "")),
        path=run_dir,
        data=data,
    )

