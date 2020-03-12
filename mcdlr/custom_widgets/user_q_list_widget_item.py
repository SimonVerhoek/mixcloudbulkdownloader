from PySide2.QtWidgets import QListWidgetItem

from ..data_classes import MixcloudUser


class UserQListWidgetItem(QListWidgetItem):
    def __init__(self, user: MixcloudUser):
        super().__init__(f'{user.name} ({user.username})')

        self.user = user
