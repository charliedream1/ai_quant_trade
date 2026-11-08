"""Run full lint/type checks and optional security regressions using project sources."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.quality_gate import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
