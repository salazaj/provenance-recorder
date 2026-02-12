# tests/test_cli_diff.py
from __future__ import annotations

from prov.cli import app


def test_diff_warnings_flag_text(prov_sandbox, runner):
    # Use tags so we exercise resolution too
    res = runner.invoke(app, ["diff", "baseline2", "baseline", "--warnings"])
    assert res.exit_code == 0, res.output
    assert "Warnings" in res.output


def test_diff_accepts_nested_path_ref_text(prov_sandbox, runner):
    # Make a real nested file under run1 so Path.exists() is true
    nested = (
        prov_sandbox.prov_dir
        / "runs"
        / prov_sandbox.run1
        / "outputs"
        / "deep"
        / "result.txt"
    )
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("out\n", encoding="utf-8")

    res = runner.invoke(app, ["diff", str(nested), "baseline"])
    assert res.exit_code == 0, res.output

    # Header must reflect resolved run ids
    assert f"Diff {prov_sandbox.run1}  →  {prov_sandbox.run2}" in res.output

    # Must show run names on A/B lines
    assert "A: abs_demo" in res.output
    assert "B: t" in res.output

    # Must show tags in parentheses (from index.json in prov_sandbox)
    assert "(baseline2" in res.output  # A side
    assert "(baseline" in res.output   # B side

    # With two explicit args, we should NOT print the "Comparing:" helper line
    assert "[dim]Comparing:" not in res.output


def test_diff_does_not_print_warnings_without_flag(prov_sandbox, runner):
    res = runner.invoke(app, ["diff", "baseline2", "baseline"])
    assert res.exit_code == 0, res.output
    assert "[bold]Warnings[/bold]" not in res.output


def test_show_json_rejects_abs_paths(prov_sandbox, runner):
    res = runner.invoke(app, ["show", "baseline", "--format", "json", "--abs-paths"])
    assert res.exit_code != 0
    assert "--abs-paths" in res.output


def test_diff_json_rejects_abs_paths(prov_sandbox, runner):
    res = runner.invoke(
        app,
        ["diff", "baseline2", "baseline", "--format", "json", "--abs-paths"],
    )
    assert res.exit_code != 0
    assert "--abs-paths" in res.output

