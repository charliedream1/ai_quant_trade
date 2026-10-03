param(
    [string]$Python = $(if ($env:PYTHON) { $env:PYTHON } else { "python" }),
    [switch]$InstallDeps,
    [switch]$Serve,
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

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
    if (-not (Test-Path "site")) {
        throw "site/ not found. Run mkdocs build first."
    }

    $patterns = @(
        "_projects",
        "egs_",
        "egs/",
        "gen_project_wrappers",
        "../snippets",
        "{% include",
        "include-markdown",
        "ai_notes"
    )

    $files = Get-ChildItem -Path "site" -Recurse -File -Include `
        *.html,*.json,*.js,*.xml,*.txt

    if (Get-Command rg -ErrorAction SilentlyContinue) {
        $rgArgs = @("-n", "-S", "-F")
        foreach ($pattern in $patterns) {
            $rgArgs += @("-e", $pattern)
        }
        $rgArgs += "site"
        & rg @rgArgs
        if ($LASTEXITCODE -eq 0) {
            throw "Forbidden legacy docs content found in site/."
        }
        if ($LASTEXITCODE -ne 1) {
            throw "rg failed while scanning site/."
        }
    } else {
        $matches = $files | Select-String -SimpleMatch -Pattern $patterns
        if ($matches) {
            $matches | ForEach-Object { Write-Host $_ }
            throw "Forbidden legacy docs content found in site/."
        }
    }

    Write-Host "[site scan] OK - no legacy project/include references found."
}

$deps = @(
    "mkdocs>=1.6",
    "mkdocs-material>=9.5",
    "mkdocs-static-i18n>=1.3",
    "mkdocs-material-extensions>=1.3",
    "pymdown-extensions>=10.7"
)

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
    Invoke-Python zz_scripts/check_docs_publish_scope.py
}

Invoke-Step "Check MkDocs config and assets" {
    Invoke-Python zz_scripts/check_docs_build.py
}

Invoke-Step "Build docs site" {
    $buildArgs = @("-m", "mkdocs", "build", "--clean")
    if ($Strict) {
        $buildArgs += "--strict"
    }
    Invoke-Python @buildArgs
}

Invoke-Step "Scan generated site" {
    Assert-NoForbiddenSiteContent
}

Write-Host ""
Write-Host "==> Build complete: site/"
Write-Host "==> Local URL after serving: http://$HostName`:$Port/ai_quant_trade/"

if ($Serve) {
    Write-Host ""
    Write-Host "==> Starting MkDocs dev server. Press Ctrl+C to stop."
    Invoke-Python -m mkdocs serve -a "$HostName`:$Port"
}
