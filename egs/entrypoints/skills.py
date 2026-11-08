"""Run project research Skills locally, or explicitly use an existing remote API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agent.skill_runner.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
