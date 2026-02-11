# tests/test_tagging.py
import pytest

from prov.tagging import (
    resolve_tag_args,
    TagAmbiguity,
    TagTwoRuns,
    TagNoRun,
)

RUN_A = "2026-02-11T16-08-36Z_27971d"
RUN_B = "2026-02-09T17-15-05Z_c66303"


def _mk_run_ok(runlike: set[str]):
    return lambda x: x in runlike


def _mk_tag_ok(taglike: set[str]):
    return lambda x: x in taglike


def _resolve_case(
    a: str,
    b: str,
    *,
    existing_tags: dict[str, str] | None = None,
    runlike: set[str] | None = None,
    taglike: set[str] | None = None,
):
    existing_tags = existing_tags or {}
    runlike = runlike or set()
    taglike = taglike or set()
    return resolve_tag_args(
        a,
        b,
        existing_tags=existing_tags,
        run_ok=_mk_run_ok(runlike),
        tag_ok=_mk_tag_ok(taglike),
    )


# --- sanity / named tests (keep a couple) --------------------------------------

def test_ordinals_win():
    run_ref, tag_name = _resolve_case(
        "#2",
        "baseline",
        runlike=set(),                 # doesn't matter
        taglike={"baseline"},
    )
    assert (run_ref, tag_name) == ("#2", "baseline")


def test_existing_tag_footgun_ambiguous_when_other_is_taglike():
    with pytest.raises(TagAmbiguity):
        _resolve_case(
            "baseline",
            "t",
            existing_tags={"baseline": RUN_A},
            runlike={"t"},              # "t" resolves to a run...
            taglike={"t"},              # ...but is also tag-like => ambiguity unless explicit run-ish
        )


# --- truth table ----------------------------------------------------------------
#
# Notes:
# - "explicit run-ish" is defined by tagging.py: ordinal, full run id, or path.
# - For the footgun rule we intentionally set things like "t" to be BOTH run_ok and tag_ok.
# - For run-id strings (RUN_A/RUN_B) we also mark tag_ok True because your tag regex allows them;
#   the algorithm must still do the right thing.

TRUTH_TABLE = [
    # 1) ordinals win
    dict(
        name="ordinal_as_run_side",
        a="#2",
        b="baseline",
        existing_tags={},
        runlike=set(),             # doesn't matter
        taglike={"baseline"},
        expect=("#2", "baseline"),
    ),
    dict(
        name="ordinal_on_right",
        a="baseline",
        b="2",
        existing_tags={},
        runlike=set(),
        taglike={"baseline"},
        expect=("2", "baseline"),
    ),

    # 2) existing-tag footgun behavior
    dict(
        name="existing_tag_plus_taglike_runref_is_ambiguous",
        a="baseline",
        b="t",
        existing_tags={"baseline": RUN_A},
        runlike={"t"},
        taglike={"t"},
        raises=TagAmbiguity,
    ),
    dict(
        name="existing_tag_plus_full_run_id_is_allowed",
        a="baseline",
        b=RUN_A,
        existing_tags={"baseline": RUN_B},
        runlike={RUN_A},
        taglike={RUN_A, "baseline"},  # run ids are tag-valid too
        expect=(RUN_A, "baseline"),
    ),
    dict(
        name="existing_tag_plus_path_is_allowed",
        a="baseline",
        b=".prov/runs/x/run.json",
        existing_tags={"baseline": RUN_B},
        runlike={".prov/runs/x/run.json"},
        taglike={".prov/runs/x/run.json", "baseline"},
        expect=(".prov/runs/x/run.json", "baseline"),
    ),

    # 3) one run-like + one tag-like (no existing-tag special case)
    dict(
        name="run_left_tag_right",
        a=RUN_A,
        b="baseline",
        existing_tags={},
        runlike={RUN_A},
        taglike={RUN_A, "baseline"},
        expect=(RUN_A, "baseline"),
    ),
    dict(
        name="run_right_tag_left",
        a="baseline",
        b=RUN_A,
        existing_tags={},
        runlike={RUN_A},
        taglike={RUN_A, "baseline"},
        expect=(RUN_A, "baseline"),
    ),

    # 4) both sides resolve to runs
    dict(
        name="two_runs_error",
        a=RUN_A,
        b=RUN_B,
        existing_tags={},
        runlike={RUN_A, RUN_B},
        taglike={RUN_A, RUN_B},
        raises=TagTwoRuns,
    ),

    # 5) neither resolves to a run
    dict(
        name="no_run_error",
        a="baseline",
        b="t",
        existing_tags={},
        runlike=set(),
        taglike={"baseline", "t"},
        raises=TagNoRun,
    ),

    # 6) fallback behavior (rare)
    # Here we simulate: left is run_ok, right is BOTH run_ok and tag_ok but NOT run_id/path/ordinal,
    # and right isn't an existing tag. This doesn’t hit the footgun rule and ends up in "both resolve to runs"
    # if run_ok is True for both; so to force fallback we make right run_ok True but left tag_ok False and right tag_ok False.
    dict(
        name="fallback_a_as_run_b_as_tag",
        a="weird-run-ref",
        b="weird-tag",
        existing_tags={},
        runlike={"weird-run-ref"},   # only a resolves
        taglike={"weird-tag"},       # only b is tag-valid
        expect=("weird-run-ref", "weird-tag"),
    ),
]


@pytest.mark.parametrize("case", TRUTH_TABLE, ids=[c["name"] for c in TRUTH_TABLE])
def test_truth_table(case):
    a = case["a"]
    b = case["b"]
    existing_tags = case.get("existing_tags", {})
    runlike = case.get("runlike", set())
    taglike = case.get("taglike", set())

    if "raises" in case:
        with pytest.raises(case["raises"]):
            _resolve_case(
                a,
                b,
                existing_tags=existing_tags,
                runlike=runlike,
                taglike=taglike,
            )
    else:
        expect = case["expect"]
        got = _resolve_case(
            a,
            b,
            existing_tags=existing_tags,
            runlike=runlike,
            taglike=taglike,
        )
        assert got == expect

