# -*- mode: python ; coding: utf-8 -*-
import os
import sys

from PyInstaller.building.api import EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.osx import BUNDLE


block_cipher = None

current_dir = os.getcwd()

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
        name='Mixcloud Bulk Downloader',
        debug=False,
        strip=False,
        upx=True,
        runtime_tmpdir=None,
        console=False,
        icon='assets/logo.icns'
    )

    app = BUNDLE(
        exe,
        name='Mixcloud Bulk Downloader.app',
        icon='./assets/logo.icns',
        bundle_identifier=None,
        info_plist={
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '0.1.0'
        }
    )

if sys.platform in ['win32', 'win64', 'linux']:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        name='Mixcloud Bulk Downloader',
        debug=False,
        strip=False,
        upx=True,
        runtime_tmpdir=None,
        console=False,
        icon='assets/icon.ico'
    )
