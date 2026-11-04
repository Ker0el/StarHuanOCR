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

# COLLECT 不会清掉上一次的产物，残留的旧 onnxruntime DLL 会让 GPU 版静默退回 CPU
$Dist = Join-Path $Root "dist\StarHuanOCR"
if (Test-Path $Dist) {
    Write-Host "==> 清理旧产物 $Dist"
    try {
        Remove-Item $Dist -Recurse -Force -ErrorAction Stop
    } catch {
        Write-Host "==> 删除失败（可能有进程占用），尝试结束同名进程后重试" -ForegroundColor Yellow
        Get-Process StarHuanOCR -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-Sleep -Seconds 2
        Remove-Item $Dist -Recurse -Force -ErrorAction Stop
    }
}

Write-Host "==> PyInstaller"
& $Python -m PyInstaller `
    --noconfirm --clean `
    --distpath (Join-Path $Root "dist") `
    --workpath (Join-Path $Root "build\work") `
    (Join-Path $Root "build\StarHuanOCR.spec")

if ($Gpu) {
    $Dml = Join-Path $Root ".venv\Lib\site-packages\onnxruntime\capi\DirectML.dll"
    $Target = Join-Path $Root "dist\StarHuanOCR\_internal\onnxruntime\capi"
    if ((Test-Path $Dml) -and (Test-Path $Target)) {
        Copy-Item $Dml $Target -Force
        Write-Host "==> 已补拷 DirectML.dll"
    }
}

$Exe = Join-Path $Root "dist\StarHuanOCR\StarHuanOCR.exe"
Write-Host "==> 完成：$Exe"
