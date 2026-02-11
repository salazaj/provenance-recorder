# prov/repair.py
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .indexdb import IndexDB, load_index
from .config import Defaults

_RUNID_TS_RE = re.compile(
    r"^(?P<Y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})T(?P<H>\d{2})-(?P<M>\d{2})-(?P<S>\d{2})Z"
)



@dataclass(frozen=True)
class RepairResult:
    runs_count: int
    tags_kept: int
    tags_total_before: int
    backup_path: Path | None
    warnings: List[str]
    timestamps_added: int


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _infer_timestamp_from_run_id(run_id: str) -> Optional[str]:
    """
    Run IDs look like: 2026-02-09T14-06-45Z_594e12
    Convert to:       2026-02-09T14:06:45Z
    """
    prefix = run_id.split("_", 1)[0]  # "2026-02-09T14-06-45Z"
    m = _RUNID_TS_RE.match(prefix)
    if not m:
        return None

    g = m.groupdict()
    ts = f"{g['Y']}-{g['m']}-{g['d']}T{g['H']}:{g['M']}:{g['S']}Z"

    # sanity check: parseable
    try:
        datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return ts


def _read_json_object(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"expected JSON object, got {type(obj).__name__}")
    return obj


def rebuild_runs_from_disk(
    prov_dir: Path, dry_run: bool
) -> Tuple[List[dict], List[str], int]:
    runs_dir = prov_dir / "runs"
    warnings: List[str] = []
    runs: List[dict] = []
    timestamps_added = 0

    if not runs_dir.exists():
        return ([], [f"{runs_dir} does not exist. Nothing to rebuild."], 0)

    for d in sorted(runs_dir.iterdir()):
        if not d.is_dir():
            continue

        run_json = d / "run.json"
        if not run_json.exists():
            warnings.append(
                f"Missing run.json in runs/{d.name} (skipping). "
                "If this is a partial/corrupt run, you can delete the directory."
            )
            continue

        try:
            obj = _read_json_object(run_json)
        except Exception as e:
            warnings.append(f"Invalid run.json in {run_json}: {e}")
            continue

        run_id = str(obj.get("run_id") or d.name)
        name = str(obj.get("name") or "")

        ts = str(obj.get("timestamp") or "").strip()
        if not ts:
            inferred = _infer_timestamp_from_run_id(run_id) or _infer_timestamp_from_run_id(d.name)
            if inferred:
                obj["timestamp"] = inferred
                ts = inferred
                timestamps_added += 1
                if not dry_run:
                    run_json.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            else:
                warnings.append(f"Missing timestamp in {run_json} and could not infer from run_id")

        # portable path only
        runs.append(
            {
                "run_id": run_id,
                "name": name,
                "timestamp": ts,
                "path": str(Path(Defaults.prov_dir_name) / Defaults.runs_dir_name / d.name),
            }
        )
        runs.sort(key=lambda r: (r.get("timestamp") or "", r.get("run_id") or ""))

    return (runs, warnings, timestamps_added)


def build_repaired_index_data(
    prov_dir: Path,
    keep_tags: bool,
    dry_run: bool,
) -> Tuple[Dict[str, Any], RepairResult]:
    existing_tags: Dict[str, str] = {}
    tags_total_before = 0

    if keep_tags and (prov_dir / "index.json").exists():
        try:
            idx: IndexDB = load_index(prov_dir)
            existing_tags = idx.tags
            tags_total_before = len(existing_tags)
        except ValueError:
            existing_tags = {}
            tags_total_before = 0

    runs, warnings, timestamps_added = rebuild_runs_from_disk(prov_dir, dry_run=dry_run)
    run_ids = {r.get("run_id") for r in runs if isinstance(r, dict)}
    kept_tags = {t: rid for t, rid in existing_tags.items() if rid in run_ids}

    data: Dict[str, Any] = {
        "version": 1,
        "runs": runs,
        "tags": dict(sorted(kept_tags.items(), key=lambda kv: kv[0])),
    }

    result = RepairResult(
        runs_count=len(runs),
        tags_kept=len(kept_tags),
        tags_total_before=tags_total_before,
        backup_path=None,
        warnings=warnings,
        timestamps_added=timestamps_added,
    )
    return data, result


def repair_index(
    prov_dir: Path,
    backup: bool = True,
    keep_tags: bool = True,
    dry_run: bool = False,
) -> Tuple[Dict[str, Any], RepairResult]:
    index_path = prov_dir / "index.json"
    data, result = build_repaired_index_data(prov_dir, keep_tags=keep_tags, dry_run=dry_run)

    bak_path: Path | None = None
    if not dry_run and backup and index_path.exists():
        bak_path = prov_dir / f"index.json.bak-{_utc_stamp()}"
        shutil.copy2(index_path, bak_path)

    if not dry_run:
        index_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return data, RepairResult(
        runs_count=result.runs_count,
        tags_kept=result.tags_kept,
        tags_total_before=result.tags_total_before,
        backup_path=bak_path,
        warnings=result.warnings,
        timestamps_added=result.timestamps_added,
    )

