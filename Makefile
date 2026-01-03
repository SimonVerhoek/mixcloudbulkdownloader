# Note: Environment variables are now loaded by app.spec based on BUILD_ENV

.PHONY: clean install build-dev build-prod dmg intel-build-dmg intel-env prepare-release

# Define variables
APP_NAME = Mixcloud Bulk Downloader.app
VERSION := $(shell grep '^version =' pyproject.toml | sed -E 's/version = "(.*)"/\1/')

# Default variables (can be overridden)
DIST_PATH ?= dist/$(APP_NAME)
DMG_NAME ?= Mixcloud Bulk Downloader ${VERSION}.dmg

# Intel-specific variables
INTEL_DIST_DIR = dist-macos-intel
INTEL_DIST_PATH = $(INTEL_DIST_DIR)/$(APP_NAME)
INTEL_DMG_NAME = Mixcloud Bulk Downloader ${VERSION} (Intel).dmg


# Setup a proper development environment
setupdev:
	# Make sure you have the Python version mandated in .python-version installed and set up!
	python -m venv venv
	source venv/bin/activate
	pip install --upgrade pip
	pip install poetry
	poetry install --with dev

# Target to clean the existing installation
clean:
	poetry remove pyside6

# Target to install the latest PySide6 version
install:
	poetry add pyside6@latest

# Target to build the app for development using PyInstaller
# Usage: make build-dev ARCH=arm64|intel (defaults to arm64)
build-dev:
ifeq ($(ARCH),intel)
	@echo "Building Intel development version using Rosetta and venv-intel..."
	arch -x86_64 zsh -c "source venv-intel/bin/activate && BUILD_ENV=dev pyinstaller --clean -y --log-level INFO app.spec --distpath dist-macos-intel"
else
	@echo "Building ARM64 development version using native shell and venv..."
	@echo "🔧 Using ARM64 environment with isolated library paths..."
	env -i \
		PATH="/Users/simonverhoek/PycharmProjects/mixcloud_bulk_downloader/mixcloud_bulk_downloader/venv/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/bin:/bin:/usr/sbin:/sbin" \
		DYLD_LIBRARY_PATH="/opt/homebrew/lib" \
		PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig" \
		HOMEBREW_PREFIX="/opt/homebrew" \
		HOMEBREW_CELLAR="/opt/homebrew/Cellar" \
		HOMEBREW_REPOSITORY="/opt/homebrew" \
		HOME="$(HOME)" \
		USER="$(USER)" \
		PYTHONPATH="$(shell source venv/bin/activate && python -c 'import sys; print(":".join(sys.path[1:]))')" \
		bash -c "source venv/bin/activate && BUILD_ENV=dev pyinstaller --clean -y --log-level INFO app.spec"
endif

# Target to build the app for production using PyInstaller
# Usage: make build-prod ARCH=arm64|intel (defaults to arm64)
build-prod:
ifeq ($(ARCH),intel)
	@echo "Building Intel version using Rosetta and venv-intel..."
	arch -x86_64 zsh -c "source venv-intel/bin/activate && BUILD_ENV=prod pyinstaller --clean -y --log-level INFO app.spec --distpath dist-macos-intel"
else
	@echo "Building ARM64 version using native shell and venv..."
	@echo "🔧 Using ARM64 environment with isolated library paths..."
	env -i \
		PATH="/Users/simonverhoek/PycharmProjects/mixcloud_bulk_downloader/mixcloud_bulk_downloader/venv/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/bin:/bin:/usr/sbin:/sbin" \
		DYLD_LIBRARY_PATH="/opt/homebrew/lib" \
		PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig" \
		HOMEBREW_PREFIX="/opt/homebrew" \
		HOMEBREW_CELLAR="/opt/homebrew/Cellar" \
		HOMEBREW_REPOSITORY="/opt/homebrew" \
		HOME="$(HOME)" \
		USER="$(USER)" \
		PYTHONPATH="$(shell source venv/bin/activate && python -c 'import sys; print(":".join(sys.path[1:]))')" \
		bash -c "source venv/bin/activate && BUILD_ENV=prod pyinstaller --clean -y --log-level INFO app.spec"
endif

# Target to create the DMG file
dmg:
	create-dmg --app-drop-link 0 35 "$(DMG_NAME)" "$(DIST_PATH)"

# Build Intel app and create DMG (without notarization)
intel-build-dmg:
	@echo "Building Intel app and creating DMG..."
	$(MAKE) build-prod ARCH=intel
	$(MAKE) dmg DIST_PATH='$(INTEL_DIST_PATH)' DMG_NAME='$(INTEL_DMG_NAME)'
	@echo "Intel DMG ready: $(INTEL_DMG_NAME)"

# Intel environment setup with complete isolation
intel-env:
	@echo "🔧 Starting Intel environment with complete isolation..."
	@arch -x86_64 zsh -c '\
		export PATH="/usr/local/bin:/usr/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin" && \
		export HOME="$(HOME)" && \
		export USER="$(USER)" && \
		export HOMEBREW_PREFIX="/usr/local" && \
		export HOMEBREW_CELLAR="/usr/local/Cellar" && \
		export HOMEBREW_REPOSITORY="/usr/local/Homebrew" && \
		export HOMEBREW_NO_AUTO_UPDATE=1 && \
		export ARCHFLAGS="-arch x86_64" && \
		export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig" && \
		export LDFLAGS="-L/usr/local/opt/openssl@3/lib -L/usr/local/opt/gettext/lib -L/usr/local/lib" && \
		export CPPFLAGS="-I/usr/local/opt/openssl@3/include -I/usr/local/opt/gettext/include -I/usr/local/include" && \
		export OPENSSL_ROOT_DIR="/usr/local/opt/openssl@3" && \
		export CC="clang -arch x86_64" && \
		export CXX="clang++ -arch x86_64" && \
		cd $(PWD) && \
		source venv-intel/bin/activate && \
		echo "✅ Intel environment ready" && \
		python -c "import platform; print(f\"Architecture: {platform.machine()}, Python: {platform.python_version()}\")" && \
		exec zsh'

# Verify the certificate used for code signing
verify-certificate:
	security find-identity -p basic -v

# Verify whether the app is ready for code signing
# Should return:
# 	valid on disk
#	satisfies its Designated Requirement
verify-codesign:
	codesign --verify --deep --strict --verbose=2 "$(DIST_PATH)"

# Codesign the MacOS app
# NOTE: as `make dmg` already attempts to codesign the app, this command is not necessary in practice
codesign-app:
	@if [ ! -f .env.prod ]; then echo "Error: .env.prod file not found"; exit 1; fi
	@set -a && source .env.prod && codesign --strict --deep --force --verify --verbose --sign "$$APPLE_DEVELOPER_ID" --options runtime "$(DIST_PATH)"

notarize:
	@if [ ! -f .env.prod ]; then echo "Error: .env.prod file not found"; exit 1; fi
	@set -a && source .env.prod && xcrun notarytool submit "$(DMG_NAME)" --keychain-profile $$KEYCHAIN_PROFILE --wait

staple:
	xcrun stapler staple "$(DMG_NAME)"

# Unified release preparation target
# Usage: make prepare-release ARCH=arm64|intel (defaults to arm64)
prepare-release:
ifeq ($(ARCH),intel)
	@echo "Preparing Intel release..."
	$(MAKE) build-prod ARCH=intel
	$(MAKE) dmg DIST_PATH='$(INTEL_DIST_PATH)' DMG_NAME='$(INTEL_DMG_NAME)'
	$(MAKE) notarize DMG_NAME='$(INTEL_DMG_NAME)'
	$(MAKE) staple DMG_NAME='$(INTEL_DMG_NAME)'
	@echo "Intel release ready: $(INTEL_DMG_NAME)"
else
	@echo "Preparing ARM64 release..."
	$(MAKE) build-prod ARCH=arm64
	$(MAKE) dmg
	$(MAKE) notarize
	$(MAKE) staple
	@echo "ARM64 release ready: $(DMG_NAME)"
endif
