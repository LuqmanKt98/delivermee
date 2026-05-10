<#
.SYNOPSIS
  Create a Firebase/GCP project, link this repo, and print env vars to connect the backend to Firestore.

  Prerequisites (run locally in PowerShell):
    - npm i -g firebase-tools
    - firebase login   (must show your account in: firebase login:list)

  This script does NOT upload secrets. It cannot enable Firestore in the cloud without you
  opening the Console once (or using gcloud). See the printed URL after success.

.EXAMPLE
  .\scripts\setup_firebase_project.ps1
  .\scripts\setup_firebase_project.ps1 -ProjectId "deliverme-backend-20260419"
#>

param(
    [string]$ProjectId = "",
    [string]$DisplayName = "Deliver Me Backend"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

function Test-FirebaseCli {
    $null = Get-Command firebase -ErrorAction SilentlyContinue
    if (-not $?) {
        Write-Error "firebase CLI not found. Install: npm i -g firebase-tools"
    }
}

Test-FirebaseCli

Write-Host "Checking Firebase login..."
$loginOut = & firebase login:list 2>&1 | Out-String
if ($loginOut -match "No authorized accounts" -or $loginOut -match "run `"firebase login`"") {
    Write-Error "No Firebase CLI login. Run: firebase login   Then retry this script."
}

if (-not $ProjectId) {
    $ProjectId = "deliverme-backend-{0:yyyyMMddHHmmss}" -f (Get-Date)
}

Write-Host "Creating Firebase project: $ProjectId (display: $DisplayName) ..."
& firebase projects:create $ProjectId --display-name $DisplayName
if ($LASTEXITCODE -ne 0) {
    Write-Error "firebase projects:create failed. If the ID is taken, pass -ProjectId with a unique value."
}

Write-Host "Setting default project for this folder..."
@"
{
  "projects": {
    "default": "$ProjectId"
  }
}
"@ | Set-Content -Path (Join-Path $RepoRoot ".firebaserc") -Encoding utf8

$snippetPath = Join-Path $RepoRoot "firebase-backend.env.snippet.txt"
@"
# Paste these into your .env (or set in your shell) to use cloud Firestore with this backend.
# 1) Enable Firestore: open Firebase Console -> Build -> Firestore -> Create database (Native, pick a region).
# 2) Download a service account key: Project settings -> Service accounts -> Generate new private key.
# 3) Save the JSON locally and set GOOGLE_APPLICATION_CREDENTIALS to its full path.

USE_FIREBASE_DB=true
GCP_PROJECT=$ProjectId
GOOGLE_APPLICATION_CREDENTIALS=D:\backend-deliver-me\service_account_key.json

# Then: python app.py
"@ | Set-Content -Path $snippetPath -Encoding utf8

Write-Host ""
Write-Host "Done."
Write-Host "  .firebaserc default project -> $ProjectId"
Write-Host "  Env snippet written to: firebase-backend.env.snippet.txt"
Write-Host ""
Write-Host "Next steps (required for cloud DB):"
Write-Host "  1) Open Firestore and create the database:"
Write-Host "     https://console.firebase.google.com/project/$ProjectId/firestore"
Write-Host "  2) Download service account JSON and set GOOGLE_APPLICATION_CREDENTIALS in .env"
Write-Host "  3) Merge variables from firebase-backend.env.snippet.txt into your .env"
Write-Host ""
