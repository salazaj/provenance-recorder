# tests/test_runstore_path_refs.py
from __future__ import annotations

from pathlib import Path

from prov.cli import app
from prov.runstore import load_run, run_id_from_ref


def test_run_id_from_ref_nested_path(prov_sandbox):
    # Create a real file under a run dir (nested)
    nested = (
        prov_sandbox.prov_dir
        / "runs"
        / prov_sandbox.run2
        / "outputs"
        / "deep"
        / "file.txt"
    )
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("hello\n", encoding="utf-8")

    rid = run_id_from_ref(prov_sandbox.prov_dir, str(nested))
    assert rid == prov_sandbox.run2


def test_load_run_accepts_nested_path(prov_sandbox):
    nested = (
        prov_sandbox.prov_dir
        / "runs"
        / prov_sandbox.run1
        / "inputs"
        / "whatever"
        / "in.txt"
    )
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("data\n", encoding="utf-8")

    r = load_run(prov_sandbox.prov_dir, str(nested))
    assert r.run_id == prov_sandbox.run1
    assert r.name == "abs_demo"


def test_cli_show_accepts_nested_path(runner, prov_sandbox):
    nested = (
        prov_sandbox.prov_dir
        / "runs"
        / prov_sandbox.run2
        / "outputs"
        / "result.txt"
    )
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("out\n", encoding="utf-8")

    res = runner.invoke(app, ["show", str(nested)])
    assert res.exit_code == 0, res.output
    assert prov_sandbox.run2 in res.output

