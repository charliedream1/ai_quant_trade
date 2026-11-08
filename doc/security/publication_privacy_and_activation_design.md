# Publication privacy and activation script literals

## Purpose and scope

The application must not distribute local Codex, TRAE, or WorkBuddy memories,
sessions, authentication state, or task transcripts. Git publication, Docker
build contexts, image layers, and documentation publishing are separate
boundaries; each needs an explicit policy. Shared project skills remain source
artifacts rather than personal memory.

## Packaging boundaries

The Docker context denies inputs by default and permits only the application,
example configuration, public documentation, document helper scripts, entry
point, dependency manifest, license, and runtime metadata. Additional exclusion
rules take precedence for secrets, private local configurations, raw audit data,
task documents, caches, environments, and agent state at any depth. The final
image uses explicit copy sources instead of copying the complete checkout.

Git ignores local Codex and WorkBuddy state while keeping their shared skills
eligible for review. TRAE state remains private. These patterns also apply
below nested project directories, after existing broad source inclusion rules.
The rules do not delete files or remove existing tracked content. A separate
tracked-file audit verifies that no local tool state has already been indexed.

Both MkDocs configurations explicitly exclude Codex, TRAE, and WorkBuddy
directories. Publication tests create synthetic memory markers and verify that
generated HTML and search indexes do not contain them. Tests never import a
developer's actual memory or credentials.

## Activation file serialization

Paths supplied to the bootstrap are data, including spaces, apostrophes, dollar
signs, backticks, and shell expression syntax. PowerShell activation uses literal
strings with escaped apostrophes. POSIX activation uses standard shell literal
quoting and Linux line endings. The PowerShell file has a UTF-8 BOM so that
Windows PowerShell can read non-ASCII paths correctly.

The informational runtime environment file uses quoted and escaped values.
Consumers reading it as dotenv data must disable interpolation when literal
paths are required. It contains path settings only, never copied provider keys.

## Runtime directories

Report stores accept the configured data root so that Docker volumes and E-drive
storage remain usable. Explicit insight roots retain their existing project
boundary and may additionally use the configured data root; sibling directories
outside those boundaries are rejected. Pipeline artifacts remain contained in
the configured data root. The standalone publication sample resolves its
inherited configuration and documentation source from its categorized location.

## Historical workstation paths

The existing working-tree provenance text already removes the workstation path
from the GenericAgent runtime. It must remain part of any future reviewed source
commit. Neither ignoring files nor making a new commit removes text from older
Git objects. History rewriting and remote replacement require a separately
approved migration; this change does not rewrite historical commits.

## Verification

Coverage includes Git ignore checks in isolated repositories, explicit Docker
copy contracts, context inclusion/exclusion cases, real local PowerShell and
POSIX activation, dotenv round trips, and actual MkDocs fixture builds. An
isolated runtime assembled from allowed context files verifies that application
imports and service startup still work. Docker image execution requires a
running daemon and is reported separately from static packaging checks.
