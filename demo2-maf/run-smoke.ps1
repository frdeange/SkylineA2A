$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv-demo2\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Error "Demo 2 venv not found. Run 'demo2-maf\run-local.ps1' first to bootstrap it."
    exit 1
}

# Use the venv's python directly — avoids depending on whether the
# caller activated the venv in this shell.
& $VenvPython (Join-Path $ScriptDir "smoke_test.py")
