"""Run the source-based AIQuant command-line client."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.cli.app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
