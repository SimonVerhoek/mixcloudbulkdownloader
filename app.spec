# -*- mode: python ; coding: utf-8 -*-
import os
import sys

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.osx import BUNDLE


block_cipher = None
current_dir = os.getcwd()

APP_VERSION = '0.1.4'
APP_TITLE = 'Mixcloud Bulk Downloader'
DEBUG = False
CONSOLE = False
ICON_WINDOWS = 'assets/logo.ico'
ICON_MACOS = 'assets/logo.icns'
WINDOWS_EXE_ONLY = False

a = Analysis(
    ['main.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        name=APP_TITLE,
        debug=DEBUG,
        strip=False,
        upx=True,
        runtime_tmpdir=None,
        console=CONSOLE,
        icon=ICON_MACOS
    )

    app = BUNDLE(
        exe,
        name=APP_TITLE,
        icon=ICON_MACOS,
        bundle_identifier=None,
        info_plist={
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': APP_VERSION
        }
    )

if sys.platform in ['win32', 'win64', 'linux']:
    if WINDOWS_EXE_ONLY:
        # only create .exe file
        exe = EXE(
            pyz,
            a.scripts,
            a.binaries,
            a.zipfiles,
            a.datas,
            name=APP_TITLE,
            debug=DEBUG,
            strip=False,
            upx=True,
            runtime_tmpdir=None,
            console=CONSOLE,
            icon=ICON_WINDOWS
        )

    else:
        # create dir with all files (this will be zipped)
        exe = EXE(
            pyz,
            a.scripts,
            [],
            exclude_binaries=True,
            name=APP_TITLE,
            debug=DEBUG,
            bootloader_ignore_signals=False,
            strip=False,
            upx=True,
            console=CONSOLE,
            icon=ICON_WINDOWS
        )
        coll = COLLECT(
            exe,
            a.binaries,
            a.zipfiles,
            a.datas,
            strip=False,
            upx=True,
            upx_exclude=[],
            name=APP_TITLE
        )
