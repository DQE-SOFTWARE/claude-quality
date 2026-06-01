# DQE Audit Skill — Desktop Install (Windows)
# Copies the dqe-audit skill to %USERPROFILE%\.claude\skills\
# No git required. Requires PowerShell 5+ (built into Windows 10/11).
#
# Usage (PowerShell):
#   irm https://raw.githubusercontent.com/DQE-SOFTWARE/claude-quality/main/install-desktop.ps1 | iex
# Or after manual download:
#   powershell -ExecutionPolicy Bypass -File install-desktop.ps1

$ErrorActionPreference = "Stop"

$repo    = "DQE-SOFTWARE/claude-quality"
$branch  = "main"
$zipUrl  = "https://github.com/$repo/archive/refs/heads/$branch.zip"
$tmpZip  = Join-Path $env:TEMP "dqe-quality.zip"
$tmpDir  = Join-Path $env:TEMP "dqe-quality-install"
$target  = Join-Path $env:USERPROFILE ".claude\skills\dqe-audit"

Write-Host ""
Write-Host "=== DQE Audit Skill — Desktop Install (Windows) ===" -ForegroundColor Cyan
Write-Host ""

# Download ZIP
Write-Host "Downloading from GitHub..." -NoNewline
try {
    Invoke-WebRequest -Uri $zipUrl -OutFile $tmpZip -UseBasicParsing
    Write-Host " OK" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "ERROR: Could not download from GitHub." -ForegroundColor Red
    Write-Host "  Check your internet connection and try again."
    Write-Host "  URL: $zipUrl"
    exit 1
}

# Extract ZIP
Write-Host "Extracting..." -NoNewline
if (Test-Path $tmpDir) { Remove-Item $tmpDir -Recurse -Force }
Expand-Archive -Path $tmpZip -DestinationPath $tmpDir -Force
Write-Host " OK" -ForegroundColor Green

# Locate extracted folder (GitHub adds a branch suffix: repo-main/)
$extracted = Get-ChildItem $tmpDir -Directory | Select-Object -First 1
if (-not $extracted) {
    Write-Host "ERROR: Could not find extracted folder." -ForegroundColor Red
    exit 1
}

$skillSrc = Join-Path $extracted.FullName "skills\dqe-audit"
if (-not (Test-Path $skillSrc)) {
    Write-Host "ERROR: skills\dqe-audit not found in archive." -ForegroundColor Red
    exit 1
}

# Create target and copy
Write-Host "Installing to $target..." -NoNewline
New-Item -ItemType Directory -Path $target -Force | Out-Null
Copy-Item -Path "$skillSrc\*" -Destination $target -Recurse -Force
Write-Host " OK" -ForegroundColor Green

# Cleanup
Remove-Item $tmpZip -Force
Remove-Item $tmpDir -Recurse -Force

Write-Host ""
Write-Host "Skill installed successfully." -ForegroundColor Green
Write-Host ""
Write-Host "Restart Claude Code desktop, then use:"
Write-Host "  /dqe-audit C:\path\to\file.csv" -ForegroundColor Yellow
Write-Host ""
Write-Host "Docs: https://github.com/$repo" -ForegroundColor DarkGray
Write-Host ""
