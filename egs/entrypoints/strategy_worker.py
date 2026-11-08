"""Start a reviewed strategy worker using this project's source tree."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.strategy.worker_main import main  # noqa: E402

if __name__ == "__main__":
    main()
