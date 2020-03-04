from typing import Dict

from PySide2.QtWidgets import QListWidgetItem


class UserQListWidgetItem(QListWidgetItem):
    def __init__(
        self, key: str, name: str, pictures: Dict[str, str], url: str, username: str
    ):
        super().__init__(f'{name} ({username})')

        self.key = key
        self.name = name
        self.pictures = pictures
        self.url = url
        self.username = username
