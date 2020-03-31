from typing import Callable, Dict, Optional

from PySide2.QtCore import QTimer, Slot
from PySide2.QtWidgets import QComboBox

from ..api import get_mixcloud_API_data, search_user_API_url
from ..data_classes import MixcloudUser
from ..custom_widgets.error_dialog import ErrorDialog


class SearchUserQComboBox(QComboBox):
    def __init__(self):
        super().__init__()

        self.setEditable(True)
        self.results: Dict[str, MixcloudUser] = {}
        self.selected_result: Optional[MixcloudUser] = None

        self._connect_with_delay(
            input=self.lineEdit().textEdited, slot=self.show_suggestions,
        )
        self.activated.connect(self.set_selected_user)

    def _connect_with_delay(self, input: Callable, slot: Slot, delay_ms: int = 750):
        """Connects a given input to a given Slot with a given delay."""
        self.timer = QTimer()
        self.timer.setInterval(delay_ms)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(slot)
        input.connect(self.timer.start)

    @Slot()
    def show_suggestions(self) -> None:
        phrase = self.currentText()

        if phrase:
            self.clear()
            self.results.clear()

            url = search_user_API_url(phrase=phrase)
            response, error = get_mixcloud_API_data(url=url)
            if error:
                ErrorDialog(parent=self.parent(), message=error)
            else:
                for result in response['data']:
                    user = MixcloudUser(**result)
                    self.results[user.username] = user
                    self.addItem(f'{user.name} ({user.username})')

    @Slot()
    def set_selected_user(self) -> None:
        selected_option = self.currentText()
        username = selected_option.split('(')[1].split(')')[0]
        self.selected_result = self.results[username]
