param(
    [string]$Python = $(if ($env:PYTHON) { $env:PYTHON } else { "python" }),
    [switch]$InstallDeps,
    [switch]$Serve,
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Strict,
    [string]$SiteDir = "site"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot
$ResolvedSiteDir = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $SiteDir))
$RepoPrefix = ([string]$RepoRoot).TrimEnd([char[]]"\/") + [System.IO.Path]::DirectorySeparatorChar
if (-not $ResolvedSiteDir.StartsWith($RepoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "SiteDir must be a generated directory inside the repository."
}

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host ""
    Write-Host "==> $Name"
    & $Action
}

function Invoke-Python {
    & $Python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Python $args"
    }
}

function Assert-NoForbiddenSiteContent {
    if (-not (Test-Path -LiteralPath $SiteDir -PathType Container)) {
        throw "$SiteDir not found. Run mkdocs build first."
    }

    $patterns = @(
        "_projects",
        "gen_project_wrappers",
        "../snippets",
        "{% include",
        "include-markdown",
        "ai_notes"
    )

    $files = Get-ChildItem -Path $SiteDir -Recurse -File -Include `
        *.html,*.json,*.js,*.xml,*.txt

    if (Get-Command rg -ErrorAction SilentlyContinue) {
        $rgArgs = @("-n", "-S", "-F")
        foreach ($pattern in $patterns) {
            $rgArgs += @("-e", $pattern)
        }
        $rgArgs += @("--", $SiteDir)
        & rg @rgArgs
        if ($LASTEXITCODE -eq 0) {
            throw "Forbidden legacy docs content found in $SiteDir."
        }
        if ($LASTEXITCODE -ne 1) {
            throw "rg failed while scanning $SiteDir."
        }
    } else {
        $matches = $files | Select-String -SimpleMatch -Pattern $patterns
        if ($matches) {
            $matches | ForEach-Object { Write-Host $_ }
            throw "Forbidden legacy docs content found in $SiteDir."
        }
    }

    Write-Host "[site scan] OK - no legacy project/include references found."
}

$deps = @("-r", "requirements-docs.txt")

Invoke-Step "Python version" {
    Invoke-Python --version
}

if ($InstallDeps) {
    Invoke-Step "Install MkDocs dependencies" {
        Invoke-Python -m pip install --no-cache-dir @deps
    }
}

Invoke-Step "MkDocs version" {
    Invoke-Python -m mkdocs --version
}

Invoke-Step "Check docs publish scope" {
    Invoke-Python scripts/docs/check_docs_publish_scope.py
}

Invoke-Step "Check MkDocs config and assets" {
    Invoke-Python scripts/docs/check_docs_build.py
}

Invoke-Step "Build docs site" {
    $buildArgs = @("-m", "mkdocs", "build", "--clean", "--site-dir", $SiteDir)
    if ($Strict) {
        $buildArgs += "--strict"
    }
    Invoke-Python @buildArgs
}

Invoke-Step "Scan generated site" {
    Assert-NoForbiddenSiteContent
}

Write-Host ""
Write-Host "==> Build complete: $SiteDir"
Write-Host "==> Local URL after serving: http://$HostName`:$Port/ai_quant_trade/"

if ($Serve) {
    Write-Host ""
    Write-Host "==> Starting MkDocs dev server. Press Ctrl+C to stop."
    Invoke-Python -m mkdocs serve -a "$HostName`:$Port"
}
