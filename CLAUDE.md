# Mixcloud Bulk Downloader - Development Guide

This document provides guidance for AI assistants and developers working on the Mixcloud Bulk Downloader project.

## Project Overview

Mixcloud Bulk Downloader is a desktop application built with PySide6 that allows users to search for Mixcloud users and bulk download their cloudcasts (mixes/shows) for offline listening.

## Architecture

### Core Components

- **main.py**: Application entry point with Qt GUI setup
- **app/data_classes.py**: Data models for MixcloudUser and Cloudcast
- **app/api.py**: Mixcloud API interaction functions
- **app/threads.py**: Background threading for API calls and downloads
- **app/custom_widgets/**: Custom Qt widgets for the UI
- **app/consts.py**: Application constants and configuration values
- **app/logging.py**: Logging configuration

### Key Dependencies

- **PySide6**: Qt GUI framework for desktop interface
- **yt-dlp**: Media downloading library for cloudcast downloads
- **httpx**: HTTP client for API requests
- **Poetry**: Package management and dependency resolution

## Development Standards

### Code Style

- **Type Hints**: Use modern Python type hints (`list[Type]`, `dict[K, V]`, `Type | None`)
- **String Formatting**: Always use f-strings for string interpolation
- **Documentation**: Comprehensive docstrings for all classes, methods, and functions
- **Constants**: Define magic numbers and strings in `app/consts.py`
- **Line Length**: 100 characters (configured in pyproject.toml)
- **Imports**: **ALWAYS** use absolute imports (`from app.module import Item`) instead of relative imports (`from .module import Item`)
- **Import Placement**: **ALL** imports must be placed at the top of the module after docstrings and before any other code. **Exception**: Platform-specific or optional dependency imports may be placed at the top of the specific method/function that uses them, but only when:
  - The import is platform-conditional (e.g., Windows-only, macOS-only)
  - The import is an optional dependency that may not be available
  - The import would cause circular dependencies if placed at module level
  This ensures better performance, clearer dependencies, and easier static analysis while allowing for necessary conditional imports.
- **File Path Handling**: **ALWAYS** use `pathlib.Path` for file path operations instead of `os.path` when possible. This provides better cross-platform compatibility, more readable code, and modern Python best practices. Use `Path` objects for path construction, joining, existence checks, and file operations.
- **Explicit Parameter Names**: **ALWAYS** use explicit parameter names in function and method calls (`function(param1=value1, param2=value2)`) instead of positional arguments (`function(value1, value2)`). This improves code readability, maintainability, and reduces errors when function signatures change. 

**Exceptions:**
  - Built-in functions and very common operations where positional arguments are conventional (e.g., `len(items)`, `str(value)`)
  - Methods/functions that do not accept keyword arguments (e.g., `QTimer.singleShot()`, some Qt methods)
  - When the API documentation explicitly states positional-only parameters

### Styling Guidelines

- **QSS Files**: All styling should be defined in `.qss` files in `./app/styles/`
- **Modular Styling**: Modularize QSS files by component type (`buttons.qss`, `labels.qss`, `dialogs.qss`, etc.)
- **No Inline Styles**: Avoid inline `setStyleSheet()` calls in widget code when possible
- **Component-Based Organization**: Group related styles in dedicated files for maintainability

### Error Handling and Logging

- **Always Log Exceptions**: All exceptions should be logged using the configured logging system
- **Prefer Logging**: Always choose logging over print statements for debugging and error reporting
- **Use Appropriate Log Levels**: Use `log_error()`, `log_api()`, `log_ui()` functions from `app.qt_logger`
- **Structured Error Messages**: Use error message constants from `app/consts.py` for consistency

### File Organization

```
app/
├── __init__.py
├── consts.py              # Application constants
├── data_classes.py        # Data models
├── api.py                 # Mixcloud API functions
├── threads.py             # Background threading classes
├── logging.py             # Logging configuration
└── custom_widgets/        # Qt custom widgets
    ├── __init__.py
    ├── cloudcast_q_tree_widget.py
    ├── cloudcast_q_tree_widget_item.py
    ├── search_user_q_combo_box.py
    ├── user_q_list_widget_item.py
    └── error_dialog.py
```

### Import Guidelines

**CRITICAL**: Always use absolute imports for internal modules.

#### ✅ Correct Import Style
```python
# Absolute imports - ALWAYS use these
from app.consts import MIXCLOUD_API_URL, ERROR_MESSAGES
from app.data_classes import MixcloudUser, Cloudcast
from app.custom_widgets.error_dialog import ErrorDialog
```

#### ❌ Incorrect Import Style
```python
# Relative imports - NEVER use these
from .consts import MIXCLOUD_API_URL, ERROR_MESSAGES
from .data_classes import MixcloudUser, Cloudcast
from ..custom_widgets.error_dialog import ErrorDialog
```

#### Why Absolute Imports?
- **Clarity**: Makes module dependencies explicit and clear
- **Refactoring**: Easier to move files and restructure code
- **IDE Support**: Better autocomplete and navigation in development tools
- **Testing**: Simpler to mock and test individual modules
- **Consistency**: Uniform import style across the entire codebase

## Development Workflows

### Running the Application

```bash
# From project root
python main.py

# Or with Poetry
poetry run python main.py
```

### Testing

```bash
# Run all tests
pytest

# Run tests by category
pytest -m "unit"        # Unit tests only (fast, reliable)
pytest -m "integration" # Integration tests
pytest -m "qt"          # GUI widget tests

# Run tests with coverage report
pytest --cov=app --cov-report=html

# Run with Poetry
poetry run pytest

# Syntax check all Python files
python -m py_compile main.py
python -m py_compile app/*.py
python -m py_compile app/custom_widgets/*.py
```

#### Test Categories

- **Unit Tests** (`-m "unit"`): Fast, isolated tests for services and utilities
- **Integration Tests** (`-m "integration"`): Thread-based tests that verify component interaction  
- **Qt Tests** (`-m "qt"`): GUI widget tests that require display environment

#### Test Configuration

The project uses pytest with configuration defined in `pytest.ini`:

- **Coverage**: Automatic coverage reporting for the `app/` module with HTML output
- **Markers**: Organized test categories for selective execution
- **Qt Support**: Integrated pytest-qt for GUI widget testing
- **Display Handling**: Properly configured for macOS with XQuartz
- **Output**: Verbose output with detailed test progress

### Building for Distribution

The project supports both development and production builds through environment-specific configurations:

#### Development Build
```bash
# Build for development (uses .env with development settings)
make build-dev

# Or manually:
BUILD_ENV=dev pyinstaller --clean -y --log-level INFO app.spec
```

#### Production Build
```bash
# Build for production (uses .env.prod with production settings)
make build-prod

# Or manually:
BUILD_ENV=prod pyinstaller --clean -y --log-level INFO app.spec
```

#### Complete Release Process
```bash
# Build production app, create DMG, notarize, and staple (always uses production settings)
make prepare-release

# Individual steps:
make build-prod                    # Build production version
make dmg                          # Create DMG file
make notarize                     # Notarize with Apple
make staple                       # Staple notarization
```

#### Environment Configuration

- **Development (`.env`)**: `DEBUG=False`, `CONSOLE=False`, `DEVELOPMENT=True`
- **Production (`.env.prod`)**: `DEBUG=False`, `CONSOLE=False`, `DEVELOPMENT=False`

The `BUILD_ENV` environment variable is **mandatory** and must be set to either `dev` or `prod`. The build will fail with a clear error message if this variable is not specified.

### Linting and Formatting

The project uses Black and isort for code formatting:

```bash
poetry run black .
poetry run isort .
```

## Common Tasks

### Adding New Constants

1. Add the constant to `app/consts.py` with proper type hints
2. Import and use the constant instead of magic numbers/strings
3. Update any existing hardcoded values to use the new constant

### Adding New API Endpoints

1. Add URL generation function to `app/api.py`
2. Follow existing patterns for error handling and type hints
3. Add comprehensive docstrings with Args/Returns sections

### Creating New Widgets

1. Create widget file in `app/custom_widgets/`
2. Inherit from appropriate Qt base class
3. Add comprehensive class and method docstrings
4. Use constants from `app/consts.py` for dimensions/values
5. Import and export in `app/custom_widgets/__init__.py`

### Error Handling

- Use the `ErrorDialog` class for user-facing error messages
- Log errors using the configured logging system
- Handle API errors gracefully with user feedback
- Validate user inputs before processing

## Threading Architecture

The application uses Qt's QThread system for background operations:

- **SearchArtistThread**: Searches for Mixcloud users
- **GetCloudcastsThread**: Fetches cloudcasts for a selected user
- **DownloadThread**: Downloads selected cloudcasts

### Thread Safety Guidelines

- Always use Qt signals for thread communication
- Emit signals for progress updates and error handling
- Properly stop threads when canceling operations
- Avoid direct GUI updates from background threads

## API Integration

### Mixcloud API

Base URL: `https://api.mixcloud.com`

Key endpoints:
- User search: `/search/?q={phrase}&type=user`
- User cloudcasts: `/{username}/cloudcasts/`

### Error Handling

- Check for API errors in response JSON
- Handle network timeouts and connection issues
- Provide meaningful error messages to users
- Log API errors for debugging

## UI Guidelines

### Widget Responsibilities

- **SearchUserQComboBox**: User search with debounced input
- **CloudcastQTreeWidget**: Cloudcast display and selection
- **CloudcastQTreeWidgetItem**: Individual cloudcast representation
- **ErrorDialog**: Consistent error message display

### User Experience

- Provide visual feedback for long-running operations
- Allow users to cancel ongoing operations
- Show progress updates during downloads
- Handle empty states gracefully

## Configuration

### Environment Variables

- `LOGGING_LEVEL`: Set logging verbosity (default: INFO)
- `DEVELOPMENT`: Enable development mode logging to console
- `CUSTOM_SETTINGS_PATH`: Override default storage location for settings and credentials (filepath)

### Application Settings

Key configuration values are stored in `app/consts.py`:
- Window dimensions and layout ratios
- API URLs and endpoints
- File extensions and paths
- Error messages and user-facing text

#### Custom Settings Storage

By default, application settings and credentials are stored in platform-specific locations:
- **macOS**: `~/Library/Preferences/com.mixcloud-bulk-downloader.plist` 
- **Windows**: `HKEY_CURRENT_USER\Software\mixcloud-bulk-downloader`
- **Linux**: `~/.config/mixcloud-bulk-downloader.conf`

To override the default location, set the `CUSTOM_SETTINGS_PATH` environment variable to a directory path. When set:
- QSettings will use `<CUSTOM_SETTINGS_PATH>/mixcloud-bulk-downloader.conf`
- Keyring credentials will be isolated using a custom service name
- The custom directory will be created automatically if it doesn't exist
- Both absolute and relative paths are supported (relative paths are resolved relative to the current working directory)
- Home directory expansion (`~`) is supported

**Examples:**
```bash
# Absolute path
export CUSTOM_SETTINGS_PATH="/opt/mixcloud-settings"

# Relative path (resolved from current directory)
export CUSTOM_SETTINGS_PATH="./config"

# Home directory
export CUSTOM_SETTINGS_PATH="~/Documents/MixcloudSettings"

# Portable drive (Windows example)
set CUSTOM_SETTINGS_PATH="D:\PortableApps\MixcloudSettings"
```

This is useful for:
- Portable installations on USB drives
- Multi-user environments requiring isolated settings
- Development and testing with separate configurations

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed via Poetry
2. **Qt Binding Issues**: Verify PySide6 is properly installed
3. **Download Failures**: Check yt-dlp version and network connectivity
4. **API Rate Limiting**: Implement proper request throttling

### Debugging

- Enable development mode logging for detailed output
- Check log files in `./logs/` directory
- Use Qt's built-in debugging tools for widget issues

## Future Enhancements

### Potential Improvements

- [ ] Implement proper logging throughout the application
- [ ] Improve error handling and user feedback
- [ ] Add download queue management
- [ ] Implement retry logic for failed downloads
- [ ] Add cloudcast metadata preservation

### Architecture Considerations

- Consider moving to async/await for API calls
- Implement proper dependency injection
- Add unit tests for core functionality
- Consider using Qt's Model/View architecture for large datasets

## Deployment

### Distribution Formats

- **macOS**: .app bundle + DMG installer
- **Windows**: Executable via PyInstaller
- **Linux**: AppImage or distribution packages

### Release Process

1. Update version in `pyproject.toml`
2. Update README.md with changes
3. Build application with PyInstaller
4. Create platform-specific installers
5. Test on target platforms
6. Tag release in version control

---

## Maintenance of This Document

**IMPORTANT**: This document must be kept current with the codebase.

### When to Update CLAUDE.md

This document **MUST** be updated whenever making:

#### **Architectural Changes**
- Adding/removing core modules or components
- Changing threading patterns or background operation flow
- Modifying API integration patterns
- Restructuring file organization
- Changing data flow between components

#### **Development Standard Changes**
- Updating code style guidelines or formatting rules
- Changing type hint conventions
- Modifying documentation requirements
- Adding new linting or testing tools
- Updating dependency management approach

#### **New Feature Categories**
- Adding new widget types or UI patterns
- Implementing new API endpoints or external integrations
- Creating new configuration or logging mechanisms
- Adding new build/deployment processes

### Update Process

1. **During Development**: Update relevant sections as you make changes
2. **Before Committing**: Review CLAUDE.md for accuracy against your changes
3. **In Pull Requests**: Include CLAUDE.md updates with architectural changes
4. **Document Why**: Explain reasoning behind architectural decisions

### Automated Reminders

When working on this project, AI assistants should:
- Check if changes affect architectural patterns described in CLAUDE.md
- Prompt for documentation updates when making significant changes
- Verify that new code follows the patterns documented here
- Update this document proactively, not just reactively

**Failure to maintain this document will lead to inconsistent development practices and technical debt.**

---

This guide should be updated as the project evolves. When making significant architectural changes, please update the relevant sections to maintain accuracy.