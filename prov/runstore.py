# prov/runstore.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .config import Defaults
from .indexdb import load_index


@dataclass(frozen=True)
class Run:
    run_id: str
    name: str
    path: Path
    data: Dict[str, Any]


def latest_run_id(prov_dir: Path) -> str:
    idx = load_index(prov_dir)
    ordered = idx.ordered_run_ids()
    if not ordered:
        raise RuntimeError("No runs recorded.")
    return ordered[-1]


def run_exists(prov_dir: Path, ref: str) -> bool:
    try:
        d = run_dir_from_ref(prov_dir, ref)
    except Exception:
        return False
    return (d / "run.json").exists()


def _find_run_dir(prov_dir: Path, p: Path) -> Path:
    runs_root = (prov_dir / Defaults.runs_dir_name).resolve()

    cur = p.resolve()
    if cur.is_file():
        cur = cur.parent

    # Walk up until parent is runs_root (so cur.name is run_id)
    while True:
        parent = cur.parent
        if parent == runs_root:
            return cur
        if cur == parent:  # hit filesystem root
            break
        cur = parent

    # Fall back to original behavior if not under runs_root
    return cur if cur.exists() else (p.parent if p.is_file() else p)


def resolve_ref(prov_dir: Path, ref: str) -> str:
    """
    Turn user input into either:
      - an existing path (returned as-is), OR
      - a run_id string

    Supports:
      - existing path
      - tag
      - ordinal "#N" (1-based; oldest=1)
      - bare integer "N" (treated as ordinal)
      - run_id (as-is)
    """
    ref = ref.strip()
    p = Path(ref)
    if p.exists():
        return ref

    idx = load_index(prov_dir)

    # tag
    if ref in idx.tags:
        return idx.tags[ref]

    # ordinal forms
    if ref.startswith("#") and ref[1:].isdigit():
        return idx.resolve_ordinal(int(ref[1:]))
    if ref.isdigit():
        return idx.resolve_ordinal(int(ref))

    # assume run_id
    return ref


def run_id_from_ref(prov_dir: Path, ref: str) -> str:
    """
    Return a run_id for any supported ref type, including paths to:
      - run dir
      - run.json
      - other files under a run dir
    """
    resolved = resolve_ref(prov_dir, ref)
    p = Path(resolved)
    if p.exists():
        run_dir = _find_run_dir(prov_dir, p)
        return run_dir.name
    return resolved


def run_dir_from_ref(prov_dir: Path, run_ref: str) -> Path:
    """
    Accept either:
      - run_id
      - tag / ordinal
      - path to a run dir
      - path to a file under a run dir (e.g. run.json)
    """
    resolved = resolve_ref(prov_dir, run_ref)
    p = Path(resolved)
    if p.exists():
        return _find_run_dir(prov_dir, p)
    return prov_dir / Defaults.runs_dir_name / resolved


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


def resolve_run_pair(
    prov_dir: Path, run_a: Optional[str], run_b: Optional[str]
) -> Tuple[str, str]:
    """
    Resolve intended (A, B) run refs given 0/1/2 user-supplied args.

    Behavior:
      - no args: last two (by index ordering)
      - one arg X: X vs latest (unless X resolves to latest => previous vs latest)
      - two args: A vs B
    """
    idx = load_index(prov_dir)
    ordered = idx.ordered_run_ids()

    if run_a is None and run_b is None:
        if len(ordered) < 2:
            raise RuntimeError("Need at least two recorded runs to diff. Run `prov record` first.")
        return (ordered[-2], ordered[-1])

    if run_a is not None and run_b is None:
        if len(ordered) < 2:
            raise RuntimeError("Need at least two recorded runs to diff. Run `prov record` first.")
        latest = ordered[-1]
        prev = ordered[-2]

        a_id = run_id_from_ref(prov_dir, run_a)
        if a_id == latest:
            return (prev, latest)

        # Keep the user's original ref form (tag/path/run_id) for nice UX,
        # but it's now safe because load_run() can handle it.
        return (run_a, latest)

    assert run_a is not None and run_b is not None
    return (run_a, run_b)

