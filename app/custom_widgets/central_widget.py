"""Central widget containing the main application UI components."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.consts.ui import (
    SEARCH_BUTTON_STRETCH,
    SEARCH_INPUT_STRETCH,
    SEARCH_LABEL_STRETCH,
)
from app.custom_widgets.cloudcast_q_tree_widget import CloudcastQTreeWidget
from app.custom_widgets.search_user_q_combo_box import SearchUserQComboBox
from app.services.api_service import MixcloudAPIService, api_service
from app.services.download_service import DownloadService, download_service
from app.services.file_service import FileService, file_service
from app.services.license_manager import LicenseManager, license_manager


class CentralWidget(QWidget):
    """Main central widget containing the application's UI components.

    This widget contains the search interface, cloudcast tree, and action buttons
    for the Mixcloud Bulk Downloader application.
    """

    def __init__(
        self,
        api_service: MixcloudAPIService = api_service,
        download_service: DownloadService = download_service,
        file_service: FileService = file_service,
        license_manager: LicenseManager = license_manager,
    ) -> None:
        """Initialize the central widget with all UI components and connections.

        Args:
            api_service: Service for API operations.
            download_service: Service for downloads.
            file_service: Service for file operations.
            license_manager: License manager for Pro status checking.
        """
        super().__init__()

        # Store services
        self.api_service = api_service
        self.download_service = download_service
        self.file_service = file_service
        self.license_manager = license_manager

        self.layout = QVBoxLayout()

        # Search user layout
        search_user_layout = QHBoxLayout()
        search_user_layout.setAlignment(Qt.AlignTop)

        self.search_user_label = QLabel("Search account:")
        self.search_user_input = SearchUserQComboBox(api_service=self.api_service)
        self.get_cloudcasts_button = QPushButton("Get cloudcasts")
        self.get_cloudcasts_button.setObjectName("primaryButton")

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
            file_service=self.file_service,
        )
        user_cloudcasts_layout.addWidget(self.cloudcasts)

        # Cloudcast action buttons layout
        cloudcast_action_buttons = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.unselect_all_button = QPushButton("Unselect All")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("secondaryButton")
        self.download_button = QPushButton("Download")
        self.download_button.setObjectName("primaryButton")
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
