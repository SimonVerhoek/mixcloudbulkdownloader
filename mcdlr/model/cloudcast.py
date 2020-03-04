from PySide2.QtWidgets import QListWidgetItem


class CloudcastQListWidgetItem(QListWidgetItem):
    def __init__(self, name: str, url: str, user):
        super().__init__(name)

        self.name = name
        self.url = url
        self.user = user
