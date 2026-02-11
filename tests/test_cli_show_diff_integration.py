# tests/test_cli_show_diff_integration.py
from __future__ import annotations

import json
from typer.testing import CliRunner

from prov.cli import app


runner = CliRunner()


def test_show_latest_defaults_to_latest(prov_sandbox):
    res = runner.invoke(app, ["show"])
    assert res.exit_code == 0, res.output
    assert "2026-02-11T16-08-36Z_bbbbbb" in res.output


def test_show_by_tag_json(prov_sandbox):
    res = runner.invoke(app, ["show", "baseline", "--format", "json"])
    assert res.exit_code == 0, res.output
    obj = json.loads(res.stdout)
    assert obj["run"]["run_id"] == "2026-02-11T16-08-36Z_bbbbbb"
    assert "baseline" in obj["run"]["tags"]


def test_show_warnings_and_paths(prov_sandbox):
    res = runner.invoke(app, ["show", "baseline2", "--warnings", "--paths"])
    assert res.exit_code == 0, res.output
    assert "Warnings" in res.output
    assert "Inputs" in res.output


def test_diff_warnings_flag(prov_sandbox):
    # Use tags so we exercise resolution too
    res = runner.invoke(app, ["diff", "baseline2", "baseline", "--warnings"])
    assert res.exit_code == 0, res.output
    # should include warning text/details when flag set
    assert "Warnings" in res.output

