param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$releaseRoot = Join-Path $projectRoot "release"
$buildDir = Join-Path $releaseRoot "build"
$stageDistDir = Join-Path $releaseRoot "dist"
$specDir = Join-Path $releaseRoot "spec"
$publishDir = Join-Path $projectRoot "dist"

Set-Location $projectRoot

if ($Clean) {
    Remove-Item -LiteralPath $releaseRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $publishDir -Recurse -Force -ErrorAction SilentlyContinue
}

try {
    python -m PyInstaller --version | Out-Null
}
catch {
    throw "PyInstaller is not installed. Run 'python -m pip install -r requirements-dev.txt' and retry."
}

New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
New-Item -ItemType Directory -Path $stageDistDir -Force | Out-Null
New-Item -ItemType Directory -Path $specDir -Force | Out-Null
New-Item -ItemType Directory -Path $publishDir -Force | Out-Null

# Package the versioned GUI entrypoint (nvm_gui_versioned.py) and include versions/ folder
python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name NvMAutomationTool `
    --distpath $stageDistDir `
    --workpath $buildDir `
    --specpath $specDir `
    --add-data "versions;versions" `
    --add-data "workspace;workspace" `
    --hidden-import jinja2 `
    --hidden-import lxml.etree `
    --hidden-import yaml `
    --hidden-import openpyxl `
    nvm_gui_versioned.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed. Check the output above for the exact packaging error."
}

$stagedExe = Join-Path $stageDistDir "NvMAutomationTool.exe"
$publishedExe = Join-Path $publishDir "NvMAutomationTool.exe"

Get-ChildItem -LiteralPath $publishDir -File -ErrorAction SilentlyContinue | Remove-Item -Force
Copy-Item -LiteralPath $stagedExe -Destination $publishedExe -Force

Write-Host ""
Write-Host "Build completed."
Write-Host "Staged executable: $stagedExe"
Write-Host "Published executable: $publishedExe"
