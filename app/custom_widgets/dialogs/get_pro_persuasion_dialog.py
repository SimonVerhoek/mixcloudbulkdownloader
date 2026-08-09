"""Pro persuasion dialog widget for encouraging users to upgrade to Pro after download completion."""

import webbrowser
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

import app.services.license_manager as _lm_module
from app.consts.license import LICENSE_CHECKOUT_ERROR, PRO_FEATURES_LIST, PRO_PRICE_TEXT
from app.custom_widgets.dialogs.error_dialog import ErrorDialog
from app.logger import log_error
from app.services.license_manager import LicenseManager, license_manager


class GetProPersuasionDialog(QDialog):
    """Dialog that persuades users to upgrade to Pro after successful downloads.

    This dialog appears after downloads complete and showcases Pro features
    to encourage users to upgrade. Only shown to free users (not Pro users).
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        license_manager: LicenseManager | None = None,
        browser_open_fn: Callable | None = None,
        error_dialog_factory: Callable | None = None,
    ) -> None:
        """Initialize the persuasion dialog.

        Args:
            parent: Parent widget for the dialog
            license_manager: License manager instance to use. If None, uses the module-level singleton.
            browser_open_fn: Callable used to open URLs in a browser. Defaults to webbrowser.open.
            error_dialog_factory: Callable used to construct error dialogs. Defaults to ErrorDialog.
        """
        super().__init__(parent)
        self._license_manager = (
            license_manager if license_manager is not None else _lm_module.license_manager
        )
        self._browser_open_fn = browser_open_fn or webbrowser.open
        self._error_dialog_factory = error_dialog_factory or ErrorDialog

        self.setWindowTitle("Upgrade to MBD Pro")
        self.setModal(True)
        self.setObjectName("proPersuasionDialog")

        self._setup_ui()
        self._connect_signals()

        # Auto-size the dialog to fit content, then fix the size
        self.adjustSize()
        self.setFixedSize(self.size())

    def _setup_ui(self) -> None:
        """Set up the dialog user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Success message
        success_label = QLabel("🎉 Your downloads have completed successfully!")
        success_label.setObjectName("successLabel")
        success_label.setWordWrap(True)
        success_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(success_label)

        # Pro features message
        pro_message = QLabel(
            "Want to download in higher quality and other formats?\n\n"
            "Upgrade to MBD Pro and unlock:"
        )
        pro_message.setWordWrap(True)
        pro_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(pro_message)

        # Feature list
        features_text = "\n".join([f"• {feature}" for feature in PRO_FEATURES_LIST])
        features_label = QLabel(features_text)
        features_label.setObjectName("featureList")
        features_label.setWordWrap(True)
        features_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(features_label)

        # Pricing
        price_label = QLabel(PRO_PRICE_TEXT)
        price_label.setObjectName("priceTextTop")
        price_label.setWordWrap(True)
        price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(price_label)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # No thank you button (left side)
        self.no_thanks_button = QPushButton("No thank you")
        self.no_thanks_button.setObjectName("secondaryButton")
        self.no_thanks_button.setFixedHeight(40)
        self.no_thanks_button.setMinimumWidth(120)
        button_layout.addWidget(self.no_thanks_button)

        # Get Pro button (right side)
        self.get_pro_button = QPushButton("Get Pro")
        self.get_pro_button.setObjectName("primaryButton")
        self.get_pro_button.setFixedHeight(40)
        self.get_pro_button.setMinimumWidth(120)
        button_layout.addWidget(self.get_pro_button)

        layout.addLayout(button_layout)

    def _connect_signals(self) -> None:
        """Connect button signals to their respective handlers."""
        self.get_pro_button.clicked.connect(self._handle_get_pro)
        self.no_thanks_button.clicked.connect(self._handle_no_thanks)

    def _handle_get_pro(self) -> None:
        """Handle the Get Pro button click by opening the checkout URL."""
        try:
            checkout_url = self._license_manager.get_checkout_url()
            self._browser_open_fn(checkout_url)
        except Exception as e:
            log_error(message=f"Failed to retrieve checkout URL: {e}")
            error_dialog = self._error_dialog_factory(
                self, LICENSE_CHECKOUT_ERROR, "Checkout Error"
            )
            error_dialog.exec()
        finally:
            self.accept()

    def _handle_no_thanks(self) -> None:
        """Handle the no thank you button click by dismissing the dialog."""
        self.reject()

    @staticmethod
    def should_show(license_manager_fn: Callable | None = None) -> bool:
        """Determine if the Pro persuasion dialog should be shown.

        Args:
            license_manager_fn: Optional callable that returns the license manager to use.
                Defaults to the module-level singleton.

        Returns:
            bool: True if dialog should be shown (user is not Pro), False otherwise.
        """
        _lm = license_manager_fn() if license_manager_fn is not None else _lm_module.license_manager
        return not _lm.is_pro
