# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import tomllib
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from environs import Env
from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.osx import BUNDLE
from PyInstaller.utils.hooks import collect_submodules


# load .env file
env = Env()
env.read_env()

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
    noarchive=False,
)

# Dynamically import get_poetry_version.py so we can grab the project's version
module_path = Path("/src/scripts/get_poetry_version.py")
spec = spec_from_file_location("get_poetry_version", module_path)
poetry_version_module = module_from_spec(spec)
spec.loader.exec_module(poetry_version_module)

APP_VERSION = poetry_version_module.get_poetry_version(root_dir=Path(current_dir))
APP_TITLE = 'Mixcloud Bulk Downloader'
DEBUG = env.bool("DEBUG", False)
CONSOLE = env.bool("CONSOLE", False)
ICON_WINDOWS = 'assets/logo.ico'
ICON_MACOS = 'assets/logo.icns'
WINDOWS_EXE_ONLY = False

print()
print(f"{sys.platform = }")
print(f"{APP_VERSION = }")
print(f"{DEBUG = }")
print(f"{CONSOLE = }")
print()

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=APP_TITLE,
        debug=DEBUG,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=CONSOLE,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

    app = BUNDLE(
        exe,
        name=f"{APP_TITLE}.app",
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
