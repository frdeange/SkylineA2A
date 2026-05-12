$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

$VenvPath = Join-Path $RepoRoot ".venv-demo2"
$Activate = Join-Path $VenvPath "Scripts\Activate.ps1"
$Requirements = Join-Path $ScriptDir "requirements.txt"

if (-not (Test-Path $Activate)) {
    Write-Host "Creating virtual environment at $VenvPath ..." -ForegroundColor Yellow
    python -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create venv."; exit $LASTEXITCODE }

    . $Activate
    Write-Host "Upgrading pip ..." -ForegroundColor Yellow
    python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { Write-Error "pip upgrade failed."; exit $LASTEXITCODE }

    Write-Host "Installing demo2-maf dependencies (this can take a minute) ..." -ForegroundColor Yellow
    python -m pip install --pre -r $Requirements
    if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed."; exit $LASTEXITCODE }
} else {
    . $Activate
}

python (Join-Path $ScriptDir "mafagent.py")

