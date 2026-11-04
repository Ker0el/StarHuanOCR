param(
    [switch]$Gpu
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "找不到虚拟环境：$Python"
}

# 两个包共用 onnxruntime 目录，必须先卸载另一个再装，否则会留下残缺安装
if ($Gpu) {
    Write-Host "==> 切换到 onnxruntime-directml（GPU 版）"
    & $Python -m pip uninstall -y --quiet onnxruntime
    & $Python -m pip install --quiet --upgrade onnxruntime-directml
} else {
    Write-Host "==> 切换到 onnxruntime（CPU 版）"
    & $Python -m pip uninstall -y --quiet onnxruntime-directml
    & $Python -m pip install --quiet --upgrade onnxruntime==1.31.1
}

Write-Host "==> PyInstaller"
& $Python -m PyInstaller `
    --noconfirm --clean `
    --distpath (Join-Path $Root "dist") `
    --workpath (Join-Path $Root "build\work") `
    (Join-Path $Root "build\StarHuanOCR.spec")

Write-Host "==> 完成：$(Join-Path $Root 'dist\StarHuanOCR\StarHuanOCR.exe')"
