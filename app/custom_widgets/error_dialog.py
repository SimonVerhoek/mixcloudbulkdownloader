from PySide6.QtWidgets import QErrorMessage


class ErrorDialog(QErrorMessage):
    def __init__(self, parent, message: str, title: str = 'Error'):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.showMessage(message)
