# -*- mode: python ; coding: utf-8 -*-
"""Reproducible onedir build; the Inno script wraps this directory."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


project_root = Path.cwd().resolve()
datas = [
    (str(project_root / "ui"), "ui"),
    (str(project_root / "assets" / "sounds" / "wake_ack.wav"), "assets/sounds"),
    (str(project_root / "models" / "kws" / "keywords.txt"), "models/kws"),
]
binaries = []
hiddenimports = ["PySide6.QtMultimedia"]
for package in ("sherpa_onnx", "faster_whisper"):
    package_datas, package_binaries, package_imports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# The Codex desktop runtime adds unrelated ICU/MSVC DLLs to PATH on this host.
# They override Windows/Qt DLLs and make the frozen app fail at QtCore import.
# Keep only application dependencies, never Codex toolchain binaries.
a.binaries[:] = [
    entry for entry in a.binaries
    if "codex-runtimes" not in str(entry[1]).lower().replace("\\", "/")
]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Jarvis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Jarvis",
)
