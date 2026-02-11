from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _git(args: list[str], cwd: Path) -> str:
    r = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "git command failed")
    return r.stdout.strip()


@dataclass(frozen=True)
class GitInfo:
    is_repo: bool
    root: Optional[str] = None
    commit: Optional[str] = None
    branch: Optional[str] = None
    detached: Optional[bool] = None
    dirty: Optional[bool] = None
    untracked: Optional[int] = None
    describe: Optional[str] = None


def capture_git_info(cwd: Path) -> GitInfo:
    try:
        root = _git(["rev-parse", "--show-toplevel"], cwd)
    except Exception:
        return GitInfo(is_repo=False)

    # commit
    commit = _git(["rev-parse", "HEAD"], cwd)

    # branch / detached
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    detached = branch == "HEAD"

    # dirty + untracked
    status = _git(["status", "--porcelain"], cwd).splitlines()
    untracked = sum(1 for line in status if line.startswith("??"))
    dirty = any(line and not line.startswith("??") for line in status)

    # describe (best effort)
    try:
        describe = _git(["describe", "--tags", "--always", "--dirty"], cwd)
    except Exception:
        describe = None

    return GitInfo(
        is_repo=True,
        root=root,
        commit=commit,
        branch=None if detached else branch,
        detached=detached,
        dirty=dirty,
        untracked=untracked,
        describe=describe,
    )
