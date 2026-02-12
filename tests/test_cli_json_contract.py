# tests/test_cli_json_contract.py
from __future__ import annotations

import json

from prov.cli import app


def test_show_json_minimal_contract(prov_sandbox, runner):
    res = runner.invoke(app, ["show", "baseline", "--format", "json"])
    assert res.exit_code == 0, res.output

    obj = json.loads(res.stdout)
    assert set(obj.keys()) == {"run", "counts", "environment", "git"}
    assert "paths" not in obj
    assert "warnings" not in obj


def test_diff_json_minimal_contract(prov_sandbox, runner):
    res = runner.invoke(app, ["diff", "baseline2", "baseline", "--format", "json"])
    assert res.exit_code == 0, res.output

    obj = json.loads(res.stdout)
    assert set(obj.keys()) == {"a", "b", "summary", "params", "environment", "git"}
    assert "inputs" not in obj
    assert "outputs" not in obj
    assert "warnings" not in obj

