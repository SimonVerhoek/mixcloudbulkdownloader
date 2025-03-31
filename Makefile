# Load variables from the .env file
include .env
export

.PHONY: clean install build dmg

# Define variables
APP_NAME = Mixcloud\ Bulk\ Downloader.app
DIST_PATH = dist/$(APP_NAME)
DMG_NAME = Mixcloud\ Bulk\ Downloader.dmg

# Setup a proper development environment
setupdev:
	# Make sure you have the Python version mandated in .python-version installed and set up!
	python -m venv venv
	source venv/bin/activate
	pip install --upgrade pip
	pip install poetry
	venv/bin/poetry install --with dev

# Target to clean the existing installation
clean:
	venv/bin/poetry remove pyside6

# Target to install the latest PySide6 version
install:
	venv/bin/poetry add pyside6@latest

# Target to build the app using PyInstaller
build:
	venv/bin/pyinstaller --clean -y app.spec

# Target to create the DMG file
dmg:
	create-dmg --overwrite $(DIST_PATH)

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
	codesign --deep --force --verify --verbose --sign $(APPLE_DEVELOPER_ID) --options runtime $(DIST_PATH)
