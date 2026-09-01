# 一键质量检查：前端 lint + typecheck + build，后端 pytest（含覆盖率）
# 用法: powershell -ExecutionPolicy Bypass -File quality-check.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ''
Write-Host '════════════════════════════════════════════'
Write-Host ' 徒步助手 · 一键质量检查'
Write-Host '════════════════════════════════════════════'

Write-Host ''
Write-Host '── [1/2] 前端: lint + typecheck + build ──'
Push-Location (Join-Path $root 'frontend')
try {
    npm run lint
    if ($LASTEXITCODE -ne 0) { throw "oxlint 失败" }
    npx tsc -b --noEmit
    if ($LASTEXITCODE -ne 0) { throw "tsc 失败" }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "vite build 失败" }
    Write-Host '✅ 前端通过 (lint + typecheck + build)'
} finally {
    Pop-Location
}

Write-Host ''
Write-Host '── [2/2] 后端: pytest (覆盖率) ──'
Push-Location (Join-Path $root 'backend')
try {
    python -m pytest --cov=app --cov-report=term -q
    if ($LASTEXITCODE -ne 0) { throw "pytest 失败" }
} finally {
    Pop-Location
}

Write-Host ''
Write-Host '🎉 全部质量检查通过'
