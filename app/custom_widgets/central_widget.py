"""Central widget containing the main application UI components."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.consts import (
    SEARCH_BUTTON_STRETCH,
    SEARCH_INPUT_STRETCH,
    SEARCH_LABEL_STRETCH,
)
from app.custom_widgets.cloudcast_q_tree_widget import CloudcastQTreeWidget
from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog
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
        self.download_button = QPushButton("Download")
        cloudcast_action_buttons.addWidget(self.select_all_button)
        cloudcast_action_buttons.addWidget(self.unselect_all_button)
        cloudcast_action_buttons.addWidget(self.cancel_button)
        cloudcast_action_buttons.addWidget(self.download_button)

        self.layout.addLayout(search_user_layout)
        self.layout.addLayout(user_cloudcasts_layout)
        self.layout.addLayout(cloudcast_action_buttons)

        # Get MBD Pro button layout (centered, only shown for non-Pro users)
        self._create_get_pro_button_layout()

        self.setLayout(self.layout)

        # Signal connections
        self.get_cloudcasts_button.clicked.connect(
            lambda: self.cloudcasts.get_cloudcasts(user=self.search_user_input.selected_result)
        )
        self.select_all_button.clicked.connect(self.cloudcasts.select_all)
        self.unselect_all_button.clicked.connect(self.cloudcasts.unselect_all)
        self.download_button.clicked.connect(self.cloudcasts.download_selected_cloudcasts)
        self.cancel_button.clicked.connect(self.cloudcasts.cancel_cloudcasts_download)

        # Initial Pro UI state setup
        self.refresh_pro_ui_elements()

    def _create_get_pro_button_layout(self) -> None:
        """Create the Get MBD Pro button layout with centered positioning."""
        # Create horizontal layout with stretches for centering
        get_pro_layout = QHBoxLayout()
        get_pro_layout.addStretch()  # Left stretch

        # Create Get MBD Pro button
        self.get_mbd_pro_button = QPushButton("Get MBD Pro")
        self.get_mbd_pro_button.setObjectName("primaryButton")
        self.get_mbd_pro_button.clicked.connect(self._show_get_pro_dialog)

        get_pro_layout.addWidget(self.get_mbd_pro_button)
        get_pro_layout.addStretch()  # Right stretch

        # Add layout to main layout
        self.layout.addLayout(get_pro_layout)

    def _show_get_pro_dialog(self) -> None:
        """Show the Get Pro dialog."""
        dialog = GetProDialog(self)
        result = dialog.exec()
        if result:  # Dialog accepted (successful verification)
            self.refresh_pro_ui_elements()

    def refresh_pro_ui_elements(self) -> None:
        """Refresh Pro UI elements based on current license status."""
        is_pro = self.license_manager.is_pro

        # Show/hide Get MBD Pro button based on Pro status
        if hasattr(self, "get_mbd_pro_button"):
            self.get_mbd_pro_button.setVisible(not is_pro)
