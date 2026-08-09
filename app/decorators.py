"""Decorators for feature gating and pro functionality."""

from functools import wraps
from typing import Any, Callable, TypeVar

from PySide6.QtWidgets import QWidget

from app.services.license_manager import license_manager as _module_license_manager


F = TypeVar("F", bound=Callable[..., Any])

# Module-level alias exposed so callers that do ``from app.decorators import license_manager``
# still work, and so tests can reference ``app.decorators.license_manager`` when needed.
license_manager = _module_license_manager


def requires_pro(func: F = None, *, _license_manager=None, _dialog_factory=None):
    """Decorator to gate methods behind Pro license verification.

    Can be used as a bare decorator (``@requires_pro``) or as a parameterised
    decorator (``@requires_pro(_license_manager=my_lm)``).  The parameterised
    form is intended for testing only; production code should always use the
    bare form so the module-level singleton is used.

    Args:
        func: The function to decorate when used as a bare decorator.
        _license_manager: Optional license manager override (for tests).
        _dialog_factory: Optional callable that returns a GetProDialog-like
            instance (for tests).

    Returns:
        The decorated function that checks Pro status before execution.

    Example:
        @requires_pro
        def premium_feature(self):
            # This method only executes for Pro users
            return "Premium functionality"
    """

    def decorator(f: F) -> F:
        @wraps(f)
        def wrapper(*args, **kwargs):
            _lm = _license_manager if _license_manager is not None else license_manager
            if not _lm.is_pro:
                # For methods that need a return value, return None for graceful degradation
                # For UI methods, we could show an upgrade prompt here
                _show_upgrade_prompt_if_possible(args, dialog_factory=_dialog_factory)
                return None

            return f(*args, **kwargs)

        return wrapper

    # Support both ``@requires_pro`` and ``@requires_pro(_license_manager=...)``.
    if func is not None:
        # Called as a bare decorator: @requires_pro
        return decorator(func)
    # Called as a factory: @requires_pro(_license_manager=...)
    return decorator


def _show_upgrade_prompt_if_possible(
    args: tuple, *, dialog_factory: Callable | None = None
) -> None:
    """Show upgrade prompt if the first argument appears to be a widget.

    Args:
        args: Function arguments, first one might be self (widget instance).
        dialog_factory: Optional callable used to create the upgrade dialog.
            Defaults to GetProDialog.
    """
    if not args:
        return

    first_arg = args[0]

    # Check if first argument is a Qt widget
    if isinstance(first_arg, QWidget):
        try:
            from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog

            factory = dialog_factory or GetProDialog
            dialog = factory(first_arg)
            dialog.exec()
        except ImportError:
            # GetProDialog not available yet, silently ignore
            pass


def pro_feature_gate(feature_name: str = "this feature", *, _license_manager=None):
    """Decorator factory for pro feature gating with custom messages.

    Args:
        feature_name: Name of the feature for error messages.
        _license_manager: Optional license manager override (for tests).

    Returns:
        Decorator function that gates the feature.

    Example:
        @pro_feature_gate("advanced downloads")
        def download_with_custom_format(self):
            return "Advanced download functionality"
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            _lm = _license_manager if _license_manager is not None else license_manager
            if not _lm.is_pro:
                _show_feature_locked_message(args, feature_name)
                return None

            return func(*args, **kwargs)

        return wrapper

    return decorator


def _show_feature_locked_message(args: tuple, feature_name: str) -> None:
    """Show feature locked message with upgrade prompt.

    Args:
        args: Function arguments, first one might be self (widget instance)
        feature_name: Name of the locked feature
    """
    if not args:
        return

    first_arg = args[0]

    # Check if first argument is a Qt widget
    if isinstance(first_arg, QWidget):
        try:
            from PySide6.QtWidgets import QMessageBox

            from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog

            # Show info about the locked feature
            reply = QMessageBox.information(
                first_arg,
                "Pro Feature",
                f"{feature_name.title()} is a Pro-only feature.\n\nWould you like to upgrade to MBD Pro?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                dialog = GetProDialog(first_arg)
                dialog.exec()

        except ImportError:
            # Dependencies not available, silently ignore
            pass
