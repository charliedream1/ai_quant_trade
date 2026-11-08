# Documentation build scripts

`setup_project.py` is the fresh-clone bootstrap. It supports both `pip` and
`uv`, creates an E-drive runtime when available, emits activation scripts, and
can install the locked `.tools/zvec-grep` package with `--install-zvec`. Use
`setup_project.ps1` or `setup_project.sh` as platform wrappers. All generated
files are outside the repository and can be removed independently.

Activation files treat configured paths as literal data, including apostrophes,
dollar signs, backticks, spaces, and non-ASCII characters. Source `activate.ps1`
in PowerShell or `activate.sh` in a POSIX shell. The generated `runtime.env`
contains quoted path metadata only; dotenv consumers should use
`interpolate=False` to preserve literal dollar signs. No agent memory, login
state, or provider credential is copied into these files.

This directory contains local equivalents of the documentation CI checks.

Windows PowerShell:

```powershell
.\scripts\build_docs.ps1
.\scripts\build_docs.ps1 -Serve
.\scripts\build_docs.ps1 -Python python
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

1. `scripts/docs/check_docs_publish_scope.py`
2. `scripts/docs/check_docs_build.py`
3. `mkdocs build --clean`
4. a generated-site scan to ensure old project wrappers and external docs
   references did not reappear.

The MkDocs site is bilingual. Chinese pages use the normal `.md` filename and
English pages use the `.en.md` suffix. Every file referenced by `mkdocs.yml`
`nav` must have a matching English translation.
