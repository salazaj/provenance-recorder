# tests/conftest.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
from typer.testing import CliRunner
from prov.cli import app

@pytest.fixture
def runner():
    return CliRunner()


@dataclass(frozen=True)
class ProvSandbox:
    workdir: Path
    prov_dir: Path
    run1: str
    run2: str


def _write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _mk_run(
    prov_dir: Path,
    run_id: str,
    *,
    name: str,
    timestamp: str,
    inputs: Optional[Dict[str, Dict[str, str]]] = None,
    outputs: Optional[Dict[str, Dict[str, str]]] = None,
    params_hash: Optional[str] = None,
    warnings: Optional[list] = None,
    environment: Optional[Dict[str, str]] = None,
    git: Optional[Dict[str, Any]] = None,
) -> None:
    run_dir = prov_dir / "runs" / run_id
    run_json = {
        "version": 1,
        "run_id": run_id,
        "name": name,
        "timestamp": timestamp,
        "inputs": inputs or {},
        "outputs": outputs or {},
        "params": ({"hash": params_hash} if params_hash else None),
        "warnings": warnings or [],
        "environment": environment
        or {"python_version": "3.11.0", "platform": "linux-x86_64"},
    }
    if run_json["params"] is None:
        del run_json["params"]
    if git is not None:
        run_json["git"] = git
    _write_json(run_dir / "run.json", run_json)


@pytest.fixture
def prov_sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProvSandbox:
    workdir = tmp_path
    monkeypatch.chdir(workdir)

    prov_dir = workdir / ".prov"
    prov_dir.mkdir(parents=True, exist_ok=True)
    (prov_dir / "runs").mkdir(parents=True, exist_ok=True)

    run1 = "2026-02-09T14-06-45Z_aaaaaa"
    run2 = "2026-02-11T16-08-36Z_bbbbbb"

    _mk_run(
        prov_dir,
        run1,
        name="abs_demo",
        timestamp="2026-02-09T14:06:45Z",
        inputs={"data/in.txt": {"hash": "h_in_1"}},
        outputs={"out/result.txt": {"hash": "h_out_1"}},
        params_hash="h_params",
        warnings=[{"code": "W001", "message": "something minor"}],
        git={
            "is_repo": True,
            "commit": "1111111",
            "branch": "main",
            "detached": False,
            "dirty": False,
            "untracked": False,
            "describe": "v0.1.0",
        },
    )
    _mk_run(
        prov_dir,
        run2,
        name="t",
        timestamp="2026-02-11T16:08:36Z",
        inputs={"data/in.txt": {"hash": "h_in_1"}, "data/new.txt": {"hash": "h_in_2"}},
        outputs={},  # simulate removed outputs in diff
        params_hash="h_params",
        warnings=["string warning ok too"],
        environment={"python_version": "3.12.0", "platform": "linux-x86_64"},
        git={
            "is_repo": True,
            "commit": "2222222",
            "branch": "main",
            "detached": False,
            "dirty": True,
            "untracked": True,
            "describe": "v0.1.1",
        },
    )

    index = {
        "version": 1,
        "runs": [
            {"run_id": run1, "name": "abs_demo", "timestamp": "2026-02-09T14:06:45Z"},
            {"run_id": run2, "name": "t", "timestamp": "2026-02-11T16:08:36Z"},
        ],
        "tags": {"baseline2": run1, "baseline": run2, "t": run2},
    }
    _write_json(prov_dir / "index.json", index)

    return ProvSandbox(workdir=workdir, prov_dir=prov_dir, run1=run1, run2=run2)

