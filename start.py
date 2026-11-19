"""Source checkout entry point; service startup also ships in the Python package."""

from src.startup import _ensure_port_available as _ensure_port_available
from src.startup import build_parser as build_parser
from src.startup import main as _service_main


def main(argv=None):
    """Keep source-launcher instrumentation compatible with the installed service."""
    return _service_main(argv, port_check=_ensure_port_available)


if __name__ == "__main__":
    main()
