# Documentation build scripts

This directory contains local equivalents of the documentation CI checks.

Windows PowerShell:

```powershell
.\scripts\build_docs.ps1 -Python D:\ProgramFiles\anaconda3\envs\py311\python.exe
.\scripts\build_docs.ps1 -Python D:\ProgramFiles\anaconda3\envs\py311\python.exe -Serve
```

Linux/macOS:

```bash
bash scripts/build_docs.sh
bash scripts/build_docs.sh --serve
```

Common options:

- `--install-deps` / `-InstallDeps`: install MkDocs dependencies first.
- `--serve` / `-Serve`: start `mkdocs serve` after a successful build.
- `--strict` / `-Strict`: pass `--strict` to `mkdocs build`.
- `--python PATH` / `-Python PATH`: choose the Python executable.

The scripts run:

1. `zz_scripts/check_docs_publish_scope.py`
2. `zz_scripts/check_docs_build.py`
3. `mkdocs build --clean`
4. a generated-site scan to ensure old project wrappers and external docs
   references did not reappear.
