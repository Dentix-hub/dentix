# Smart Clinic - Git-based Deployment Script
param([string]$Target)
$ErrorActionPreference = "Stop"

if (-not $Target) {
    Write-Host "Usage: .\deploy_git.ps1 -Target [staging|production]"
    $Target = Read-Host "Enter Target (staging/production)"
}

$REPO_URL = if ($Target -eq "production") { "https://huggingface.co/spaces/SmartClinic/smart-clinic-v2" } else { "https://huggingface.co/spaces/SmartClinic/smart-clinic-staging" }
$CLONE_DIR = ".hf-deploy-$Target"
$SOURCE_DIR = $PSScriptRoot

Write-Host "Deploying to $Target ($REPO_URL)..." -ForegroundColor Cyan

if (Test-Path $CLONE_DIR) {
    cd $CLONE_DIR
    git pull --rebase
    cd ..
} else {
    git clone $REPO_URL $CLONE_DIR
}

Write-Host "Copying files..."
if (Test-Path "$CLONE_DIR\backend") { Remove-Item -Recurse -Force "$CLONE_DIR\backend" }
if (Test-Path "$CLONE_DIR\frontend") { Remove-Item -Recurse -Force "$CLONE_DIR\frontend" }

robocopy "$SOURCE_DIR\backend" "$CLONE_DIR\backend" /E /XD __pycache__ venv .venv uploads /XF *.pyc *.db *.sqlite *.log .env /NFL /NDL /NJH /NJS
robocopy "$SOURCE_DIR\frontend" "$CLONE_DIR\frontend" /E /XD node_modules dist .vite /XF *.log .env* /NFL /NDL /NJH /NJS
Copy-Item "$SOURCE_DIR\Dockerfile" "$CLONE_DIR\" -Force
Copy-Item "$SOURCE_DIR\requirements.txt" "$CLONE_DIR\" -Force

Write-Host "Pushing..."
cd $CLONE_DIR
git add -A
git commit -m "Deploy $(Get-Date)"
git push
cd ..

Write-Host "Done." -ForegroundColor Green
