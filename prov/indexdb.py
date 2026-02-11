# prov/indexdb.py
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple
from json import JSONDecodeError

from .config import Defaults


def _parse_ts(ts: str) -> float:
    ts = str(ts).strip()
    if not ts:
        raise ValueError("empty timestamp")
    if ts.endswith("Z"):
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return dt.timestamp()
    return datetime.fromisoformat(ts).timestamp()


_TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def validate_tag_name(tag: str) -> None:
    """
    Reject ambiguous/footgun tag names:
      - digits-only (collides with ordinals)
      - "#N" (collides with ordinals)
      - whitespace
      - characters outside [A-Za-z0-9._-]
    """
    t = tag.strip()
    if t != tag:
        raise ValueError("Tag must not have leading/trailing whitespace.")
    if any(ch.isspace() for ch in tag):
        raise ValueError("Tag must not contain whitespace.")
    if tag.isdigit():
        raise ValueError("Tag must not be all digits (would collide with ordinals).")
    if tag.startswith("#") and tag[1:].isdigit():
        raise ValueError("Tag must not look like an ordinal (e.g. '#3').")
    if not _TAG_RE.fullmatch(tag):
        raise ValueError("Tag must match: [A-Za-z0-9][A-Za-z0-9._-]*")


@dataclass
class IndexDB:
    version: int
    data: Dict[str, Any]
    path: Path

    @property
    def runs(self) -> list[dict]:
        return list(self.data.get("runs") or [])

    @property
    def tags(self) -> Dict[str, str]:
        t = self.data.get("tags")
        if isinstance(t, dict):
            return {str(k): str(v) for k, v in t.items()}
        return {}

    def ordered_run_ids(self) -> list[str]:
        """
        Return run_ids sorted by timestamp ascending (oldest first).
        Ignores malformed entries rather than crashing.
        """
        sortable: list[Tuple[float, str]] = []
        for r in self.runs:
            if not isinstance(r, dict):
                continue
            run_id = r.get("run_id")
            ts = r.get("timestamp")
            if not run_id or not ts:
                continue
            try:
                sortable.append((_parse_ts(ts), str(run_id)))
            except Exception:
                continue
        sortable.sort(key=lambda x: x[0])
        return [rid for _, rid in sortable]

    def resolve_ordinal(self, n: int) -> str:
        """
        1-based ordinal. oldest=1.
        """
        ordered = self.ordered_run_ids()
        if n < 1 or n > len(ordered):
            raise ValueError(f"Run index {n} out of range (1..{len(ordered)}).")
        return ordered[n - 1]

    def tags_for_run(self, run_id: str) -> list[str]:
        out: list[str] = []
        for tag, rid in self.tags.items():
            if rid == run_id:
                out.append(tag)
        return sorted(out)

    def run_ids_for_tags(self, tags: Iterable[str]) -> Dict[str, str]:
        """
        Return {tag: run_id} for any tags that exist.
        """
        all_tags = self.tags
        return {t: all_tags[t] for t in tags if t in all_tags}

    def set_tag(self, tag: str, run_id: str, force: bool = False) -> None:
        validate_tag_name(tag)

        tags = self.tags
        if (tag in tags) and not force:
            raise ValueError(f"Tag '{tag}' already exists (use --force to overwrite).")
        tags[tag] = run_id
        self.data["tags"] = dict(sorted(tags.items(), key=lambda kv: kv[0]))

    def del_tag(self, tag: str) -> None:
        tags = self.tags
        if tag not in tags:
            raise KeyError(f"Tag '{tag}' does not exist.")
        del tags[tag]
        self.data["tags"] = dict(sorted(tags.items(), key=lambda kv: kv[0]))

    def write(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2) + "\n", encoding="utf-8")


def load_index(prov_dir: Path) -> IndexDB:
    p = prov_dir / Defaults.index_file_name
    if not p.exists():
        data: Dict[str, Any] = {"version": 1, "runs": [], "tags": {}}
        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return IndexDB(version=1, data=data, path=p)

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in index file {p}: {e}")

    # ✅ NEW: ensure top-level is an object
    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid JSON in index file {p}: expected an object, got {type(data).__name__}."
        )

    data.setdefault("version", 1)
    data.setdefault("runs", [])
    data.setdefault("tags", {})

    # Optional extra hardening (recommended):
    if not isinstance(data["runs"], list):
        raise ValueError(f"Invalid index file {p}: 'runs' must be a list.")
    if not isinstance(data["tags"], dict):
        raise ValueError(f"Invalid index file {p}: 'tags' must be an object/dict.")

    return IndexDB(version=int(data.get("version", 1)), data=data, path=p)
