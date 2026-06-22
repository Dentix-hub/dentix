#!/usr/bin/env pwsh
# =============================================================
# Dentix Local Development Starter
# Usage: .\scripts\dev\start-local.ps1
# =============================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  DENTIX — Local Development Environment" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# 1. Check Docker is running
Write-Host "`n[1/4] Checking Docker..." -ForegroundColor Yellow
try {
    docker info 2>&1 | Out-Null
    Write-Host "  ✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# 2. Check .env exists
Write-Host "[2/4] Checking .env file..." -ForegroundColor Yellow
$envFile = Join-Path $ProjectRoot ".env"
$envExample = Join-Path $ProjectRoot ".env.dev.example"

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Write-Host "  ⚠️  No .env found. Copying from .env.dev.example..." -ForegroundColor Yellow
        Copy-Item $envExample $envFile
        Write-Host "  📝 Please edit .env with your actual values before continuing." -ForegroundColor Yellow
        Write-Host "  📝 At minimum, set DATABASE_URL and ENCRYPTION_KEY." -ForegroundColor Yellow
        exit 1
    } else {
        Write-Host "  ❌ No .env or .env.dev.example found!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  ✅ .env file exists" -ForegroundColor Green
}

# 3. Security Check: Prevent using production database url
Write-Host "[3/4] Running Security Check on Database URL..." -ForegroundColor Yellow
$prodDbRef = "zfizwxdlechxomqxxnig"
$envContent = Get-Content $envFile -ErrorAction SilentlyContinue
$dbUrlLine = $envContent | Where-Object { $_ -match "^DATABASE_URL\s*=" }

if ($dbUrlLine -like "*$prodDbRef*") {
    Write-Host "`n  ❌ ERROR: DATABASE ISOLATION VIOLATION!" -ForegroundColor Red
    Write-Host "  You are trying to connect the local development environment to the PRODUCTION database ($prodDbRef)." -ForegroundColor Red
    Write-Host "  To protect production data, this script has blocked execution." -ForegroundColor Red
    Write-Host "  Please change DATABASE_URL in your .env file to a development/staging database." -ForegroundColor Red
    Write-Host ""
    exit 1
} else {
    Write-Host "  ✅ Security Check Passed: No production database URL detected." -ForegroundColor Green
}

# 4. Start services
Write-Host "`n[4/4] Starting Dentix services..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Backend API:  http://localhost:7860" -ForegroundColor Cyan
Write-Host "  Frontend Dev: Run 'cd frontend && npm run dev' separately" -ForegroundColor Cyan
Write-Host "  Redis:        localhost:6379" -ForegroundColor Cyan
Write-Host ""

Set-Location $ProjectRoot
docker compose -f docker-compose.dev.yml up --build
