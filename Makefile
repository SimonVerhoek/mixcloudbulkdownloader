.PHONY: clean install build dmg

# Define variables
APP_NAME = Mixcloud\ Bulk\ Downloader.app
DIST_PATH = dist/$(APP_NAME)

# Target to clean the existing installation
clean:
	poetry remove pyside6

# Target to install the latest PySide6 version
install:
	poetry add pyside6@latest

# Target to build the app using PyInstaller
build:
	pyinstaller --clean -y app.spec

# Target to create the DMG file
dmg:
	create-dmg --overwrite $(DIST_PATH)

# Default target
all: clean install build dmg
