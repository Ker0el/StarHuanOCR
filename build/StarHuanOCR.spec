# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：onedir，模型与图标随包。"""
import os

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = []
binaries = []
hiddenimports = []

for package in ("rapidocr", "onnxruntime", "qfluentwidgets"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# rapidocr 的 wheel 里打包了所有语言的模型缓存，我们只用 models/ 下的 4 个，剔除
datas = [
    item for item in datas
    if "rapidocr" + os.sep + "models" not in item[0].replace("/", os.sep)
]

# PyInstaller 的 onnxruntime 钩子不会带 DirectML.dll，GPU 版必须手动收集
try:
    import onnxruntime

    capi = os.path.join(os.path.dirname(onnxruntime.__file__), "capi")
    for dll_name in ("DirectML.dll", "onnxruntime_providers_shared.dll"):
        dll_path = os.path.join(capi, dll_name)
        if os.path.exists(dll_path):
            binaries.append((dll_path, "onnxruntime/capi"))
except ImportError:
    pass

datas += [
    (os.path.join(ROOT, "models"), "models"),
    (os.path.join(ROOT, "assets", "icon.ico"), "assets"),
    (os.path.join(ROOT, "assets", "fonts"), "assets/fonts"),
    (os.path.join(ROOT, "assets", "reward.jpg"), "assets"),
]

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["PyQt5", "matplotlib", "scipy", "pytest", "tkinter", "IPython", "notebook"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="StarHuanOCR",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(ROOT, "assets", "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="StarHuanOCR",
)
