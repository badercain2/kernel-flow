# -*- mode: python ; coding: utf-8 -*-
# Configuracion de PyInstaller para generar el ejecutable de KernelFlow.
# Uso: python3 empaquetar.py   (o: python3 -m PyInstaller kernelflow.spec)
#
# La carpeta data/ (CSV y logo) NO se mete dentro del ejecutable: se copia al
# lado para que el usuario pueda ver y agregar sus propios lotes.

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["unittest", "pydoc", "test"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="KernelFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
