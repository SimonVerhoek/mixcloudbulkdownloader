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

```bash
# Create executable with PyInstaller
pyinstaller --clean -y app.spec

# macOS DMG creation (requires create-dmg)
create-dmg dist/Mixcloud\ Bulk\ Downloader.app
```

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

### Application Settings

Key configuration values are stored in `app/consts.py`:
- Window dimensions and layout ratios
- API URLs and endpoints
- File extensions and paths
- Error messages and user-facing text

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