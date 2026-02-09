from __future__ import annotations

import secrets
from datetime import datetime, timezone


def new_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    suffix = secrets.token_hex(3)  # 6 hex chars
    return f"{ts}_{suffix}"
