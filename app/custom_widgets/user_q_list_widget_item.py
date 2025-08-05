"""List widget item for displaying Mixcloud users."""

from PySide6.QtWidgets import QListWidgetItem

from app.data_classes import MixcloudUser


class UserQListWidgetItem(QListWidgetItem):
    """List widget item representing a Mixcloud user.

    This item displays user information in a list widget with the format
    "Display Name (username)" and stores the user data for reference.
    """

    def __init__(self, user: MixcloudUser) -> None:
        """Initialize the list item with user data.

        Args:
            user: MixcloudUser data to display in this item
        """
        super().__init__(f"{user.name} ({user.username})")

        self.user = user
