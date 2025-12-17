# Note: Environment variables are now loaded by app.spec based on BUILD_ENV

.PHONY: clean install build-dev build-prod dmg prepare-release-intel

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
build-dev:
	BUILD_ENV=dev pyinstaller --clean -y --log-level INFO app.spec

# Target to build the app for production using PyInstaller
build-prod:
	BUILD_ENV=prod pyinstaller --clean -y --log-level INFO app.spec

# Target to create the DMG file
dmg:
	create-dmg --app-drop-link 0 35 "$(DMG_NAME)" "$(DIST_PATH)"

# Verify the certificate used for code signing
verify-certificate:
	security find-identity -p basic -v

# Verify whether the app is ready for code signing
# Should return:
# 	valid on disk
#	satisfies its Designated Requirement
verify-codesign:
	codesign --verify --deep --strict --verbose=2 "$(DIST_PATH)"

# Verify Intel onedir app bundle signing
verify-intel-codesign:
	@echo "Verifying Intel onedir app bundle signatures..."
	@echo "=== Verifying individual components ==="
	@find "$(INTEL_DIST_PATH)/Contents/MacOS" -type f \( -name "*.dylib" -o -name "*.so" -o -perm +111 \) -exec echo "Checking: {}" \; -exec codesign --verify --verbose {} \; || true
	@echo "=== Verifying main executable ==="
	@codesign --verify --verbose "$(INTEL_DIST_PATH)/Contents/MacOS/Mixcloud Bulk Downloader"
	@echo "=== Verifying entire app bundle ==="
	@codesign --verify --deep --strict --verbose=2 "$(INTEL_DIST_PATH)"

# Codesign the MacOS app
# NOTE: as `make dmg` already attempts to codesign the app, this command is not necessary in practice
codesign-app:
	@if [ ! -f .env.prod ]; then echo "Error: .env.prod file not found"; exit 1; fi
	@set -a && source .env.prod && codesign --strict --deep --force --verify --verbose --sign "$$APPLE_DEVELOPER_ID" --options runtime "$(DIST_PATH)"

# Codesign Intel onedir app bundle with individual file signing
# This target specifically handles the onedir structure from Intel CI builds
codesign-intel-onedir:
	@if [ ! -f .env.prod ]; then echo "Error: .env.prod file not found"; exit 1; fi
	@echo "Signing Intel onedir build with individual component signing..."
	@set -a && source .env.prod && \
	echo "Step 1: Sign all dylibs and executables in MacOS directory" && \
	find "$(INTEL_DIST_PATH)/Contents/MacOS" -type f \( -name "*.dylib" -o -name "*.so" -o -perm +111 \) -exec codesign --force --verify --verbose --sign "$$APPLE_DEVELOPER_ID" --options runtime {} \; && \
	echo "Step 2: Sign main executable" && \
	codesign --force --verify --verbose --sign "$$APPLE_DEVELOPER_ID" --options runtime "$(INTEL_DIST_PATH)/Contents/MacOS/Mixcloud Bulk Downloader" && \
	echo "Step 3: Sign entire app bundle" && \
	codesign --strict --force --verify --verbose --sign "$$APPLE_DEVELOPER_ID" --options runtime "$(INTEL_DIST_PATH)"

notarize:
	@if [ ! -f .env.prod ]; then echo "Error: .env.prod file not found"; exit 1; fi
	@set -a && source .env.prod && xcrun notarytool submit "$(DMG_NAME)" --keychain-profile $$KEYCHAIN_PROFILE --wait

staple:
	xcrun stapler staple "$(DMG_NAME)"

# Prepare Intel release: codesign, create DMG, notarize, and staple  
# Note: Assumes Intel .app bundle is already in dist-macos-intel/
# Both Intel and ARM64 now use standard onefile signing
prepare-release-intel:
	@echo "Preparing Intel release..."
	$(MAKE) codesign-app DIST_PATH='$(INTEL_DIST_PATH)'
	$(MAKE) dmg DIST_PATH='$(INTEL_DIST_PATH)' DMG_NAME='$(INTEL_DMG_NAME)'
	$(MAKE) notarize DMG_NAME='$(INTEL_DMG_NAME)'
	$(MAKE) staple DMG_NAME='$(INTEL_DMG_NAME)'
	@echo "Intel release ready: $(INTEL_DMG_NAME)"

# Prepare ARM64 release (default local build)
prepare-release: build-prod dmg notarize staple
