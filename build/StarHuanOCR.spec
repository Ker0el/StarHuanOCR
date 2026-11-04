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

datas += [
    (os.path.join(ROOT, "models"), "models"),
    (os.path.join(ROOT, "assets", "icon.ico"), "assets"),
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
