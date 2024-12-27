from typing import Any

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import QComboBox

from ..custom_widgets.error_dialog import ErrorDialog
from ..data_classes import MixcloudUser
from ..threads import SearchArtistThread


class SearchUserQComboBox(QComboBox):
    def __init__(self):
        super().__init__()

        self.setEditable(True)
        self.results: list[MixcloudUser] = []
        self.selected_result: Any[MixcloudUser, None] = None
        self.search_artist_thread = SearchArtistThread()

        self.timer = QTimer()
        self.timer.setInterval(750)
        self.timer.setSingleShot(True)

        # Connections
        self.timer.timeout.connect(self.get_suggestions)
        self.lineEdit().textEdited.connect(self.timer.start)

        self.currentIndexChanged.connect(self.on_index_changed)
        self.search_artist_thread.new_result.connect(self.add_result)
        self.search_artist_thread.error_signal.connect(self.show_error)

        # set focus policy
        self.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit().setFocusPolicy(Qt.StrongFocus)
        self.lineEdit().setFocus()

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
        ErrorDialog(self, message=msg)

    @Slot()
    def add_result(self, item: MixcloudUser):
        self.results.append(item)

        if len(self.results) == 1:
            self.set_selected_result(index=0)

        self.addItem(f"{item.name} ({item.username})")

    @Slot(int)
    def on_index_changed(self, index: int):
        self.set_selected_result(index)

    @Slot(MixcloudUser)
    def set_selected_result(self, index: int):
        self.selected_result = self.results[index]
