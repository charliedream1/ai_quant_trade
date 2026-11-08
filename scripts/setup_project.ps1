param(
    [ValidateSet("pip", "uv")][string]$Manager = "uv",
    [ValidateSet("base", "models", "llm", "channels", "observability", "docs", "development")][string]$Profile = "base",
    [string]$Python = "python",
    [string]$RuntimeRoot = "",
    [switch]$InstallZvec,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script = Join-Path $root "scripts/setup_project.py"
$argsList = @($script, "--manager", $Manager, "--profile", $Profile, "--python", $Python)
if ($RuntimeRoot) { $argsList += @("--runtime-root", $RuntimeRoot) }
if ($InstallZvec) { $argsList += "--install-zvec" }
if ($DryRun) { $argsList += "--dry-run" }
& $Python @argsList
if ($LASTEXITCODE -ne 0) { throw "Project bootstrap failed with exit code $LASTEXITCODE" }
