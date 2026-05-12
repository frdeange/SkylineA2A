$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

$VenvPath = Join-Path $RepoRoot ".venv-demo2"
$Activate = Join-Path $VenvPath "Scripts\Activate.ps1"
$Requirements = Join-Path $ScriptDir "requirements.txt"

# The agent-framework-a2a package is installed from a git clone of
# microsoft/agent-framework, which contains C# sample paths over 260 chars
# (e.g. dotnet/samples/02-agents/AgentWithOpenAI/...). On Windows, git's
# default checkout fails with "Filename too long" unless core.longpaths is
# enabled. Enable it globally (user-level, no admin needed) before pip install.
$longPaths = (& git config --global --get core.longpaths) 2>$null
if ($longPaths -ne "true") {
    Write-Host "Enabling git core.longpaths=true globally (Windows MAX_PATH workaround) ..." -ForegroundColor Yellow
    git config --global core.longpaths true
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to set git core.longpaths."; exit $LASTEXITCODE }
}

if (-not (Test-Path $Activate)) {
    Write-Host "Creating virtual environment at $VenvPath ..." -ForegroundColor Yellow
    python -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create venv."; exit $LASTEXITCODE }

    . $Activate
    Write-Host "Upgrading pip ..." -ForegroundColor Yellow
    python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { Write-Error "pip upgrade failed."; exit $LASTEXITCODE }
} else {
    . $Activate
}

# Always sync dependencies — keeps the venv in line with requirements.txt
# without forcing a full rebuild. pip is a no-op when everything is already
# satisfied, so this is cheap on warm runs and self-healing when deps drift.
Write-Host "Syncing demo2-maf dependencies ..." -ForegroundColor Yellow
python -m pip install --pre -r $Requirements
if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed."; exit $LASTEXITCODE }

python (Join-Path $ScriptDir "mafagent.py")

