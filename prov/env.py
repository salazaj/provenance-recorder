from __future__ import annotations

import platform
import sys
from typing import Dict


def capture_minimal_env() -> Dict[str, str]:
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
    }
