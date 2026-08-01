"""First-run consent dialog for automatic error reporting."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ErrorReportingConsentDialog(QDialog):
    """First-run dialog asking the user to consent to automatic error reporting.

    Displayed once on first launch. The user's choice is persisted via
    SettingsManager and controls whether Sentry events are forwarded.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the consent dialog.

        Args:
            parent: Parent widget for the dialog.
        """
        super().__init__(parent)

        self.setWindowTitle("Help improve Mixcloud Bulk Downloader")
        self.setModal(True)
        self.setObjectName("errorReportingConsentDialog")
        self.setFixedWidth(480)

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Body text
        body = QLabel(
            "When errors occur, Mixcloud Bulk Downloader can automatically send a report to the "
            "developer. This greatly helps in diagnosing and fixing issues.\n\n"
            "Each report includes the error message and stack trace, recent log entries, "
            "and device information (OS, version, processor type).\n\n"
            "Your IP address and system username are never included. Log entries may reference cloudcast names and partial file paths.\n\n"
            "You can change this at any time in Settings \u2192 Error Reporting."
        )
        body.setWordWrap(True)
        body.setObjectName("consentBodyLabel")
        body.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.no_button = QPushButton("No thanks")
        self.no_button.setObjectName("secondaryButton")
        self.no_button.clicked.connect(self.reject)

        self.yes_button = QPushButton("Yes, send reports (Recommended)")
        self.yes_button.setObjectName("primaryButton")
        self.yes_button.setDefault(True)
        self.yes_button.clicked.connect(self.accept)

        button_layout.addWidget(self.no_button)
        button_layout.addWidget(self.yes_button)

        layout.addWidget(body)
        layout.addLayout(button_layout)

        self.setLayout(layout)
