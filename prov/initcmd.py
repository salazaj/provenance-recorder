from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

from rich.console import Console

from .config import Defaults

console = Console()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write_json_if_missing(path: Path, obj: dict) -> bool:
    if path.exists():
        return False
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return True


def _write_text_if_missing(path: Path, text: str) -> bool:
    if path.exists():
        return False
    path.write_text(text, encoding="utf-8")
    return True


def _ensure_gitignore_has_entry(repo_root: Path, entry: str) -> Tuple[bool, Path]:
    """
    Ensure .gitignore contains the given entry (line). Returns (changed, path).
    Creates .gitignore if missing.
    """
    gitignore = repo_root / ".gitignore"
    if gitignore.exists():
        existing = gitignore.read_text(encoding="utf-8").splitlines()
    else:
        existing = []

    # Normalize: accept ".prov" or ".prov/" equivalently; we will write ".prov/".
    normalized = {
        line.strip()
        for line in existing
        if line.strip() and not line.strip().startswith("#")
    }
    if entry in normalized or entry.rstrip("/") in normalized:
        return (False, gitignore)

    # Append with a newline if file non-empty and last line not blank
    content = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if content and not content.endswith("\n"):
        content += "\n"
    if content and not content.endswith("\n\n"):
        # keep it simple: ensure at least one newline before appending
        pass
    content += f"{entry}\n"
    gitignore.write_text(content, encoding="utf-8")
    return (True, gitignore)


def init_project(
    prov_dir: Path, force: bool = False, write_config: bool = True
) -> None:
    """
    Initialize the .prov structure in the current repo.
    """
    repo_root = Path.cwd()
    runs_dir = prov_dir / Defaults.runs_dir_name
    index_path = prov_dir / Defaults.index_file_name
    config_path = prov_dir / Defaults.config_file_name

    if prov_dir.exists() and not force:
        # If .prov exists, we treat init as idempotent *unless* it's a file.
        if prov_dir.is_file():
            raise RuntimeError(f"{prov_dir} exists and is a file.")
    _ensure_dir(runs_dir)

    created_index = _write_json_if_missing(
        index_path,
        {"version": 1, "runs": []},
    )

    created_config = False
    if write_config:
        created_config = _write_text_if_missing(
            config_path,
            "# provenance-recorder config (v1)\n"
            "redact_paths: true\n"
            "hash_method: sha256\n"
            "hash_mode: strict  # strict | fast\n"
            "store_env: minimal # none | minimal | full\n"
            "git: auto          # auto | require | off\n",
        )

    gitignore_changed, gitignore_path = _ensure_gitignore_has_entry(
        repo_root, Defaults.gitignore_entry
    )

    # Summary (explicit, as requested)
    console.print("[bold]Initialized provenance-recorder[/bold]")
    console.print(f"Artifacts directory: [cyan]{prov_dir}[/cyan]")
    console.print(f"Runs stored at:       [cyan]{runs_dir}[/cyan]")
    console.print(
        f"Index file:           [cyan]{index_path}[/cyan] ({'created' if created_index else 'exists'})"
    )
    if write_config:
        console.print(
            f"Config file:          [cyan]{config_path}[/cyan] ({'created' if created_config else 'exists'})"
        )
    console.print(
        f"Default gitignore:    [cyan]{Defaults.gitignore_entry}[/cyan] "
        f"({'added to ' + str(gitignore_path) if gitignore_changed else 'already present'})"
    )
