from typing import Any, Callable, List

from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import QComboBox

from ..custom_widgets.error_dialog import ErrorDialog
from ..data_classes import MixcloudUser
from ..threads import SearchArtistThread


class SearchUserQComboBox(QComboBox):
    def __init__(self):
        super().__init__()

        self.setEditable(True)
        self.results: List[MixcloudUser] = []
        self.selected_result: Any[MixcloudUser, None] = None
        self.search_artist_thread = SearchArtistThread()

        # Connections
        self._connect_with_delay(
            input=self.lineEdit().textEdited, slot=self.get_suggestions,
        )
        self.currentIndexChanged.connect(
            lambda user: self.set_selected_result(index=self.currentIndex())
        )
        self.search_artist_thread.new_result.connect(self.add_result)
        self.search_artist_thread.error_signal.connect(self.show_error)

    def _connect_with_delay(self, input: Callable, slot: Slot, delay_ms: int = 750):
        """Connects a given input to a given Slot with a given delay."""
        self.timer = QTimer()
        self.timer.setInterval(delay_ms)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(slot)
        input.connect(self.timer.start)

    @Slot()
    def get_suggestions(self) -> None:
        phrase = self.currentText()

        if phrase:
            self.clear()
            self.results.clear()

            self.search_artist_thread.phrase = phrase
            self.search_artist_thread.start()

    @Slot()
    def show_error(self, msg: str):
        ErrorDialog(self.parent(), message=msg)

    @Slot()
    def add_result(self, item: MixcloudUser):
        self.results.append(item)

        if len(self.results) == 1:
            self.set_selected_result(index=0)

        self.addItem(f'{item.name} ({item.username})')

    @Slot(MixcloudUser)
    def set_selected_result(self, index: int):
        self.selected_result = self.results[index]
