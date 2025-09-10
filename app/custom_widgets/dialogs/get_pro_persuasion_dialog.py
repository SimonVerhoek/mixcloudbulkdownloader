"""Pro persuasion dialog widget for encouraging users to upgrade to Pro after download completion."""

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.consts import PRO_FEATURES_LIST, PRO_PRICE_TEXT, STRIPE_CHECKOUT_URL
from app.qt_logger import log_error
from app.services.license_manager import license_manager


class GetProPersuasionDialog(QDialog):
    """Dialog that persuades users to upgrade to Pro after successful downloads.

    This dialog appears after downloads complete and showcases Pro features
    to encourage users to upgrade. Only shown to free users (not Pro users).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the persuasion dialog.

        Args:
            parent: Parent widget for the dialog
        """
        super().__init__(parent)

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
            "Want to download even faster with premium features?\n\n"
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
            webbrowser.open(STRIPE_CHECKOUT_URL)
        except Exception as e:
            log_error(message=f"Failed to open browser for Pro checkout: {e}")
        finally:
            self.accept()

    def _handle_no_thanks(self) -> None:
        """Handle the no thank you button click by dismissing the dialog."""
        self.reject()

    @staticmethod
    def should_show() -> bool:
        """Determine if the Pro persuasion dialog should be shown.

        Returns:
            bool: True if dialog should be shown (user is not Pro), False otherwise.
        """
        return not license_manager.is_pro
