"""Support python -m src.cli without installing the project."""

from .app import main

raise SystemExit(main())
