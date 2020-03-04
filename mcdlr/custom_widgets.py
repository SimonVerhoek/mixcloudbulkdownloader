from PySide2.QtWidgets import QListWidgetItem

from .data_classes import Cloudcast, MixcloudUser


class UserQListWidgetItem(QListWidgetItem):
    def __init__(self, user: MixcloudUser):
        super().__init__(f'{user.name} ({user.username})')

        self.user = user


class CloudcastQListWidgetItem(QListWidgetItem):
    def __init__(self, cloudcast: Cloudcast):
        super().__init__(cloudcast.name)

        self.cloudcast = Cloudcast
