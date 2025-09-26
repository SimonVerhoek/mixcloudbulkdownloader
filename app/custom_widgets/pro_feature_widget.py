"""Base widget class for Pro-only features with consistent styling and behavior."""

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from app.services.license_manager import LicenseManager, license_manager


class ProFeatureWidget:
    """Mixin class for widgets that contain pro-only features.

    This class provides consistent styling and behavior for Pro features:
    - Automatic enabling/disabling based on license status
    - Lock icons and tooltips for free users
    - Upgrade prompts when features are accessed
    - Real-time updates when license status changes

    Note: This is a mixin class and should be used with multiple inheritance
    along with a QWidget-derived class.
    """

    def __init__(
        self, license_manager: LicenseManager = license_manager, parent: QWidget | None = None
    ):
        """Initialize the Pro feature widget.

        Args:
            license_manager: License manager instance for Pro status checking
            parent: Parent widget (ignored, should be handled by main widget class)
        """
        # Don't call super().__init__ since this is a mixin
        self.license_manager = license_manager
        self._pro_widgets: list[QWidget] = []
        self._lock_labels: list[QLabel] = []
        self._setup_pro_gating()
        self._connect_license_signals()

    def _setup_pro_gating(self) -> None:
        """Set up pro feature visibility and styling based on license status."""
        if not self.license_manager.is_pro:
            self._show_upgrade_prompt_ui()
        else:
            self._enable_pro_features()

    def _connect_license_signals(self) -> None:
        """Connect to license status change signals for real-time updates."""
        self.license_manager.license_status_changed.connect(self._on_license_status_changed)

    def _show_upgrade_prompt_ui(self) -> None:
        """Show upgrade prompt UI elements for non-pro users."""
        self._disable_pro_widgets()
        self._add_lock_icons_and_tooltips()

    def _enable_pro_features(self) -> None:
        """Enable full pro feature set for licensed users."""
        self._enable_pro_widgets()
        self._remove_lock_icons()

    def _disable_pro_widgets(self) -> None:
        """Apply disabled styling to pro widgets using object names for QSS."""
        for widget in self._pro_widgets:
            widget.setEnabled(False)
            widget.setObjectName("proFeatureDisabled")

    def _enable_pro_widgets(self) -> None:
        """Enable and restore normal styling to pro widgets."""
        for widget in self._pro_widgets:
            widget.setEnabled(True)
            widget.setObjectName("")  # Remove styling object name

    def _add_lock_icons_and_tooltips(self) -> None:
        """Add lock icons with friendly tooltips for pro features."""
        tooltip_text = "🔒 Upgrade to MBD Pro to unlock this feature"

        for widget in self._pro_widgets:
            # Create lock icon label
            lock_label = QLabel("🔒")
            lock_label.setObjectName("proFeatureLockIcon")
            lock_label.setToolTip(tooltip_text)
            # Use a proper lambda that captures the current state
            lock_label.mousePressEvent = lambda event, self=self: self._show_upgrade_dialog()

            # Try multiple strategies to place the lock icon
            icon_placed = False

            # Strategy 1: If widget parent has an HBoxLayout, add to it
            if widget.parent() and hasattr(widget.parent(), "layout"):
                parent_layout = widget.parent().layout()
                if isinstance(parent_layout, QHBoxLayout):
                    parent_layout.addWidget(lock_label)
                    self._lock_labels.append(lock_label)
                    icon_placed = True

            # Strategy 2: If widget has a direct sibling area, create wrapper
            if not icon_placed and widget.parent():
                # Create a horizontal layout to hold widget + lock icon
                wrapper = QWidget()
                wrapper_layout = QHBoxLayout(wrapper)
                wrapper_layout.setContentsMargins(0, 0, 0, 0)
                wrapper_layout.setSpacing(5)

                # Move the original widget to wrapper and add lock
                original_parent = widget.parent()
                widget.setParent(wrapper)
                wrapper_layout.addWidget(widget)
                wrapper_layout.addWidget(lock_label)

                # Replace widget in its original location with wrapper
                if hasattr(original_parent, "layout") and original_parent.layout():
                    layout = original_parent.layout()
                    if hasattr(layout, "replaceWidget"):
                        layout.replaceWidget(widget, wrapper)
                        icon_placed = True
                        self._lock_labels.append(lock_label)

            # Strategy 3: Fallback - set lock as text prefix (visual indicator only)
            if not icon_placed:
                original_text = widget.text() if hasattr(widget, "text") else ""
                if hasattr(widget, "setText") and original_text:
                    widget.setText(f"🔒 {original_text}")

            # Always set tooltip on the widget itself
            widget.setToolTip(tooltip_text)

    def _remove_lock_icons(self) -> None:
        """Remove lock icons when pro features are enabled."""
        for lock_label in self._lock_labels:
            lock_label.setParent(None)
            lock_label.deleteLater()
        self._lock_labels.clear()

        # Remove tooltips and text prefix from widgets
        for widget in self._pro_widgets:
            widget.setToolTip("")
            # Remove lock prefix from text if it was added as fallback
            if hasattr(widget, "text") and hasattr(widget, "setText"):
                text = widget.text()
                if text.startswith("🔒 "):
                    widget.setText(text[2:])  # Remove "🔒 " prefix

    def _show_upgrade_dialog(self) -> None:
        """Show upgrade dialog when user tries to access locked feature."""
        try:
            from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog

            dialog = GetProDialog(self)
            dialog.exec()
        except ImportError:
            # GetProDialog not available, show simple message
            QMessageBox.information(
                self,
                "Pro Feature",
                "This is a Pro-only feature.\n\nUpgrade to MBD Pro to unlock advanced functionality.",
                QMessageBox.StandardButton.Ok,
            )

    @Slot()
    def _on_license_status_changed(self) -> None:
        """Handle license status changes and update UI accordingly."""
        if self.license_manager.is_pro:
            self._enable_pro_features()
        else:
            self._show_upgrade_prompt_ui()

    def register_pro_widget(self, widget: QWidget) -> None:
        """Register a widget as a Pro-only feature.

        Args:
            widget: Widget that should be gated behind Pro license
        """
        if widget not in self._pro_widgets:
            self._pro_widgets.append(widget)

        # Apply current pro status to the newly registered widget
        if not self.license_manager.is_pro:
            widget.setEnabled(False)
            widget.setObjectName("proFeatureDisabled")
            tooltip_text = "🔒 Upgrade to MBD Pro to unlock this feature"
            widget.setToolTip(tooltip_text)
        else:
            widget.setEnabled(True)
            widget.setObjectName("")
            widget.setToolTip("")

    def unregister_pro_widget(self, widget: QWidget) -> None:
        """Unregister a widget from Pro-only features.

        Args:
            widget: Widget to remove from Pro gating
        """
        if widget in self._pro_widgets:
            self._pro_widgets.remove(widget)
            widget.setEnabled(True)
            widget.setObjectName("")
            widget.setToolTip("")


# The ProFeatureMixin functionality is now merged into the main ProFeatureWidget class
