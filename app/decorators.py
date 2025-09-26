"""Decorators for feature gating and pro functionality."""

from functools import wraps
from typing import Any, Callable, TypeVar

from app.services.license_manager import license_manager


F = TypeVar("F", bound=Callable[..., Any])


def requires_pro(func: F) -> F:
    """Decorator to gate methods behind Pro license verification.

    This decorator checks if the user has a valid Pro license before
    executing the decorated method. If not Pro, it shows an upgrade prompt
    or returns None for graceful degradation.

    Args:
        func: The function to decorate

    Returns:
        The decorated function that checks Pro status before execution

    Example:
        @requires_pro
        def premium_feature(self):
            # This method only executes for Pro users
            return "Premium functionality"
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not license_manager.is_pro:
            # For methods that need a return value, return None for graceful degradation
            # For UI methods, we could show an upgrade prompt here
            _show_upgrade_prompt_if_possible(args)
            return None

        return func(*args, **kwargs)

    return wrapper


def _show_upgrade_prompt_if_possible(args: tuple) -> None:
    """Show upgrade prompt if the first argument appears to be a widget.

    Args:
        args: Function arguments, first one might be self (widget instance)
    """
    if not args:
        return

    first_arg = args[0]

    # Check if first argument looks like a Qt widget (has a parent method/attribute)
    if hasattr(first_arg, "parent") and callable(getattr(first_arg, "parent", None)):
        try:
            from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog

            dialog = GetProDialog(first_arg)
            dialog.exec()
        except ImportError:
            # GetProDialog not available yet, silently ignore
            pass


def pro_feature_gate(feature_name: str = "this feature"):
    """Decorator factory for pro feature gating with custom messages.

    Args:
        feature_name: Name of the feature for error messages

    Returns:
        Decorator function that gates the feature

    Example:
        @pro_feature_gate("advanced downloads")
        def download_with_custom_format(self):
            return "Advanced download functionality"
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not license_manager.is_pro:
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

    # Check if first argument looks like a Qt widget
    if hasattr(first_arg, "parent") and callable(getattr(first_arg, "parent", None)):
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
