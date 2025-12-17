# -*- mode: python ; coding: utf-8 -*-
import os
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

# Detect Intel CI build environment
IS_INTEL_CI = os.getenv("GITHUB_ACTIONS") == "true" and build_env == "prod"

# For Intel builds in CI, always enable debug mode to capture detailed bootloader output
if IS_INTEL_CI:
    print("GitHub Actions Intel build detected - enabling debug mode for detailed output")
    DEBUG = True
    CONSOLE = True
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


# Prepare binaries and hidden imports for Intel CI builds
intel_binaries = []
intel_hiddenimports = []

if IS_INTEL_CI:
    print("Configuring Intel CI build with enhanced Python bundling...")
    
    # Add explicit Python runtime dependencies for Intel builds
    intel_hiddenimports.extend([
        'pkg_resources.py2_warn',
        'pkg_resources.markers',
        'packaging',
        'packaging.version',
        'packaging.specifiers',
        'packaging.requirements',
    ])
    
    # Try to detect and include Python shared library
    import sys
    import os
    python_lib_path = None
    
    # Find Python shared library in common locations for GitHub Actions
    possible_paths = [
        f"{sys.prefix}/lib/libpython{sys.version_info.major}.{sys.version_info.minor}.dylib",
        f"{sys.prefix}/lib/python{sys.version_info.major}.{sys.version_info.minor}/config-{sys.version_info.major}.{sys.version_info.minor}-darwin/libpython{sys.version_info.major}.{sys.version_info.minor}.dylib",
        f"/usr/local/lib/libpython{sys.version_info.major}.{sys.version_info.minor}.dylib",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            python_lib_path = path
            print(f"Found Python library at: {python_lib_path}")
            intel_binaries.append((python_lib_path, '.'))
            break
    
    if not python_lib_path:
        print(f"Warning: Could not find Python shared library. Checked paths: {possible_paths}")

a = Analysis(
    ['main.py'],
    pathex=[current_dir],
    binaries=intel_binaries,
    datas=[
        ("app/styles/*.qss", "styles"),
        ("app/resources/ffmpeg/", "app/resources/ffmpeg"),
        ("app/_version.py", "app"),
    ],
    hiddenimports=intel_hiddenimports,
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

    if IS_INTEL_CI:
        print("Creating Intel CI build with enhanced Python bundling")
        # For Intel CI builds, use onefile but with explicit Python runtime inclusion
        # to avoid embedded signature issues while ensuring Python is bundled
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
            upx=False,  # Disable UPX for Intel builds to avoid compression issues
            upx_exclude=[],
            runtime_tmpdir=None,
            console=CONSOLE,
            disable_windowed_traceback=False,
            argv_emulation=False,
            target_arch=None,
            codesign_identity=APPLE_DEVELOPER_ID,
            entitlements_file=None,
        )
    else:
        print("Creating standard build with onefile mode")
        # Use onefile mode for local builds (ARM64)
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

    # Both Intel and ARM64 builds now use the same BUNDLE structure (onefile mode)
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
