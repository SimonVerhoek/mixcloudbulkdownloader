"""Error dialog widget for displaying error messages to the user."""

from PySide6.QtWidgets import QErrorMessage, QWidget


class ErrorDialog(QErrorMessage):
    """Simple error dialog for displaying error messages.

    This dialog provides a consistent way to show error messages throughout
    the application with an optional custom title.
    """

    def __init__(self, parent: QWidget | None, message: str, title: str = "Error") -> None:
        """Initialize and display the error dialog.

        Args:
            parent: Parent widget for the dialog
            message: Error message to display
            title: Dialog window title (defaults to "Error")
        """
        super().__init__(parent)

        self.setWindowTitle(title)
        self.showMessage(message)
