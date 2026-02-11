# prov/resolve.py
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from .indexdb import load_index


def resolve_user_ref(prov_dir: Path, ref: str) -> str:
    """
    Turn user input into a run_id or an existing path.

    Supports:
      - existing path
      - tag
      - ordinal "#N" (1-based; oldest=1)
      - bare integer "N" (treated as ordinal; 1-based; oldest=1)
      - run_id (as-is)
    """
    ref = ref.strip()
    p = Path(ref)
    if p.exists():
        return ref

    idx = load_index(prov_dir)

    # tag
    if ref in idx.tags:
        return idx.tags[ref]

    # ordinal forms
    if ref.startswith("#") and ref[1:].isdigit():
        return idx.resolve_ordinal(int(ref[1:]))

    if ref.isdigit():
        return idx.resolve_ordinal(int(ref))

    # assume run_id
    return ref


def resolve_run_pair(
    prov_dir: Path, run_a: Optional[str], run_b: Optional[str]
) -> Tuple[str, str]:
    """
    Resolve the intended (A, B) run refs given 0/1/2 user-supplied args.

    Behavior:
      - no args: last two (by timestamp)
      - one arg X: X vs latest (unless X resolves to latest => previous vs latest)
      - two args: resolved(A) vs resolved(B)
    """
    idx = load_index(prov_dir)
    ordered = idx.ordered_run_ids()

    if run_a is None and run_b is None:
        if len(ordered) < 2:
            raise RuntimeError(
                "Need at least two recorded runs to diff. Run `prov record` first."
            )
        return (ordered[-2], ordered[-1])

    if run_a is not None and run_b is None:
        if len(ordered) < 2:
            raise RuntimeError(
                "Need at least two recorded runs to diff. Run `prov record` first."
            )
        latest = ordered[-1]
        prev = ordered[-2]
        a_resolved = resolve_user_ref(prov_dir, run_a)
        a_id = Path(a_resolved).name if Path(a_resolved).exists() else a_resolved
        if a_id == latest:
            return (prev, latest)
        return (a_resolved, latest)

    assert run_a is not None and run_b is not None
    return (resolve_user_ref(prov_dir, run_a), resolve_user_ref(prov_dir, run_b))
