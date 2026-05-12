$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

$VenvPath = Join-Path $RepoRoot ".venv-demo1"
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

    Write-Host "Installing demo1-foundry dependencies (this can take a minute) ..." -ForegroundColor Yellow
    python -m pip install --pre -r $Requirements
    if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed."; exit $LASTEXITCODE }
} else {
    . $Activate
}

function Step {
    param([string]$Title, [string]$Script)
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan
    python (Join-Path $ScriptDir $Script)
    if ($LASTEXITCODE -ne 0) {
        Write-Error "$Script failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

Step "Step 1/3 - create_agent.py"     "create_agent.py"
Step "Step 2/3 - enable_a2a.py"       "enable_a2a.py"
Step "Step 3/3 - test_a2a_client.py"  "test_a2a_client.py"

Write-Host ""
Write-Host "Demo 1 end-to-end completed." -ForegroundColor Green
Write-Host "Run 'python demo1-foundry\delete_agent.py' to remove the agent when you are done." -ForegroundColor Yellow

