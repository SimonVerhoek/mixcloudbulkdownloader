# -*- mode: python ; coding: utf-8 -*-
import os
import platform
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from environs import Env
from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.osx import BUNDLE
from PySide6.QtCore import QCoreApplication, Qt


# Enable high DPI scaling
QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)


# Load environment file based on mandatory BUILD_ENV variable
env = Env()
build_env = os.getenv("BUILD_ENV", "prod")

if build_env == "dev":
    env_file = ".env"
elif build_env == "prod":
    env_file = ".env.prod"
else:
    raise ValueError(
        f"Invalid BUILD_ENV value: '{build_env}'. "
        "Valid values are 'dev' or 'prod'."
    )

print(f"Loading environment from: {env_file}")
env.read_env(env_file)

block_cipher = None

current_dir = os.getcwd()
root_dir = Path(current_dir)


# Dynamically import get_poetry_version.py so we can grab the project's version
module_path = Path("./scripts/get_poetry_version.py")
spec = spec_from_file_location("get_poetry_version", module_path)
poetry_version_module = module_from_spec(spec)
spec.loader.exec_module(poetry_version_module)

APP_VERSION = poetry_version_module.get_poetry_version(root_dir=root_dir)
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


# Create version file for use in production
(root_dir / "app" / "_version.py").write_text(f'__version__ = "{APP_VERSION}"\n')


# Detect architecture and set appropriate SSL library paths
if sys.platform == "darwin":
    # Configure architecture-specific SSL binaries
    if platform.machine() == 'arm64':
        # ARM64 build: explicitly use Homebrew ARM64 SSL libraries
        ssl_binaries = [
            ('/opt/homebrew/opt/openssl@3/lib/libssl.3.dylib', '.'),
            ('/opt/homebrew/opt/openssl@3/lib/libcrypto.3.dylib', '.'),
        ]
        print("🔧 ARM64 build: Using ARM64 SSL libraries from /opt/homebrew")
    else:
        # Intel build: explicitly use Homebrew Intel SSL libraries
        ssl_binaries = [
            ('/usr/local/opt/openssl@3/lib/libssl.3.dylib', '.'),
            ('/usr/local/opt/openssl@3/lib/libcrypto.3.dylib', '.'),
        ]
        print("🔧 Intel build: Using Intel SSL libraries from /usr/local")
else:
    ssl_binaries = None


a = Analysis(
    ['main.py'],
    pathex=[current_dir],
    binaries=ssl_binaries,
    datas=[
        ("app/styles/*.qss", "styles"),
        ("app/resources/ffmpeg/", "app/resources/ffmpeg"),
        ("app/_version.py", "app"),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)


pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)


if sys.platform == 'darwin':
    import ctypes
    app_bundle_path = os.path.abspath(".")
    ctypes.cdll.LoadLibrary("/System/Library/Frameworks/Cocoa.framework/Cocoa").NSApplicationLoad()

    # .env values should always be quoted, but we do not want double quoting here so strip the duplicates
    APPLE_DEVELOPER_ID = env.str("APPLE_DEVELOPER_ID").strip("'").strip('"')

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
        codesign_identity=APPLE_DEVELOPER_ID,
        entitlements_file=None,
    )

    app = BUNDLE(
        exe,
        name=f"{APP_TITLE}.app",
        icon=ICON_MACOS,
        bundle_identifier=None,
        info_plist={
            "CFBundleIdentifier": "com.simonic-software-intelligence.MixcloudBulkDownloader",
            "CFBundleName": APP_TITLE,
            "CFBundleDisplayName": APP_TITLE,
            "CFBundleVersion": APP_VERSION,
            "CFBundleShortVersionString": APP_VERSION,
            "NSHighResolutionCapable": "True",
        }
    )

if sys.platform in ['win32', 'win64', 'linux']:
    import re
    from PyInstaller.utils.win32.versioninfo import (
        VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, 
        StringStruct, VarFileInfo, VarStruct
    )
    
    def parse_version_for_windows(version_string: str) -> tuple[int, int, int, int]:
        """Parse version string to extract numeric components for Windows version resource.
        
        Args:
            version_string: Version like "2.2.0a0", "1.0.0", "3.1.2rc1"
            
        Returns:
            Tuple of 4 integers (major, minor, patch, build) for Windows FixedFileInfo
        """
        try:
            # Remove pre-release identifiers (alpha, beta, rc, dev, etc.)
            clean_version = re.sub(r'[a-zA-Z].*$', '', version_string)
            parts = clean_version.split('.')
            
            # Ensure we have at least 3 parts, pad with zeros if needed
            while len(parts) < 3:
                parts.append('0')
            
            major = int(parts[0]) if parts[0] else 0
            minor = int(parts[1]) if parts[1] else 0  
            patch = int(parts[2]) if parts[2] else 0
            build = 0  # Always 0 for build number
            
            return (major, minor, patch, build)
        except (ValueError, IndexError) as e:
            print(f"Parsing version string for Windows failed: {e}")
            raise
    
    # Create Windows version resource
    major, minor, patch, build = parse_version_for_windows(APP_VERSION)
    version_resource = VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=(major, minor, patch, build),
            prodvers=(major, minor, patch, build),
        ),
        kids=[
            StringFileInfo([StringTable(
                '040904B0',
                [
                    StringStruct('FileVersion', APP_VERSION),
                    StringStruct('ProductVersion', APP_VERSION),
                    StringStruct('ProductName', 'Mixcloud Bulk Downloader'),
                    StringStruct('FileDescription', 'Mixcloud Bulk Downloader Application'),
                ]
            )]),
            VarFileInfo([VarStruct('Translation', [1033, 1200])]),
        ]
    )
    
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
            icon=ICON_WINDOWS,
            version=version_resource
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
            icon=ICON_WINDOWS,
            version=version_resource
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
