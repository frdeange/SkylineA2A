# ============================================================================
#  Demo 2 - Remote build and push of DevOps Helper image in Azure Container Registry
#
#  Reads ACR_NAME / ACR_LOGIN_SERVER / ACR_IMAGE_NAME / ACR_IMAGE_TAG from
#  ../.env. Tags image with both ACR_IMAGE_TAG (default: "latest") and a short
#  git SHA for immutable ACA revision pinning.
#
#  Prerequisites:
#    * az login completed
#    * ACR exists and caller has AcrPush permissions
# ============================================================================

[CmdletBinding()]
param(
    [string] $Tag,
    [switch] $SkipPush
)

$ErrorActionPreference = "Stop"

# --- Preflight ---
foreach ($cli in @("az", "git")) {
    if (-not (Get-Command $cli -ErrorAction SilentlyContinue)) {
        Write-Error "$cli is not on PATH. Install it before running this script."
    }
}

$AzAccount = (& az account show --query "id" -o tsv 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $AzAccount) {
    Write-Error "Not logged in to Azure. Run 'az login' first."
}

# --- Load .env from repo root ---
$EnvPath = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $EnvPath)) {
    Write-Error "Could not find .env at $EnvPath. Copy .env.example to .env and fill it in."
}

Get-Content $EnvPath | Where-Object { $_ -match '^\s*[^#].*=' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    $name = $name.Trim()
    $value = $value.Trim().Trim('"')
    if ($name) {
        Set-Item -Path ("Env:" + $name) -Value $value
    }
}

# --- Required vars ---
$AcrName      = $env:ACR_NAME
$AcrLogin     = $env:ACR_LOGIN_SERVER
$ImageName    = $env:ACR_IMAGE_NAME
$DefaultTag   = if ($env:ACR_IMAGE_TAG) { $env:ACR_IMAGE_TAG } else { "latest" }
$ImageTag     = if ($Tag) { $Tag } else { $DefaultTag }
$Subscription = $env:AZURE_SUBSCRIPTION_ID

foreach ($var in @("ACR_NAME", "ACR_LOGIN_SERVER", "ACR_IMAGE_NAME")) {
    $value = [Environment]::GetEnvironmentVariable($var)
    if (-not $value) {
        Write-Error "$var is empty in .env - fill it in before running this script."
    }
}

# az acr build enforces lowercase repository names.
$OriginalImageName = $ImageName
$ImageName = $ImageName.ToLowerInvariant()
if ($OriginalImageName -ne $ImageName) {
    Write-Host "Normalizing ACR_IMAGE_NAME to lowercase: $OriginalImageName -> $ImageName"
}

# Minimal Docker repository + tag validation (fail fast with actionable message).
$RepoPattern = '^[a-z0-9]+([._-][a-z0-9]+)*(\/[a-z0-9]+([._-][a-z0-9]+)*)*$'
if ($ImageName -notmatch $RepoPattern) {
    Write-Error "ACR_IMAGE_NAME '$ImageName' is invalid. Use lowercase Docker repository format (example: skylinea2a-maf-agent)."
}
$TagPattern = '^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$'
if ($ImageTag -notmatch $TagPattern) {
    Write-Error "Image tag '$ImageTag' is invalid. Use Docker tag format [A-Za-z0-9_.-], max 128 chars."
}

if ($Subscription) {
    Write-Host "Setting active Azure subscription to $Subscription ..."
    & az account set --subscription $Subscription | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Error "az account set failed for AZURE_SUBSCRIPTION_ID=$Subscription."
    }
}

# --- Git SHA tag ---
$GitSha = (& git -C $PSScriptRoot rev-parse --short=12 HEAD 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $GitSha) {
    $GitSha = "nogit"
}

$ImageBase    = "$AcrLogin/$ImageName"
$ImageWithTag = "${ImageBase}:${ImageTag}"
$ImageWithSha = "${ImageBase}:sha-${GitSha}"

Write-Host "======================================================================="
Write-Host "  ACR             : $AcrName ($AcrLogin)"
Write-Host "  Image           : $ImageWithTag"
Write-Host "  Also tagged     : $ImageWithSha"
Write-Host "  Build context   : $PSScriptRoot (remote build in ACR)"
Write-Host "  Push            : $([bool](-not $SkipPush))"
Write-Host "======================================================================="

# --- Remote build in ACR ---
Write-Host "`nSubmitting remote build to ACR ..."
$AcrBuildArgs = @(
    "acr", "build",
    "--registry", $AcrName,
    "--image", "$ImageName`:$ImageTag",
    "--image", "$ImageName`:sha-$GitSha",
    "--file", (Join-Path $PSScriptRoot "Dockerfile"),
    "--platform", "linux/amd64",
    "--no-logs",
    "--only-show-errors",
    "--output", "json"
)
if ($SkipPush) {
    $AcrBuildArgs += "--no-push"
}
$AcrBuildArgs += $PSScriptRoot

Write-Host "Using --no-logs to avoid Azure CLI Windows encoding issues when streaming build output."
$BuildResultRaw = & az @AcrBuildArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "az acr build failed."
}

$BuildResult = $null
try {
    if ($BuildResultRaw) { $BuildResult = $BuildResultRaw | ConvertFrom-Json }
}
catch { }

if ($BuildResult -and $BuildResult.runId) {
    Write-Host "  ACR Run ID : $($BuildResult.runId)"
    Write-Host "  See logs   : az acr task logs --registry $AcrName --run-id $($BuildResult.runId)"
}

if (-not $SkipPush) {
    Write-Host "`nRemote build completed and pushed."
    Write-Host "  Image tag : $ImageWithTag"
    Write-Host "  Pinned tag: $ImageWithSha"
}
else {
    Write-Host "`nRemote build completed (--no-push)."
}
