# prov/tagging.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, Tuple


class TaggingError(ValueError):
    """Base error for tag argument resolution."""


class TagAmbiguity(TaggingError):
    """Raised when the user input is ambiguous and could cause a footgun."""


class TagTwoRuns(TaggingError):
    """Raised when both args resolve to runs."""


class TagNoRun(TaggingError):
    """Raised when neither arg resolves to a run."""


_RUN_ID_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z_[A-Za-z0-9]+")


def looks_like_run_id(x: str) -> bool:
    return bool(_RUN_ID_RE.fullmatch(x.strip()))


def looks_like_ordinal(x: str) -> bool:
    x = x.strip()
    return x.isdigit() or (x.startswith("#") and x[1:].isdigit())


@dataclass(frozen=True)
class ArgInfo:
    raw: str
    is_ordinal: bool
    looks_like_run_id: bool
    has_path_sep: bool
    tag_ok: bool
    run_ok: bool
    existing_tag: bool

    @property
    def explicit_runish(self) -> bool:
        # “User clearly intended run side”
        return self.is_ordinal or self.looks_like_run_id or self.has_path_sep


def resolve_tag_args(
    a: str,
    b: str,
    *,
    existing_tags: Dict[str, str],
    tag_ok: Callable[[str], bool],
    run_ok: Callable[[str], bool],
) -> Tuple[str, str]:
    """
    Decide (run_ref, tag_name) from two positional args.

    Policy highlights:
    - Ordinals win (#N / N) to avoid surprises.
    - If one side is an existing tag and the other resolves to a run, we only
      accept it automatically when the run side is *explicit run-ish*
      (ordinal, full run id, or path). Otherwise raise TagAmbiguity.
    - Also block the specific footgun: existing tag + tag-like other arg
      (baseline t) => ambiguity, unless the other arg is explicit-run-ish.
    """

    def _info(x: str) -> ArgInfo:
        x = x.strip()
        return ArgInfo(
            raw=x,
            is_ordinal=looks_like_ordinal(x),
            looks_like_run_id=looks_like_run_id(x),
            has_path_sep=("/" in x) or ("\\" in x),
            tag_ok=tag_ok(x),
            run_ok=run_ok(x),
            existing_tag=(x in existing_tags),
        )

    A = _info(a)
    B = _info(b)

    # 1) Ordinals win
    if A.is_ordinal and not B.is_ordinal:
        return (A.raw, B.raw)
    if B.is_ordinal and not A.is_ordinal:
        return (B.raw, A.raw)

    # 2) existing-tag + run-ok => only auto-accept if run side is explicit-run-ish
    if A.existing_tag and B.run_ok:
        if B.explicit_runish:
            return (B.raw, A.raw)
        raise TagAmbiguity(_ambig_msg(existing=A.raw, other=B.raw))

    if B.existing_tag and A.run_ok:
        if A.explicit_runish:
            return (A.raw, B.raw)
        raise TagAmbiguity(_ambig_msg(existing=B.raw, other=A.raw))

    # 3) existing-tag + tag-like (baseline t) => ambiguity unless other is explicit-run-ish
    if A.existing_tag and B.tag_ok and not B.run_ok and not B.explicit_runish:
        raise TagAmbiguity(_ambig_msg(existing=A.raw, other=B.raw))

    if B.existing_tag and A.tag_ok and not A.run_ok and not A.explicit_runish:
        raise TagAmbiguity(_ambig_msg(existing=B.raw, other=A.raw))

    # 4) Exactly one side resolves to a run and the other is tag-like
    if A.run_ok and B.tag_ok and not B.run_ok:
        return (A.raw, B.raw)
    if B.run_ok and A.tag_ok and not A.run_ok:
        return (B.raw, A.raw)

    # 5) Both resolve to runs
    if A.run_ok and B.run_ok:
        raise TagTwoRuns(
            "Both arguments resolve to runs; I need a tag name and a run reference.\n\n"
            "Examples:\n"
            "  prov tag baseline #2\n"
            "  prov tag baseline 2026-02-11T16-08-36Z_27971d\n"
        )

    # 6) Neither resolves to a run
    if not A.run_ok and not B.run_ok:
        raise TagNoRun(
            "Could not resolve a run from either argument. "
            "Provide a run ref (id/tag/ordinal/path) and a tag name.\n"
            "Examples:\n"
            "  prov tag baseline #2\n"
            "  prov tag baseline 2026-02-09T14-06-45Z_ab12cd\n"
        )

    # 7) Fallback: assume a is run, b is tag
    return (A.raw, B.raw)


def _ambig_msg(*, existing: str, other: str) -> str:
    return (
        f"Ambiguous: '{existing}' is an existing tag, and '{other}' could be a tag name or a run reference.\n\n"
        "Be explicit:\n"
        f"  prov tag {existing} #<N>\n"
        f"  prov tag {existing} <run_id>\n"
        f"  prov tag {other} {existing}    # if you meant to create/update tag '{other}' instead\n"
    )

