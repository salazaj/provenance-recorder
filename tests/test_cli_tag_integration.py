# tests/test_cli_tag_integration.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from prov.cli import app


def _write_run(prov_dir: Path, run_id: str, name: str) -> None:
    run_dir = prov_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "run.json").write_text(
        json.dumps(
            {"run_id": run_id, "name": name, "timestamp": "2026-02-11T00:00:00Z"},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_index(prov_dir: Path, runs: list[dict], tags: dict[str, str] | None = None) -> None:
    prov_dir.mkdir(parents=True, exist_ok=True)
    data = {"version": 1, "runs": runs, "tags": tags or {}}
    (prov_dir / "index.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


@pytest.fixture()
def prov_tree(runner):
    # runs entirely inside an isolated cwd
    with runner.isolated_filesystem():
        workdir = Path(".").resolve()
        prov_dir = workdir / ".prov"
        run1 = "2026-02-09T14-06-45Z_aaaaaa"
        run2 = "2026-02-11T16-08-36Z_bbbbbb"

        _write_run(prov_dir, run1, "oldest")
        _write_run(prov_dir, run2, "latest")

        runs = [
            {
                "run_id": run1,
                "name": "oldest",
                "timestamp": "2026-02-09T14:06:45Z",
                "path": f".prov/runs/{run1}",
            },
            {
                "run_id": run2,
                "name": "latest",
                "timestamp": "2026-02-11T16:08:36Z",
                "path": f".prov/runs/{run2}",
            },
        ]
        _write_index(prov_dir, runs=runs, tags={})
        yield workdir, prov_dir, run1, run2


def test_tag_by_ordinal(prov_tree, runner):
    _workdir, prov_dir, _run1, run2 = prov_tree

    res = runner.invoke(app, ["tag", "baseline", "#2"])
    assert res.exit_code == 0, res.output
    assert "Tagged baseline" in res.output
    assert run2 in res.output

    idx = json.loads((prov_dir / "index.json").read_text(encoding="utf-8"))
    assert idx["tags"]["baseline"] == run2


def test_tag_existing_tag_footgun_ambiguous(prov_tree, runner):
    _workdir, _prov_dir, _run1, _run2 = prov_tree

    res1 = runner.invoke(app, ["tag", "baseline", "#2"])
    assert res1.exit_code == 0, res1.output

    res2 = runner.invoke(app, ["tag", "baseline", "t"])
    assert res2.exit_code != 0
    assert "Ambiguous" in res2.output
    assert "Be explicit" in res2.output


def test_tag_existing_tag_force_by_run_id(prov_tree, runner):
    _workdir, prov_dir, run1, run2 = prov_tree

    res1 = runner.invoke(app, ["tag", "baseline", "#1"])
    assert res1.exit_code == 0, res1.output

    res2 = runner.invoke(app, ["tag", "--force", "baseline", run2])
    assert res2.exit_code == 0, res2.output

    idx = json.loads((prov_dir / "index.json").read_text(encoding="utf-8"))
    assert idx["tags"]["baseline"] == run2


def test_tag_existing_tag_force_by_path_to_run_json(prov_tree, runner):
    _workdir, prov_dir, _run1, run2 = prov_tree

    res1 = runner.invoke(app, ["tag", "baseline", "#1"])
    assert res1.exit_code == 0, res1.output

    run_json_path = prov_dir / "runs" / run2 / "run.json"
    assert run_json_path.exists()

    res2 = runner.invoke(app, ["tag", "--force", "baseline", str(run_json_path)])
    assert res2.exit_code == 0, res2.output

    idx = json.loads((prov_dir / "index.json").read_text(encoding="utf-8"))
    assert idx["tags"]["baseline"] == run2


def test_tags_command_shows_mapping(prov_tree, runner):
    _workdir, _prov_dir, _run1, run2 = prov_tree

    runner.invoke(app, ["tag", "baseline", "#2"])
    res = runner.invoke(app, ["tags"])

    assert res.exit_code == 0, res.output
    assert "baseline" in res.output
    assert run2 in res.output

