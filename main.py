"""Main application entry point for Mixcloud Bulk Downloader."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QGuiApplication

from app.consts import (
    MAIN_WINDOW_MIN_WIDTH,
    MAIN_WINDOW_MIN_HEIGHT,
    SEARCH_LABEL_STRETCH,
    SEARCH_INPUT_STRETCH,
    SEARCH_BUTTON_STRETCH,
)
from app.custom_widgets import CloudcastQTreeWidget, SearchUserQComboBox
from app.services.api_service import MixcloudAPIService
from app.services.download_service import DownloadService
from app.services.file_service import FileService

# from app.logging import logging
# logger = logging.getLogger(__name__)


class CentralWidget(QWidget):
    """Main central widget containing the application's UI components.
    
    This widget contains the search interface, cloudcast tree, and action buttons
    for the Mixcloud Bulk Downloader application.
    """
    
    def __init__(self, 
                 api_service: MixcloudAPIService | None = None,
                 download_service: DownloadService | None = None, 
                 file_service: FileService | None = None) -> None:
        """Initialize the central widget with all UI components and connections.
        
        Args:
            api_service: Service for API operations. If None, creates default.
            download_service: Service for downloads. If None, creates default.
            file_service: Service for file operations. If None, creates default.
        """
        super().__init__()

        # Create services with dependency injection support
        self.api_service = api_service or MixcloudAPIService()
        self.download_service = download_service or DownloadService()
        self.file_service = file_service or FileService()

        self.layout = QVBoxLayout()

        # Search user layout
        search_user_layout = QHBoxLayout()
        search_user_layout.setAlignment(Qt.AlignTop)

        self.search_user_label = QLabel("Search account:")
        self.search_user_input = SearchUserQComboBox(api_service=self.api_service)
        self.get_cloudcasts_button = QPushButton("Get cloudcasts")

        search_user_layout.addWidget(self.search_user_label)
        search_user_layout.addWidget(self.search_user_input)
        search_user_layout.addWidget(self.get_cloudcasts_button)

        search_user_layout.setStretch(0, SEARCH_LABEL_STRETCH)
        search_user_layout.setStretch(1, SEARCH_INPUT_STRETCH)
        search_user_layout.setStretch(2, SEARCH_BUTTON_STRETCH)

        # User cloudcasts layout
        user_cloudcasts_layout = QVBoxLayout()
        self.cloudcasts = CloudcastQTreeWidget(
            api_service=self.api_service,
            download_service=self.download_service,
            file_service=self.file_service
        )
        user_cloudcasts_layout.addWidget(self.cloudcasts)

        # Cloudcast action buttons layout
        cloudcast_action_buttons = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.unselect_all_button = QPushButton("Unselect All")
        self.cancel_button = QPushButton("Cancel")
        self.download_button = QPushButton("Download")
        cloudcast_action_buttons.addWidget(self.select_all_button)
        cloudcast_action_buttons.addWidget(self.unselect_all_button)
        cloudcast_action_buttons.addWidget(self.cancel_button)
        cloudcast_action_buttons.addWidget(self.download_button)

        self.layout.addLayout(search_user_layout)
        self.layout.addLayout(user_cloudcasts_layout)
        self.layout.addLayout(cloudcast_action_buttons)

        self.setLayout(self.layout)

        # Signal connections
        self.get_cloudcasts_button.clicked.connect(
            lambda: self.cloudcasts.get_cloudcasts(user=self.search_user_input.selected_result)
        )
        self.select_all_button.clicked.connect(self.cloudcasts.select_all)
        self.unselect_all_button.clicked.connect(self.cloudcasts.unselect_all)
        self.download_button.clicked.connect(self.cloudcasts.download_selected_cloudcasts)
        self.cancel_button.clicked.connect(self.cloudcasts.cancel_cloudcasts_download)


class MainWindow(QMainWindow):
    """Main application window for Mixcloud Bulk Downloader.
    
    This is the top-level window that contains all the application UI
    and handles window-level operations like menus and window properties.
    """
    
    def __init__(self) -> None:
        """Initialize the main window with UI components and application settings."""
        super().__init__()

        widget = CentralWidget()

        self.setWindowTitle("Mixcloud Bulk Downloader")
        self.setMinimumSize(MAIN_WINDOW_MIN_WIDTH, MAIN_WINDOW_MIN_HEIGHT)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction("Exit", QApplication.quit)

        self.setCentralWidget(widget)

        # Configure application behavior
        app_instance = QGuiApplication.instance()
        if app_instance:
            app_instance.setQuitOnLastWindowClosed(True)
            app_instance.setApplicationDisplayName("Mixcloud Bulk Downloader")
            app_instance.processEvents()


def main() -> None:
    """Main application entry point."""
    application = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    window.activateWindow()
    window.raise_()
    
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
