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
- **app/logger.py**: Qt-free logging module — owns all logging configuration and convenience functions; safe to import in any layer
- **app/qt_logger.py**: Thin Qt adapter — captures Qt framework messages only; imported solely in `main.py`

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
- **Import Placement**: **ALL** imports must be placed at the top of the module after docstrings and before any other code. **No inline imports are permitted** — not for platform-conditional logic, optional dependencies, or circular-dependency workarounds. If a circular dependency forces a late import, that is a design signal: extract a shared interface/protocol or inject the dependency via constructor or method parameter instead. This ensures better performance, clearer dependencies, and easier static analysis.
- **File Path Handling**: **ALWAYS** use `pathlib.Path` for file path operations instead of `os.path` when possible. This provides better cross-platform compatibility, more readable code, and modern Python best practices. Use `Path` objects for path construction, joining, existence checks, and file operations.
- **Explicit Parameter Names**: **ALWAYS** use explicit parameter names in function and method calls (`function(param1=value1, param2=value2)`) instead of positional arguments (`function(value1, value2)`). This improves code readability, maintainability, and reduces errors when function signatures change. 

**Exceptions:**
  - Built-in functions and very common operations where positional arguments are conventional (e.g., `len(items)`, `str(value)`)
  - Methods/functions that do not accept keyword arguments (e.g., `QTimer.singleShot()`, some Qt methods)
  - When the API documentation explicitly states positional-only parameters
- **Environment Variables**: Always use `environs` (`from environs import env`) for reading environment variables. Never use `os.getenv()` directly. Declare env var constants in `app/consts/settings.py` using `env.str()`, `env.bool()`, etc., so all env var access is centralised and consistently typed.

  **Exception — OS-standard platform env vars**: `APPDATA`, `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, `USER`, and `USERNAME` are OS-defined path/identity variables, not app config. Using `os.getenv()` with a sensible fallback is the idiomatic Python approach for these and routing them through `environs` adds no value. All other env vars that represent app behaviour or configuration **must** go through `app/consts/settings.py`.

### Styling Guidelines

- **QSS Files**: All styling should be defined in `.qss` files in `./app/styles/`
- **Modular Styling**: Modularize QSS files by component type (`buttons.qss`, `labels.qss`, `dialogs.qss`, etc.)
- **No Inline Styles**: Avoid inline `setStyleSheet()` calls in widget code when possible
- **Component-Based Organization**: Group related styles in dedicated files for maintainability

### Error Handling and Logging

- **Always Log Exceptions**: All exceptions should be logged using the configured logging system
- **Prefer Logging**: Always choose logging over print statements for debugging and error reporting
- **Use Appropriate Log Levels**: Use `log_error()`, `log_api()`, `log_ui()` functions from `app.logger` (never from `app.qt_logger`)
- **Structured Error Messages**: Use error message constants from `app/consts.py` for consistency

### File Organization

```
app/
├── __init__.py
├── consts.py              # Application constants
├── data_classes.py        # Data models
├── api.py                 # Mixcloud API functions
├── logger.py              # Qt-free logging (convenience functions + file handler setup)
├── qt_logger.py           # Qt adapter (Qt message capture only; imported only in main.py)
├── threads.py             # Background threading classes
└── custom_widgets/        # Qt custom widgets
    ├── __init__.py
    ├── cloudcast_q_tree_widget.py
    ├── cloudcast_q_tree_widget_item.py
    ├── search_user_q_combo_box.py
    ├── user_q_list_widget_item.py
    └── error_dialog.py
```

### Logging Architecture

The logging system is split into two modules to enforce the Qt boundary rule:

- **`app/logger.py`** — Qt-free. Configures Python's standard `logging` module, owns all
  convenience functions (`log_api`, `log_ui`, `log_download`, `log_thread`, `log_error`,
  `log_error_with_traceback`, `log_exception`), and detects the platform-appropriate log
  directory. **Import this module in all layers** (logic, services, UI, threads).

- **`app/qt_logger.py`** — Qt adapter only. Calls `logger.configure()` once (after
  `QApplication` exists) and installs `qInstallMessageHandler` to route Qt's own internal
  messages into the `qt` Python logger. **Only `main.py` should import from this module.**

This separation means that services, API clients, and utilities never transitively pull in
PySide6, keeping them fully testable without a running `QApplication`.

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

### Testing Philosophy & Mocking Rules

#### Rule 1 — No `@patch`: use dependency injection instead

`@patch` is **forbidden in all test files**. Even for external systems, dependency injection and
handwritten stubs produce cleaner, more refactor-safe tests. The `scripts/check_mock_rules.py`
script enforces this at pre-commit time.

**Replace every `@patch` with injection — use these alternatives:**

| Old `@patch` use | Replacement |
|---|---|
| `@patch("app.api.httpx.get")` | Inject `httpx.Client`; use `httpx.MockTransport` or a `StubHttpClient` stub |
| `@patch("app.X.yt_dlp.YoutubeDL")` | Inject `YoutubeDL` class/factory; write `StubYoutubeDL` |
| `@patch("sys.platform")` / `@patch("platform.system")` | Accept platform string as a parameter: `def foo(platform: str = sys.platform)` |
| `@patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory")` | Wrap in an injectable callable; pass `dir_picker: Callable` to the widget |
| `@patch("app.X.QMetaObject.invokeMethod")` | Override in a test subclass or inject the invoker |
| Your own functions or classes | Accept the dependency as a constructor/method parameter |
| `Path` or any stdlib type | Accept the resolved path as a parameter (e.g. `home_dir: Path`) |
| Module-level singletons (`settings`, `license_manager`) | Inject via constructor |
| Configuration constants (`DEVELOPMENT`) | Pass as a parameter where possible |

#### Rule 2 — Internal patch = design signal

If you find yourself wanting to patch something internal, stop and ask why:

| What you want to patch | What it signals | Fix |
|---|---|---|
| `module.Path` to avoid `Path.home()` | Path is hardcoded; not injected | Accept the path as a parameter |
| `module.get_ffmpeg_path` called inside a method | Dependency not injectable | Accept `ffmpeg_path: Path` as a constructor or method param |
| `module.get_appdata_dir` / `get_xdg_config_home` | Platform helpers hardcoded inside logic | Accept a `storage_path: Path` param instead |
| `module.CredentialEncryptor` class | Collaborator is hardcoded in `__init__` | Inject via constructor (`encryptor: CredentialEncryptor`) |
| `module.settings` singleton | Module-level import instead of injection | Accept `settings_manager: SettingsManager` as a parameter |
| `module.StartupVerificationThread` | Thread created directly instead of via factory | Accept an optional thread factory or use a test subclass |

#### Rule 3 — Test double hierarchy

When you need a stand-in for a dependency, prefer in order:

1. **Real object** — use the real implementation when it is fast and has no side effects
2. **Handwritten fake / stub** — a minimal class implementing the same interface with
   controlled behaviour; readable and refactor-safe
3. **`unittest.mock.MagicMock` / `create_autospec`** — for unimportant collaborators
   where you only need call verification
4. **`@patch`** — only for external boundaries (Rule 1)

Never use `@patch` to replace an internal collaborator with a `MagicMock`. Write a stub instead.

#### Rule 6 — Mock instances must always carry a spec

Never instantiate a mock without telling it what it represents:

```python
# Bad — silently accepts any attribute or call, hides interface drift
m = Mock()
m = MagicMock()

# Good — raises AttributeError for attributes that don't exist on the real class
m = Mock(spec=SettingsManager)
m = MagicMock(spec=SettingsManager)

# Best — also validates call signatures (argument names and counts)
m = create_autospec(SettingsManager)
m = create_autospec(SettingsManager, instance=True)
```

**Why it matters:** a spec-less mock will happily return another mock for any attribute you
typo or that no longer exists on the real class. `spec=` turns those silent successes into
`AttributeError`, catching regressions at test time instead of production time.

**Preference order within mocks:**
1. `create_autospec(RealClass, instance=True)` — validates both attributes and call signatures
2. `Mock(spec=RealClass)` / `MagicMock(spec=RealClass)` — validates attributes only
3. Never: `Mock()` / `MagicMock()` without `spec`

#### Rule 7 — Inject values, not callables, for pure functions

When the goal is to make a pure function's result controllable in tests, inject the
**resolved value**, not the callable itself:

```python
# Bad — callable injection for a pure function; no external side effect
def cleanup_partial_files(
    ...,
    time_fn: Callable[[], float] | None = None,
)

# Good — value injection; matches existing CredentialEncryptor pattern
def cleanup_partial_files(
    ...,
    now: float | None = None,
)
```

Callable injection is reserved for genuine external boundaries:
- Spawning OS processes: `popen_fn` → `subprocess.Popen`
- Third-party library entry points: `ydl_class` → `yt_dlp.YoutubeDL`
- Framework infrastructure: `invoke_method_fn` → `QMetaObject.invokeMethod`
- Simulating OS-level errors (e.g. `PermissionError` on file deletion) where real
  `os.chmod` manipulation is fragile and platform-dependent: `remove_fn`

Do **not** inject callables for pure stdlib functions (`time.time`, `uuid.uuid4`,
`os.getcwd`, `open`, `sleep`, etc.). Pass the computed value instead.

#### Rule 8 — Use `T = real_default` instead of `T | None = None` for injectable parameters

When a DI parameter has a production default that is stable and safe to evaluate at
module-load time, express it directly rather than using `None` as a sentinel:

```python
# Bad — type is a lie (param is never None at runtime); adds resolution boilerplate
def __init__(self, popen_fn: Callable | None = None):
    _popen = popen_fn if popen_fn is not None else subprocess.Popen
    result = _popen(...)

# Good — honest type, simpler body
def __init__(self, popen_fn: Callable = subprocess.Popen):
    result = popen_fn(...)
```

Keep `T | None = None` only when the real default **cannot** be expressed at definition time:
- It must be called at call time: `now: float | None = None` (defaults to `time.time()`)
- It depends on runtime context: `storage_path: Path | None = None` (env-var path)
- It is a module-level singleton not ready at import time: `settings: SettingsManager | None = None`
- It requires lazy import to avoid circular dependencies
- Calling it at import time may raise (e.g. `ffmpeg_path` defaulting to `get_ffmpeg_path()`)

#### Rule 9 — No `hasattr()` or `getattr()` — use explicit typing instead

Both functions return `Any` or `bool` without narrowing the type, defeating static analysis:

| Pattern | Replacement |
|---|---|
| `if hasattr(self, "x"):` where `x` may not be set | Declare `x: T \| None = None` in `__init__`; check `if self.x is not None:` |
| `if hasattr(obj, "method"):` to test an interface | `isinstance(obj, ExpectedType)` or a `@runtime_checkable Protocol` |
| `getattr(self, name)` in dynamic iteration | Use `vars(self).items()` or a private `dict` registry |
| Duck-typing widget detection via `hasattr(x, "parent")` | `isinstance(x, QWidget)` |
| Singleton guard `hasattr(cls, "_instance")` | Declare `_instance: T \| None = None` class var; check `if cls._instance is None:` |

**Exception:** Runtime-injected markers from PyInstaller (`sys._MEIPASS`, `sys.frozen`) that
genuinely do not exist at static analysis time. Keep `getattr`/`hasattr` for these, and annotate
with `# type: ignore[attr-defined]`.

**Scope — production code only.** Rule 9 targets production code where type narrowing matters
for correctness. In test code the following guidance applies instead:

| Test usage | Guidance |
|---|---|
| `assert not hasattr(obj, "attr")` — negative attribute check | **Allowed** — no clean, readable alternative exists |
| `assert hasattr(obj, "attr")` followed immediately by direct access | **Forbidden** — the direct access already proves existence; drop the `hasattr` |
| `if hasattr(widget, "text"):` type guard in a test helper | **Prefer `isinstance`** — more specific, catches renames |
| `assert hasattr(obj, "method")` standalone callable check | **Prefer `assert callable(obj.method)`** — more specific |

#### Rule 4 — Never patch `Path` or other stdlib types inside app modules

If a function calls `Path.home()`, `Path(__file__).parent`, or similar, the fix is to accept the
resolved path as a parameter:

```python
# Instead of patching Path inside credential_encryptor:
def get_device_salt(home_dir: Path = Path.home()) -> bytes: ...

# Instead of patching Path inside settings_manager:
class SettingsManager:
    def __init__(self, storage_path: Path | None = None): ...
```

Tests then pass a known `tmp_path` fixture path. No patching required.

#### Rule 5 — Use `caplog` for log assertions, not `@patch`

Do not patch `log_ui`, `log_error`, or similar logging functions to verify they were called.
Use pytest's built-in `caplog` fixture instead:

```python
def test_logs_warning(caplog):
    with caplog.at_level(logging.WARNING):
        do_something()
    assert "expected message" in caplog.text
```

#### Acceptable exceptions

The `scripts/check_mock_rules.py` script flags every `patch()` call. The only acceptable
exception is `patch.object()` used on a **test-provided instance** (not a production import)
to adjust a single attribute — and only when no injection point exists. Document the reason
inline with a comment.


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
