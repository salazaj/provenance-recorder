from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner
from prov.cli import app
from prov.diff import diff_runs

runner = CliRunner()


def _write_run(run_dir: Path, run_id: str, name: str, *, with_git: bool) -> None:
    run_dir.mkdir(parents=True, exist_ok=False)
    data = {
        "run_id": run_id,
        "name": name,
        "inputs": {"in.txt": {"hash": "aaa"}},
        "outputs": {"out.txt": {"hash": "bbb"}},
        "params": None,
        "environment": {"python_version": "3.x", "platform": "linux"},
        "warnings": [],
    }
    if with_git:
        data["git"] = {
            "is_repo": True,
            "commit": "deadbeef",
            "describe": "deadbeef",
            "branch": "main",
            "detached": False,
            "dirty": False,
            "untracked": 0,
        }
    (run_dir / "run.json").write_text(json.dumps(data), encoding="utf-8")


def test_git_missing_is_not_a_change(tmp_path: Path) -> None:
    prov_dir = tmp_path / ".prov"
    runs_dir = prov_dir / "runs"
    runs_dir.mkdir(parents=True)

    a_id = "A"
    b_id = "B"
    _write_run(runs_dir / a_id, a_id, "a", with_git=False)
    _write_run(runs_dir / b_id, b_id, "b", with_git=True)

    # Should not treat git as "changed" when one side didn't record it.
    code = diff_runs(
        prov_dir=prov_dir,
        run_a=a_id,
        run_b=b_id,
        show_paths=False,
        abs_paths=False,
        out_format="json",
        fail_on="any",
    )
    assert code == 0  # because git_changed=false in this case


def test_show_raw_json(prov_sandbox):
    res = runner.invoke(app, ["show", "baseline", "--raw"])
    assert res.exit_code == 0
    obj = json.loads(res.stdout)
    assert obj["run_id"] == "2026-02-11T16-08-36Z_bbbbbb"


def test_show_hashes_text(prov_sandbox):
    res = runner.invoke(app, ["show", "baseline", "--paths", "--hashes"])
    assert res.exit_code == 0
    assert "Inputs" in res.output
    assert "h_in_1" in res.output  # from fixture

