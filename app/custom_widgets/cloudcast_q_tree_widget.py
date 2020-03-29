from os.path import expanduser
from typing import List

from PySide2.QtCore import Qt, Slot
from PySide2.QtWidgets import QFileDialog, QTreeWidget, QTreeWidgetItem

from ..data_classes import Cloudcast, MixcloudUser
from ..threads import DownloadThread, GetCloudcastsThread


class CloudcastQTreeWidget(QTreeWidget):
    def __init__(self):
        super().__init__()

        self.setColumnCount(3)
        self.setHeaderLabels(['select', 'title', 'download status'])
        self.header().resizeSection(0, 50)
        self.header().resizeSection(1, 400)
        self.header().resizeSection(2, 200)
        self.setHeaderHidden(True)

        self.results: List[Cloudcast] = []

    def _get_download_dir(self) -> QFileDialog:
        dialog = QFileDialog()
        dialog.setOption(QFileDialog.ShowDirsOnly)
        dialog.setOption(QFileDialog.DontResolveSymlinks)
        download_dir = dialog.getExistingDirectory(
            self, 'Select download location', expanduser('~')
        )
        return download_dir

    def _get_tree_items(self) -> List[QTreeWidgetItem]:
        root = self.invisibleRootItem()
        return [root.child(i) for i in range(root.childCount())]

    def get_selected_cloudcasts(self) -> List[QTreeWidgetItem]:
        selected_cloudcasts = []
        for item in self._get_tree_items():
            if item.checkState(0) == Qt.Checked:
                selected_cloudcasts.append(item)
        return selected_cloudcasts

    @Slot(MixcloudUser)
    def get_cloudcasts(self, user: MixcloudUser) -> None:
        self.clear()
        GetCloudcastsThread(cloudcasts_list=self, user=user).start()

    @Slot()
    def select_all(self) -> None:
        for item in self._get_tree_items():
            item.setCheckState(0, Qt.Checked)

    @Slot()
    def unselect_all(self) -> None:
        for item in self._get_tree_items():
            item.setCheckState(0, Qt.Unchecked)

    @Slot()
    def download_selected_cloudcasts(self) -> None:
        download_dir = self._get_download_dir()

        for item in self.get_selected_cloudcasts():
            DownloadThread(item=item, download_dir=download_dir).start()
