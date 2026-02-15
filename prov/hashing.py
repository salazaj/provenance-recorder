from __future__ import annotations

import hashlib
from os.path import relpath
from pathlib import Path
from typing import Iterable, Dict, Callable, Optional
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


def _path_for_json(p: Path) -> str:
    try:
        if p.is_absolute():
            return relpath(str(p), str(Path.cwd()))
    except Exception:
        pass
    return str(p)


def manifest_paths(
    paths: Iterable[Path],
    algo: str = "sha256",
    recursive: bool = False,
    *,
    key_fn: Optional[Callable[[Path], str]] = None,
) -> Dict[str, dict]:
    """
    Return a manifest: {path_str: {bytes, mtime, hash}}

    Contract: path_str is never absolute.
    """
    if key_fn is None:
        key_fn = _path_for_json

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
                    manifest[key_fn(sub)] = {
                        "bytes": st.st_size,
                        **_mtime_fields(st),
                        "hash": hash_file(sub, algo),
                    }
        else:
            st = p.stat()
            manifest[key_fn(p)] = {
                "bytes": st.st_size,
                **_mtime_fields(st),
                "hash": hash_file(p, algo),
            }
    return manifest

