from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, Dict
from datetime import datetime, timezone


def _mtime_fields(stat) -> dict:
    m = int(stat.st_mtime)
    return {
        "mtime_epoch": m,
        "mtime_utc": datetime.fromtimestamp(m, tz=timezone.utc).isoformat(),
    }


def hash_file(path: Path, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_paths(
    paths: Iterable[Path],
    algo: str = "sha256",
    recursive: bool = False,
) -> Dict[str, dict]:
    """
    Return a manifest: {path_str: {bytes, mtime, hash}}
    """
    manifest: Dict[str, dict] = {}

    for p in paths:
        if not p.exists():
            raise FileNotFoundError(p)

        if p.is_dir():
            if not recursive:
                continue
            for sub in sorted(p.rglob("*")):
                if sub.is_file():
                    st = sub.stat()
                    manifest[str(sub)] = {
                        "bytes": st.st_size,
                        **_mtime_fields(st),
                        "hash": hash_file(sub, algo),
                    }
        else:
            st = p.stat()
            manifest[str(p)] = {
                "bytes": st.st_size,
                **_mtime_fields(st),
                "hash": hash_file(p, algo),
            }

    return manifest
