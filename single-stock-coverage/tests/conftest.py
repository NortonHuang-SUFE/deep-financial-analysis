from __future__ import annotations

import os
import sys
from pathlib import Path


os.environ.setdefault("SINGLE_STOCK_COVERAGE_TEST_MODE", "1")
os.environ.setdefault("SINGLE_STOCK_COVERAGE_DISABLE_MCP", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
