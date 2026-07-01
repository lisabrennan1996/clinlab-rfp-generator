# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for clinlab-rfp-desktop.
Build: pyinstaller build.spec

For Windows colleagues: run this on a Windows machine with Python installed.
First install: pip install -r requirements.txt
Then build:    pyinstaller build.spec
The .exe will be in dist/ directory.
"""
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('ui', 'ui'),
        ('engine', 'engine'),
        ('agent.py', '.'),
    ],
    hiddenimports=[
        'liteparse',
        'fitz',
        'docx',
        'docx.table',
        'docx.text',
        'docx.oxml',
        'transformers',
        'torch',
        'sentencepiece',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RFPGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # No console window for end-users
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
