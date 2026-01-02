# Intel Build Setup via Rosetta

This document provides step-by-step instructions for setting up a local Intel build environment on ARM64 Mac using Rosetta emulation.

## Prerequisites

- ✅ Rosetta 2 installed on ARM64 Mac
- ✅ Existing ARM64 development environment working
- ✅ Apple Developer certificates configured locally

## Overview

This setup creates a completely separate Intel Python environment that builds Intel binaries locally, eliminating cross-compilation issues and maintaining secure local signing.

## Step 1: Install Intel Python via Rosetta

### 1.1: Check and Install Intel Homebrew

```bash
# Open Terminal in Intel mode
arch -x86_64 zsh

# Check if Intel Homebrew is already installed
if [ -f "/usr/local/bin/brew" ]; then
    echo "Intel Homebrew already installed at /usr/local/bin/brew"
else
    echo "Installing Intel Homebrew to /usr/local..."
    # Install Intel Homebrew (will install to /usr/local for x86_64)
    arch -x86_64 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Verify dual Homebrew installation
echo "=== ARM64 Homebrew (existing) ==="
/opt/homebrew/bin/brew --version | head -1
file /opt/homebrew/bin/brew

echo "=== Intel Homebrew (for Intel builds) ==="
/usr/local/bin/brew --version | head -1
file /usr/local/bin/brew
# Should show: x86_64
```

### 1.2: Install pyenv and Python 3.11.5

```bash
# Still in Intel mode (arch -x86_64 zsh)
# Install pyenv using Intel Homebrew for precise version control (if not already installed)
arch -x86_64 /usr/local/bin/brew install pyenv

# Install pyenv-rosetta-suffix plugin for automatic x86 naming
git clone https://github.com/orlevii/pyenv-rosetta-suffix.git $(pyenv root)/plugins/pyenv-rosetta-suffix

# Add pyenv to your shell (if not already done)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# Reload shell configuration
source ~/.zshrc
```

### 1.3: Install Intel Python 3.11.5

With the pyenv-rosetta-suffix plugin installed, Intel Python versions will automatically get a `_x86` suffix. **Critical**: Complete environment isolation is required to prevent ARM64/x86_64 library conflicts.

```bash
# IMPORTANT: Start with completely clean environment to avoid ARM64/x86_64 conflicts
arch -x86_64 env -i zsh

# Set minimal clean PATH (x86_64 paths first, no ARM64 Homebrew paths)
export PATH="/usr/local/bin:/usr/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin"
export HOME="/Users/$(whoami)"
export USER="$(whoami)"

# Set complete x86_64 Homebrew environment (critical for proper library linking)
export HOMEBREW_PREFIX="/usr/local"
export HOMEBREW_CELLAR="/usr/local/Cellar"
export HOMEBREW_REPOSITORY="/usr/local/Homebrew"
export HOMEBREW_NO_AUTO_UPDATE=1

# Python build environment variables for x86_64
export ARCHFLAGS="-arch x86_64"
export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig"
export LDFLAGS="-L/usr/local/opt/openssl@3/lib -L/usr/local/opt/gettext/lib -L/usr/local/lib"
export CPPFLAGS="-I/usr/local/opt/openssl@3/include -I/usr/local/opt/gettext/include -I/usr/local/include"
export OPENSSL_ROOT_DIR="/usr/local/opt/openssl@3"
export CC="clang -arch x86_64"
export CXX="clang++ -arch x86_64"

# Install required x86_64 dependencies including build tools
/usr/local/bin/brew install openssl@3 libb2 gettext libffi readline sqlite3 xz zlib create-dmg

# Install Python 3.11.5 - will automatically be named 3.11.5_x86
pyenv install 3.11.5 --keep --verbose

# Alternative one-line command approach:
# arch -x86_64 env \
#   ARCHFLAGS="-arch x86_64" \
#   HOMEBREW_PREFIX="/usr/local" \
#   PKG_CONFIG_PATH="/usr/local/lib/pkgconfig" \
#   LDFLAGS="-L/usr/local/opt/gettext/lib -L/usr/local/lib" \
#   CPPFLAGS="-I/usr/local/opt/gettext/include" \
#   CC="clang -arch x86_64" \
#   CXX="clang++ -arch x86_64" \
#   pyenv install 3.11.5 --keep --verbose

# Verify both architectures are available (if you had ARM64 version)
pyenv versions | grep 3.11.5
# Should show:
# 3.11.5 (ARM64 version, if it existed)
# 3.11.5_x86 (Intel version)

# Verify Intel Python 3.11.5 installation
arch -x86_64 ~/.pyenv/versions/3.11.5_x86/bin/python -c "import platform; print(f'Architecture: {platform.machine()}, Python: {platform.python_version()}')"
# Expected output: Architecture: x86_64, Python: 3.11.5

# CRITICAL: Verify blake2 support is working (fixes blake2b errors)
arch -x86_64 ~/.pyenv/versions/3.11.5_x86/bin/python -c "
import hashlib
print('✅ Blake2b available:', 'blake2b' in hashlib.algorithms_available)
print('✅ Blake2s available:', 'blake2s' in hashlib.algorithms_available)
try:
    h = hashlib.blake2b(b'test')
    print('✅ Blake2b functional:', h.hexdigest()[:16] + '...')
    print('✅ No blake2 import errors - environment is correctly isolated!')
except Exception as e:
    print('❌ Blake2 error:', str(e))
"

# Verify build tools are available in isolated environment
which create-dmg && echo "✅ create-dmg available" || echo "❌ create-dmg not found"
which pyinstaller && echo "✅ pyinstaller available" || echo "❌ pyinstaller not found (will be installed later in venv)"
```

### 1.4: Fix Hardcoded Library Paths (RPATH Fix) (Optional)

**Note**: With the pyenv-rosetta-suffix plugin, RPATH issues are much less common since there's no version name conflicts. However, if you still get "library not loaded" errors:

```bash
# Check if Intel Python has hardcoded path issues
arch -x86_64 ~/.pyenv/versions/3.11.5_x86/bin/python -c "print('Testing library loading...')"

# If you get errors like:
# "Library not loaded: /Users/.../3.11.5/lib/libpython3.11.dylib (have 'arm64', need 'x86_64')"
# Then fix the hardcoded library paths:

echo "Fixing hardcoded library paths in Intel Python binary..."

# Fix the main Python executable (adjust paths if needed)
install_name_tool -change \
  /Users/$(whoami)/.pyenv/versions/3.11.5/lib/libpython3.11.dylib \
  /Users/$(whoami)/.pyenv/versions/3.11.5_x86/lib/libpython3.11.dylib \
  ~/.pyenv/versions/3.11.5_x86/bin/python3.11

# Also fix the unversioned python symlink if it exists
if [ -f ~/.pyenv/versions/3.11.5_x86/bin/python ]; then
  install_name_tool -change \
    /Users/$(whoami)/.pyenv/versions/3.11.5/lib/libpython3.11.dylib \
    /Users/$(whoami)/.pyenv/versions/3.11.5_x86/lib/libpython3.11.dylib \
    ~/.pyenv/versions/3.11.5_x86/bin/python
fi

# Verify the fix worked
echo "Testing Intel Python after RPATH fix..."
arch -x86_64 ~/.pyenv/versions/3.11.5_x86/bin/python -c "import platform; print(f'✅ Success! Architecture: {platform.machine()}, Python: {platform.python_version()}')"
```

### 1.5: Create Homebrew Aliases (Optional)

Add these to your `~/.zshrc` for easy Homebrew management:

```bash
# Homebrew aliases for different architectures
alias brew-arm="/opt/homebrew/bin/brew"
alias brew-intel="arch -x86_64 /usr/local/bin/brew"

# Quick architecture check
alias check-brew="echo 'ARM64 Homebrew:'; /opt/homebrew/bin/brew --version | head -1; echo 'Intel Homebrew:'; /usr/local/bin/brew --version | head -1 2>/dev/null || echo 'Intel Homebrew not installed'"
```

## Step 2: Create Intel Virtual Environment

```bash
# Still in Intel terminal (arch -x86_64 zsh)
# Navigate to your project directory
cd /Users/simonverhoek/PycharmProjects/mixcloud_bulk_downloader/mixcloud_bulk_downloader

# Create Intel virtual environment using architecture-specific pyenv Python 3.11.5_x86
arch -x86_64 ~/.pyenv/versions/3.11.5_x86/bin/python -m venv venv-intel

# Activate Intel environment
source venv-intel/bin/activate

# Verify Intel environment with exact version and architecture
python -c "import platform; print(f'Architecture: {platform.machine()}, Python: {platform.python_version()}')"
# Expected output: Architecture: x86_64, Python: 3.11.5

# Additional verification - test SSL and basic functionality
python -c "import ssl; print('✅ SSL support available')"
python -c "import platform, sys; print(f'✅ Python {platform.python_version()} on {platform.machine()} ready for Intel builds')"
```

## Step 3: Install Intel Poetry & Dependencies

```bash
# Still in activated venv-intel
# Upgrade pip
python -m pip install --upgrade pip

# Install Intel Poetry (specific version for compatibility)
pip install poetry==2.1.4

# Verify Poetry architecture
python -c "import poetry; print('Poetry installed successfully')"

# Deactivate and reactivate venv to refresh PATH for poetry command
deactivate
source venv-intel/bin/activate

# Install project dependencies (all will be Intel-compiled)
poetry install --with dev --without ci

# Verify key dependencies are Intel-compiled
python -c "import PyInstaller; print('PyInstaller available')"
python -c "import PySide6; print('PySide6 available')"
python -c "import httpx; print('httpx available')"
python -c "import yt_dlp; print('yt_dlp available')"
```

## Step 4: Download Intel ffmpeg

```bash
# Still in Intel environment and project root
# The ffmpeg download script should automatically detect Intel architecture
chmod +x ./scripts/download_ffmpeg.sh
./scripts/download_ffmpeg.sh

# Verify Intel ffmpeg was downloaded
file app/resources/ffmpeg/ffmpeg
# Expected output: should show x86_64 architecture
```

## Step 5: Test Intel Build

```bash
# Still in Intel environment
# Build Intel version locally using new unified make command
make build-dev ARCH=intel

# Verify Intel build architecture
file "dist-macos-intel/Mixcloud Bulk Downloader.app/Contents/MacOS/Mixcloud Bulk Downloader"
# Expected output: Mach-O 64-bit executable x86_64

# Check app bundle size (should be substantial, similar to ARM64 build)
du -sh "dist-macos-intel/Mixcloud Bulk Downloader.app"

# Test the Intel app (should launch without Python runtime errors)
open "dist-macos-intel/Mixcloud Bulk Downloader.app"

# Comprehensive verification of Intel build
echo "=== Comprehensive Intel Build Verification ==="

# 1. Check main executable architecture
echo "1. Main executable architecture:"
file "dist-macos-intel/Mixcloud Bulk Downloader.app/Contents/MacOS/Mixcloud Bulk Downloader"
# Should show: x86_64

# 2. Check for any ARM64 contamination  
echo "2. Scanning for ARM64 libraries (should find none):"
find "dist-macos-intel/Mixcloud Bulk Downloader.app" -name "*.dylib" -o -name "*.so" | xargs file | grep arm64 || echo "✅ No ARM64 libraries found"

# 3. Check Python runtime libraries
echo "3. Python runtime libraries:"
find "dist-macos-intel/Mixcloud Bulk Downloader.app" -name "*python*" | xargs file | head -3

# 4. Check application dependencies
echo "4. Main executable dependencies:"
otool -L "dist-macos-intel/Mixcloud Bulk Downloader.app/Contents/MacOS/Mixcloud Bulk Downloader" | head -10

# 5. Verify app bundle structure
echo "5. App bundle structure:"
ls -la "dist-macos-intel/Mixcloud Bulk Downloader.app/Contents/"

echo "✅ Intel build verification complete"
```

## Step 6: Intel Environment Make Command

For convenient access to the Intel environment with all proper environment variables, use the dedicated Make command:

```bash
# Enter Intel environment with complete isolation and all environment variables
make intel-env

# This command will:
# - Start isolated x86_64 shell with env -i
# - Set all required environment variables from Step 1.3
# - Activate venv-intel virtual environment
# - Navigate to project directory
# - Provide architecture and Python version confirmation
# - Drop you into an interactive Intel shell
```

### What make intel-env Does

The `make intel-env` command automatically sets up the complete Intel environment including:

- **Clean Environment**: Uses `arch -x86_64 env -i zsh` for complete isolation
- **Proper PATH**: `/usr/local/bin:/usr/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin`
- **Homebrew Variables**: `HOMEBREW_PREFIX`, `HOMEBREW_CELLAR`, `HOMEBREW_REPOSITORY`
- **Build Variables**: `ARCHFLAGS`, `PKG_CONFIG_PATH`, `LDFLAGS`, `CPPFLAGS`
- **Compiler Settings**: `CC`, `CXX`, `OPENSSL_ROOT_DIR`
- **Virtual Environment**: Activates `venv-intel` automatically

### Optional: Check Architecture Function

You can optionally add this function to `~/.zshrc` for quick architecture verification:

```bash
# Function to check current architecture
check-arch() {
    echo "Shell: $(arch)"
    echo "Python: $(python -c 'import platform; print(platform.machine())' 2>/dev/null || echo 'No Python active')"
    echo "Venv: ${VIRTUAL_ENV:-'No virtual environment active'}"
}
```

## Step 7: Complete Intel Build & Sign Workflow

```bash
# 1. Build and prepare Intel release using new unified command
make intel-env
# In the Intel environment shell:
make prepare-release ARCH=intel

# This single command will:
# - Build the Intel app using Rosetta and venv-intel
# - Code sign the Intel app with your local certificates
# - Create Intel DMG 
# - Notarize with Apple
# - Staple the notarization
```

## Verification Steps

### After Setup
```bash
# Verify Intel environment works
make intel-env
check-arch  # (if you added the optional function)
# Should show: Shell: x86_64, Python: x86_64

# Verify ARM environment still works (regular shell)
source venv/bin/activate
check-arch  # (if you added the optional function)
# Should show: Shell: arm64, Python: arm64
```

### After Build
```bash
# Verify Intel app architecture
file "dist-macos-intel/Mixcloud Bulk Downloader.app/Contents/MacOS/Mixcloud Bulk Downloader"
# Should show: x86_64

# Test Intel app launches correctly
open "dist-macos-intel/Mixcloud Bulk Downloader.app"
# Should launch without Python runtime errors

# Verify signing (after make prepare-release-intel)
codesign -dv --verbose=4 "dist-macos-intel/Mixcloud Bulk Downloader.app"
# Should show your Developer ID signature
```

## Common Build Issues

### Blake2b/Blake2s Import Errors

If you encounter errors like:
```
ERROR:root:code for hash blake2b was not found.
ValueError: unsupported hash type blake2b
```

This indicates **ARM64/x86_64 library path conflicts**. The Python was built using ARM64 libraries instead of x86_64 libraries. **Solution:** Use complete environment isolation as described above.

### gettext/libintl Linking Errors

If you encounter build failures with errors like:
```
"_libintl_textdomain", referenced from:
    __locale_textdomain in _localemodule.o
ld: symbol(s) not found for architecture x86_64
```

This indicates missing or incorrect gettext libraries. **Solution:**

```bash
# Ensure x86_64 gettext is installed
arch -x86_64 /usr/local/bin/brew install gettext

# Set environment variables and retry Python installation
export ARCHFLAGS="-arch x86_64"
export HOMEBREW_PREFIX="/usr/local"
export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:/usr/local/share/pkgconfig"
export LDFLAGS="-L/usr/local/opt/gettext/lib -L/usr/local/lib"
export CPPFLAGS="-I/usr/local/opt/gettext/include -I/usr/local/include"
export CC="clang -arch x86_64"
export CXX="clang++ -arch x86_64"

# Install Python with these environment variables set
arch -x86_64 pyenv install 3.11.5 --keep --verbose
```

**Note:** These environment variables are crucial when building x86_64 Python on Apple Silicon Macs to ensure proper linking against x86_64 libraries.

## Troubleshooting

### Python Architecture Issues
```bash
# If Python shows wrong architecture, ensure you're in correct terminal mode
arch -x86_64 zsh  # Force Intel mode
which python      # Should point to Intel Python path
```

### PyInstaller Build Failures
```bash
# Clean build if needed
rm -rf build dist dist-macos-intel
make build-dev ARCH=intel
```

### Dependencies Not Intel
```bash
# Reinstall dependencies in Intel environment
pip uninstall -y PyInstaller PySide6
pip install PyInstaller PySide6
```

### pyenv Installation Issues
```bash
# If pyenv install fails, you may need build dependencies
arch -x86_64 /usr/local/bin/brew install openssl readline sqlite3 xz zlib

# If you get gettext/libintl linking errors, ensure gettext is installed
arch -x86_64 /usr/local/bin/brew install gettext

# Ensure pyenv-rosetta-suffix plugin is installed
git clone https://github.com/orlevii/pyenv-rosetta-suffix.git $(pyenv root)/plugins/pyenv-rosetta-suffix

# CRITICAL: Use complete environment isolation to fix blake2b/library conflicts
arch -x86_64 env -i zsh

# Set minimal clean PATH (x86_64 paths first, no ARM64 Homebrew paths)
export PATH="/usr/local/bin:/usr/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin"
export HOME="/Users/$(whoami)"
export USER="$(whoami)"

# Set complete x86_64 Homebrew environment (critical for proper library linking)
export HOMEBREW_PREFIX="/usr/local"
export HOMEBREW_CELLAR="/usr/local/Cellar"
export HOMEBREW_REPOSITORY="/usr/local/Homebrew"
export HOMEBREW_NO_AUTO_UPDATE=1

# Python build environment variables for x86_64
export ARCHFLAGS="-arch x86_64"
export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig"
export LDFLAGS="-L/usr/local/opt/openssl@3/lib -L/usr/local/opt/gettext/lib -L/usr/local/lib"
export CPPFLAGS="-I/usr/local/opt/openssl@3/include -I/usr/local/opt/gettext/include -I/usr/local/include"
export OPENSSL_ROOT_DIR="/usr/local/opt/openssl@3"
export CC="clang -arch x86_64"
export CXX="clang++ -arch x86_64"

# Install required x86_64 dependencies including build tools
/usr/local/bin/brew install openssl@3 libb2 gettext libffi readline sqlite3 xz zlib create-dmg

# Install Python (will automatically be named 3.11.5_x86 with the plugin)
pyenv install 3.11.5 --keep --verbose

# Check if version was installed correctly
pyenv versions | grep 3.11.5_x86
```

### Architecture Coexistence Issues
```bash
# With pyenv-rosetta-suffix plugin, version conflicts should not occur
echo "Current pyenv versions:"
pyenv versions

# Check what architecture existing versions are
if [ -f ~/.pyenv/versions/3.11.5/bin/python ]; then
  echo "ARM64 version (3.11.5):"
  file ~/.pyenv/versions/3.11.5/bin/python
fi

if [ -f ~/.pyenv/versions/3.11.5_x86/bin/python ]; then
  echo "Intel version (3.11.5_x86):"
  file ~/.pyenv/versions/3.11.5_x86/bin/python
  # Should show: x86_64
fi

# If the plugin wasn't installed before, you may need to reinstall Intel Python
# to get the _x86 suffix
```

### Library Loading Errors (RPATH Issues)

If you encounter errors like:
```
dyld: Library not loaded: /Users/.../3.11.5/lib/libpython3.11.dylib
Reason: tried: '...' (mach-o file, but is an incompatible architecture (have 'arm64', need 'x86_64'))
```

This means hardcoded library paths need fixing:

```bash
# Diagnose the issue
echo "=== Diagnosing RPATH issues ==="

# 1. Check what library paths are embedded in Intel Python
otool -L ~/.pyenv/versions/3.11.5_x86/bin/python3.11 | grep python
# Look for paths pointing to wrong directories

# 2. Check if ARM64 version exists at the problematic path
if [ -f ~/.pyenv/versions/3.11.5/lib/libpython3.11.dylib ]; then
  echo "ARM64 library found at conflicting path:"
  file ~/.pyenv/versions/3.11.5/lib/libpython3.11.dylib
fi

# 3. Apply the RPATH fix
echo "Applying RPATH fix..."
install_name_tool -change \
  /Users/$(whoami)/.pyenv/versions/3.11.5/lib/libpython3.11.dylib \
  /Users/$(whoami)/.pyenv/versions/3.11.5_x86/lib/libpython3.11.dylib \
  ~/.pyenv/versions/3.11.5_x86/bin/python3.11

# Fix additional Python executables if they exist
for py_exec in ~/.pyenv/versions/3.11.5_x86/bin/python*; do
  if [ -f "$py_exec" ] && [ ! -L "$py_exec" ]; then
    echo "Fixing RPATH for: $py_exec"
    install_name_tool -change \
      /Users/$(whoami)/.pyenv/versions/3.11.5/lib/libpython3.11.dylib \
      /Users/$(whoami)/.pyenv/versions/3.11.5_x86/lib/libpython3.11.dylib \
      "$py_exec" 2>/dev/null || echo "  (no change needed)"
  fi
done

# 4. Verify the fix
echo "Testing fix..."
arch -x86_64 ~/.pyenv/versions/3.11.5_x86/bin/python3.11 -c "print('✅ RPATH fix successful!')"

# 5. Verify no remaining RPATH issues
echo "Updated library paths:"
otool -L ~/.pyenv/versions/3.11.5_x86/bin/python3.11 | grep python
```

### pyenv Python Not Found
```bash
# Ensure pyenv is properly initialized
source ~/.zshrc

# Check pyenv path
echo $PYENV_ROOT
# Should show: /Users/[username]/.pyenv

# Verify Python 3.11.5_x86 exists
ls ~/.pyenv/versions/
# Should include: 3.11.5_x86 (and possibly 3.11.5 for ARM64)
```

### ffmpeg Architecture Wrong
```bash
# Re-download ffmpeg in Intel environment
rm -rf app/resources/ffmpeg
./scripts/download_ffmpeg.sh
```

## Benefits of This Approach

- ✅ **Security**: All certificates stay local, no CI exposure
- ✅ **Consistency**: Same machine builds and signs Intel app
- ✅ **No Cross-Compilation**: Pure Intel environment eliminates signature conflicts
- ✅ **Control**: Full control over Intel build environment
- ✅ **Simplicity**: No complex CI setup or secret management

## Maintenance

### Updating Dependencies
```bash
# Update Intel environment
make intel-env
# In the Intel environment shell:
poetry update
```

### Cleaning Environments
```bash
# Remove Intel environment if needed
rm -rf venv-intel

# Rebuild from Step 2 if necessary
```

---

**Note**: This setup completely eliminates the need for GitHub Actions Intel builds, providing a secure and reliable local Intel build process.
