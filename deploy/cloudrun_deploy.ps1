<#
.SYNOPSIS
  Build this repository on Cloud Build and deploy it to Cloud Run as "dmaic-planner".

.DESCRIPTION
  Runs `gcloud run deploy --source .` from the repository root, then prints the
  public URL. Do the one-time setup in deploy/README.md first. Every deploy sets
  the environment variables from scratch (--set-env-vars), so nothing is left
  over from an earlier revision.

.EXAMPLE
  .\deploy\cloudrun_deploy.ps1
.EXAMPLE
  .\deploy\cloudrun_deploy.ps1 -MinInstances 1
.EXAMPLE
  .\deploy\cloudrun_deploy.ps1 -ProjectId another-project -Region us-east1 -Model placeholder
#>
param(
    [string]$ProjectId = "dmaic-planner-ari510",
    [string]$Region = "us-central1",
    # Empty = the DEFAULT_MODEL line in app/predictor.py.
    [string]$Model = "",
    [int]$MinInstances = 0,
    [int]$MaxInstances = 2,
    [string]$Memory = "2Gi",
    [int]$Cpu = 1,
    [string]$Service = "dmaic-planner"
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "gcloud is not on PATH. Install the Google Cloud CLI and do the one-time setup in deploy/README.md."
}
if (-not $Model) {
    $match = Select-String -Path (Join-Path $repo "app/predictor.py") -Pattern '^DEFAULT_MODEL = "([^"]+)"'
    if (-not $match) { throw "Could not read the DEFAULT_MODEL line in app/predictor.py." }
    $Model = $match.Matches[0].Groups[1].Value
}

Write-Host "Deploying $Service to project $ProjectId, region $Region, DMAIC_MODEL=$Model"
Write-Host "(instances $MinInstances-$MaxInstances, $Cpu CPU, $Memory). The first build takes several minutes."
Push-Location $repo
try {
    gcloud run deploy $Service `
        --source . `
        --project $ProjectId `
        --region $Region `
        --allow-unauthenticated `
        --memory $Memory `
        --cpu $Cpu `
        --cpu-boost `
        --min-instances $MinInstances `
        --max-instances $MaxInstances `
        --session-affinity `
        --set-env-vars "DMAIC_MODEL=$Model,DMAIC_THREADS=$Cpu"
    if ($LASTEXITCODE -ne 0) { throw "gcloud run deploy failed (exit code $LASTEXITCODE)." }

    $url = gcloud run services describe $Service --project $ProjectId --region $Region --format "value(status.url)"
    Write-Host ""
    Write-Host "Live at: $url"
}
finally {
    Pop-Location
}
