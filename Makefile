# Note: Environment variables are now loaded by app.spec based on BUILD_ENV

.PHONY: clean install build-dev build-prod dmg

# Define variables
APP_NAME = Mixcloud\ Bulk\ Downloader.app
DIST_PATH = dist/$(APP_NAME)
VERSION := $(shell grep '^version =' pyproject.toml | sed -E 's/version = "(.*)"/\1/')
DMG_NAME = Mixcloud\ Bulk\ Downloader\ ${VERSION}.dmg


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
	create-dmg ${DMG_NAME} $(DIST_PATH)

# Verify the certificate used for code signing
verify-certificate:
	security find-identity -p basic -v

# Verify whether the app is ready for code signing
# Should return:
# 	valid on disk
#	satisfies its Designated Requirement
verify-codesign:
	codesign --verify --deep --strict --verbose=2 $(DIST_PATH)

# Codesign the MacOS app
# NOTE: as `make dmg` already attempts to codesign the app, this command is not necessary in practice
codesign-app:
	@if [ ! -f .env.prod ]; then echo "Error: .env.prod file not found"; exit 1; fi
	@set -a && source .env.prod && codesign --strict --deep --force --verify --verbose --sign "$$APPLE_DEVELOPER_ID" --options runtime $(DIST_PATH)

notarize:
	@if [ ! -f .env.prod ]; then echo "Error: .env.prod file not found"; exit 1; fi
	@set -a && source .env.prod && xcrun notarytool submit $(DMG_NAME) --keychain-profile $$KEYCHAIN_PROFILE --wait

staple:
	xcrun stapler staple $(DMG_NAME)

prepare-release: build-prod dmg notarize staple
