from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Defaults:
    prov_dir_name: str = ".prov"
    runs_dir_name: str = "runs"
    index_file_name: str = "index.json"
    config_file_name: str = "config.yaml"
    gitignore_entry: str = ".prov/"


def prov_dir(path: Path | None = None) -> Path:
    return (path or Path(Defaults.prov_dir_name)).resolve()
