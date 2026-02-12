# tests/test_cli_show.py
from __future__ import annotations

import json

from prov.cli import app


def test_show_latest_defaults_to_latest(prov_sandbox, runner):
    res = runner.invoke(app, ["show"])
    assert res.exit_code == 0, res.output
    assert prov_sandbox.run2 in res.output


def test_show_by_tag_json(prov_sandbox, runner):
    res = runner.invoke(app, ["show", "baseline", "--format", "json"])
    assert res.exit_code == 0, res.output

    obj = json.loads(res.stdout)
    assert obj["run"]["run_id"] == prov_sandbox.run2
    assert "baseline" in obj["run"]["tags"]


def test_show_warnings_and_paths_text(prov_sandbox, runner):
    res = runner.invoke(app, ["show", "baseline2", "--warnings", "--paths"])
    assert res.exit_code == 0, res.output
    assert "Warnings" in res.output
    assert "Inputs" in res.output


def test_show_raw_json(prov_sandbox, runner):
    res = runner.invoke(app, ["show", "baseline", "--raw"])
    assert res.exit_code == 0, res.output

    obj = json.loads(res.stdout)
    assert obj["run_id"] == prov_sandbox.run2


def test_show_hashes_text(prov_sandbox, runner):
    res = runner.invoke(app, ["show", "baseline", "--paths", "--hashes"])
    assert res.exit_code == 0, res.output
    assert "Inputs" in res.output
    assert "h_in_1" in res.output  # from fixture

