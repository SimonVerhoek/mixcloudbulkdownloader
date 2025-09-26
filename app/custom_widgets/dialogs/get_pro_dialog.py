"""GetPro dialog for license verification and Pro feature showcase."""

import re
import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.consts.license import (
    LICENSE_CHECKOUT_ERROR,
    LICENSE_INVALID_CREDENTIALS,
    LICENSE_VERIFICATION_FAILED,
    PRO_FEATURES_LIST,
    PRO_PRICE_TEXT,
)
from app.consts.ui import (
    GET_PRO_DIALOG_HEIGHT,
    GET_PRO_DIALOG_WIDTH,
)
from app.custom_widgets.dialogs.error_dialog import ErrorDialog
from app.custom_widgets.dialogs.license_verification_failure_dialog import (
    LicenseVerificationFailureDialog,
)
from app.custom_widgets.dialogs.license_verification_success_dialog import (
    LicenseVerificationSuccessDialog,
)
from app.qt_logger import log_error
from app.services.license_manager import license_manager


class GetProDialog(QDialog):
    """Dialog for license verification and Pro features showcase.

    This dialog provides two main sections:
    1. License verification form for existing Pro users
    2. Pro features showcase with purchase option for new users
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the GetPro dialog.

        Args:
            parent: Parent widget for the dialog.
        """
        super().__init__(parent)

        self.setWindowTitle("Get MBD Pro")
        self.setModal(True)
        self.setObjectName("getProDialog")

        # Set dialog dimensions
        self.setFixedSize(GET_PRO_DIALOG_WIDTH, GET_PRO_DIALOG_HEIGHT)

        self._setup_ui()
        self._connect_signals()
        self._load_existing_credentials()

    def _setup_ui(self) -> None:
        """Set up the dialog user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # License verification section
        verification_section = self._create_verification_section()
        main_layout.addWidget(verification_section)

        main_layout.addSpacing(10)

        # Pro features section
        features_section = self._create_features_section()
        main_layout.addWidget(features_section)

    def _create_verification_section(self) -> QWidget:
        """Create the license verification form section.

        Returns:
            QWidget: Widget containing the verification form.
        """
        section = QWidget()
        layout = QVBoxLayout(section)

        # Section title
        title = QLabel("Already have MBD Pro? Enter your credentials:")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # Email field with label and input
        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        email_label.setObjectName("formLabel")
        self.email_edit = QLineEdit()
        self.email_edit.setObjectName("emailEdit")
        self.email_edit.setPlaceholderText("Enter your license email")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_edit)

        # License key field with label and input
        license_key_layout = QHBoxLayout()
        license_key_label = QLabel("License Key:")
        license_key_label.setObjectName("formLabel")
        self.license_key_edit = QLineEdit()
        self.license_key_edit.setObjectName("licenseKeyEdit")
        self.license_key_edit.setPlaceholderText("Enter your license key")
        license_key_layout.addWidget(license_key_label)
        license_key_layout.addWidget(self.license_key_edit)

        # Verify button positioned to the right
        self.verify_button = QPushButton("Verify License")
        self.verify_button.setObjectName("primaryButton")

        verify_button_layout = QHBoxLayout()
        verify_button_layout.addStretch()  # Push button to the right
        verify_button_layout.addWidget(self.verify_button)

        layout.addLayout(email_layout)
        layout.addLayout(license_key_layout)
        layout.addLayout(verify_button_layout)

        return section

    def _create_features_section(self) -> QWidget:
        """Create the Pro features showcase section.

        Returns:
            QWidget: Widget containing the features showcase.
        """
        section = QWidget()
        layout = QVBoxLayout(section)

        # Section title
        title = QLabel("New to MBD Pro? Here's what you get:")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # Features list
        features_text = "\n".join([f"• {feature}" for feature in PRO_FEATURES_LIST])
        features_label = QLabel(features_text)
        features_label.setObjectName("featureList")
        features_label.setWordWrap(True)
        features_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        features_label.setMinimumHeight(120)  # Ensure enough space for all 4 features
        layout.addWidget(features_label)

        # Pricing
        price_label = QLabel(PRO_PRICE_TEXT)
        price_label.setObjectName("priceText")
        price_label.setWordWrap(True)
        price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(price_label)

        # Purchase button
        self.get_pro_now_button = QPushButton("Get MBD Pro now")
        self.get_pro_now_button.setObjectName("primaryButton")
        layout.addWidget(self.get_pro_now_button)

        return section

    def _connect_signals(self) -> None:
        """Connect button signals to their respective handlers."""
        self.verify_button.clicked.connect(self._handle_verify)
        self.get_pro_now_button.clicked.connect(self._handle_get_pro_now)

    def _load_existing_credentials(self) -> None:
        """Load existing credentials from settings into the form."""
        self.email_edit.setText(license_manager.settings.email)
        self.license_key_edit.setText(license_manager.settings.license_key)

    def _validate_form(self) -> bool:
        """Validate the license verification form.

        Returns:
            bool: True if form is valid, False otherwise.
        """
        email = self.email_edit.text().strip()
        license_key = self.license_key_edit.text().strip()

        # Check required fields
        if not email or not license_key:
            return False

        # Basic email format validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return False

        return True

    def _handle_verify(self) -> None:
        """Handle the verify license button click."""
        if not self._validate_form():
            failure_dialog = LicenseVerificationFailureDialog(self, LICENSE_INVALID_CREDENTIALS)
            failure_dialog.exec()
            return

        email = self.email_edit.text().strip()
        license_key = self.license_key_edit.text().strip()

        # Store credentials before verification
        license_manager.settings.email = email
        license_manager.settings.license_key = license_key

        # Perform verification
        success = license_manager.verify_license()

        if success:
            success_dialog = LicenseVerificationSuccessDialog(self)
            success_dialog.exec()
            self.accept()  # Close GetPro dialog
        else:
            failure_dialog = LicenseVerificationFailureDialog(self, LICENSE_VERIFICATION_FAILED)
            failure_dialog.exec()
            # Keep GetPro dialog open for retry

    def _handle_get_pro_now(self) -> None:
        """Handle the Get MBD Pro now button click."""
        try:
            checkout_url = license_manager.get_checkout_url()
            webbrowser.open(checkout_url)
        except Exception as e:
            log_error(message=f"Failed to retrieve checkout URL: {e}")
            error_dialog = ErrorDialog(self, LICENSE_CHECKOUT_ERROR, "Checkout Error")
            error_dialog.exec()
        # Keep dialog open so user can enter credentials after purchase
