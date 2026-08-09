"""Tests for license-related dialog functionality."""

import logging
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog
from app.custom_widgets.dialogs.get_pro_persuasion_dialog import GetProPersuasionDialog
from app.custom_widgets.dialogs.license_verification_failure_dialog import (
    LicenseVerificationFailureDialog,
)
from app.custom_widgets.dialogs.license_verification_success_dialog import (
    LicenseVerificationSuccessDialog,
)
from tests.stubs.license_server_stubs import StubLicenseManager


@pytest.fixture
def parent_widget():
    """Create a parent widget for dialog testing."""
    return QWidget()


@pytest.fixture
def stub_lm():
    """Provide a StubLicenseManager with empty credentials for dialog testing."""
    lm = StubLicenseManager()
    lm.settings = Mock(spec=["email", "license_key"])
    lm.settings.email = ""
    lm.settings.license_key = ""
    return lm


class StubSuccessDialog:
    """Stub for LicenseVerificationSuccessDialog that records calls without showing UI."""

    def __init__(self, parent=None) -> None:
        self.parent_arg = parent
        self.exec_called = False

    def exec(self) -> None:
        self.exec_called = True


class StubFailureDialog:
    """Stub for LicenseVerificationFailureDialog that records calls without showing UI."""

    def __init__(self, parent=None, message=None) -> None:
        self.parent_arg = parent
        self.message_arg = message
        self.exec_called = False

    def exec(self) -> None:
        self.exec_called = True


class StubErrorDialog:
    """Stub for ErrorDialog that records calls without showing UI."""

    def __init__(self, parent=None, message=None, title=None) -> None:
        self.parent_arg = parent
        self.message_arg = message
        self.title_arg = title
        self.exec_called = False

    def exec(self) -> None:
        self.exec_called = True


class TestGetProDialog:
    """Test cases for GetPro dialog functionality."""

    @pytest.mark.qt
    def test_get_pro_dialog_initialization(self, qtbot, parent_widget, stub_lm):
        """Test GetPro dialog initializes correctly."""
        dialog = GetProDialog(parent=parent_widget, license_manager=stub_lm)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Get MBD Pro"
        assert dialog.isModal()
        assert dialog.objectName() == "getProDialog"

    @pytest.mark.qt
    def test_get_pro_dialog_form_validation_empty_fields(self, qtbot, parent_widget, stub_lm):
        """Test form validation with empty fields."""
        dialog = GetProDialog(parent=parent_widget, license_manager=stub_lm)
        qtbot.addWidget(dialog)

        assert not dialog._validate_form()

    @pytest.mark.qt
    def test_get_pro_dialog_form_validation_invalid_email(self, qtbot, parent_widget, stub_lm):
        """Test form validation with invalid email format."""
        dialog = GetProDialog(parent=parent_widget, license_manager=stub_lm)
        qtbot.addWidget(dialog)

        dialog.email_edit.setText("invalid-email")
        dialog.license_key_edit.setText("test-key-123")

        assert not dialog._validate_form()

    @pytest.mark.qt
    def test_get_pro_dialog_form_validation_valid_input(self, qtbot, parent_widget, stub_lm):
        """Test form validation with valid input."""
        dialog = GetProDialog(parent=parent_widget, license_manager=stub_lm)
        qtbot.addWidget(dialog)

        dialog.email_edit.setText("test@example.com")
        dialog.license_key_edit.setText("test-key-123")

        assert dialog._validate_form()

    @pytest.mark.qt
    def test_get_pro_dialog_loads_existing_credentials(self, qtbot, parent_widget, stub_lm):
        """Test that dialog loads existing credentials from settings."""
        stub_lm.settings.email = "existing@example.com"
        stub_lm.settings.license_key = "existing-key-456"

        dialog = GetProDialog(parent=parent_widget, license_manager=stub_lm)
        qtbot.addWidget(dialog)

        assert dialog.email_edit.text() == "existing@example.com"
        assert dialog.license_key_edit.text() == "existing-key-456"

    @pytest.mark.qt
    def test_get_pro_dialog_successful_verification(self, qtbot, parent_widget, stub_lm):
        """Test successful license verification flow."""
        stub_lm.should_verify_fail = False

        stub_success = StubSuccessDialog()

        dialog = GetProDialog(
            parent=parent_widget,
            license_manager=stub_lm,
            success_dialog_factory=lambda parent: stub_success,
        )
        qtbot.addWidget(dialog)

        dialog.email_edit.setText("test@example.com")
        dialog.license_key_edit.setText("valid-key-123")

        with patch.object(dialog, "accept"):
            dialog._handle_verify()

        assert stub_lm.settings.email == "test@example.com"
        assert stub_lm.settings.license_key == "valid-key-123"
        assert stub_lm.verify_calls == 1
        assert stub_success.exec_called

    @pytest.mark.qt
    def test_get_pro_dialog_failed_verification(self, qtbot, parent_widget, stub_lm):
        """Test failed license verification flow."""
        stub_lm.should_verify_fail = True

        stub_failure = StubFailureDialog()
        failure_calls = []

        def failure_factory(parent, message=None):
            failure_calls.append((parent, message))
            return stub_failure

        dialog = GetProDialog(
            parent=parent_widget,
            license_manager=stub_lm,
            failure_dialog_factory=failure_factory,
        )
        qtbot.addWidget(dialog)

        dialog.email_edit.setText("test@example.com")
        dialog.license_key_edit.setText("invalid-key-123")

        dialog._handle_verify()

        assert len(failure_calls) == 1
        assert stub_failure.exec_called

    @pytest.mark.qt
    def test_get_pro_dialog_browser_opening(self, qtbot, parent_widget, stub_lm):
        """Test that Pro purchase button opens browser correctly."""
        stub_lm.checkout_url = "https://checkout.stripe.com/test-checkout-url"

        opened_urls = []

        dialog = GetProDialog(
            parent=parent_widget,
            license_manager=stub_lm,
            browser_open_fn=opened_urls.append,
        )
        qtbot.addWidget(dialog)

        dialog._handle_get_pro_now()

        assert stub_lm.checkout_calls == 1
        assert opened_urls == ["https://checkout.stripe.com/test-checkout-url"]

    @pytest.mark.qt
    def test_get_pro_dialog_browser_opening_failure(self, qtbot, parent_widget, stub_lm, caplog):
        """Test graceful handling of checkout URL retrieval failure."""
        stub_lm.configure_checkout_failure(reason="Checkout server error")

        stub_error = StubErrorDialog()
        error_calls = []

        def error_factory(parent, message=None, title=None):
            error_calls.append((parent, message, title))
            return stub_error

        dialog = GetProDialog(
            parent=parent_widget,
            license_manager=stub_lm,
            error_dialog_factory=error_factory,
        )
        qtbot.addWidget(dialog)

        with caplog.at_level(logging.ERROR):
            dialog._handle_get_pro_now()

        assert len(error_calls) == 1
        assert stub_error.exec_called
        assert "Failed to retrieve checkout URL" in caplog.text


class TestLicenseVerificationSuccessDialog:
    """Test cases for license verification success dialog."""

    @pytest.mark.qt
    def test_success_dialog_initialization(self, qtbot, parent_widget):
        """Test success dialog initializes correctly."""
        dialog = LicenseVerificationSuccessDialog(parent_widget)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Welcome to MBD Pro!"
        assert dialog.isModal()
        assert dialog.objectName() == "licenseSuccessDialog"

    @pytest.mark.qt
    def test_success_dialog_button_closes_dialog(self, qtbot, parent_widget):
        """Test that start button closes the dialog."""
        dialog = LicenseVerificationSuccessDialog(parent_widget)
        qtbot.addWidget(dialog)

        with patch.object(dialog, "accept") as mock_accept:
            qtbot.mouseClick(dialog.start_button, Qt.MouseButton.LeftButton)
            mock_accept.assert_called_once()


class TestLicenseVerificationFailureDialog:
    """Test cases for license verification failure dialog."""

    @pytest.mark.qt
    def test_failure_dialog_initialization(self, qtbot, parent_widget):
        """Test failure dialog initializes correctly."""
        error_message = "Custom error message"
        dialog = LicenseVerificationFailureDialog(parent_widget, error_message)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "License Verification Failed"
        assert dialog.isModal()
        assert dialog.objectName() == "licenseFailureDialog"
        assert dialog.error_message == error_message

    @pytest.mark.qt
    def test_failure_dialog_default_message(self, qtbot, parent_widget):
        """Test failure dialog with default error message."""
        dialog = LicenseVerificationFailureDialog(parent_widget)
        qtbot.addWidget(dialog)

        assert dialog.error_message == "License verification failed."

    @pytest.mark.qt
    def test_failure_dialog_button_closes_dialog(self, qtbot, parent_widget):
        """Test that ok button closes the dialog."""
        dialog = LicenseVerificationFailureDialog(parent_widget)
        qtbot.addWidget(dialog)

        with patch.object(dialog, "accept") as mock_accept:
            qtbot.mouseClick(dialog.ok_button, Qt.MouseButton.LeftButton)
            mock_accept.assert_called_once()


class TestGetProPersuasionDialog:
    """Test cases for Pro persuasion dialog."""

    @pytest.mark.qt
    def test_pro_persuasion_dialog_should_show_non_pro_user(self, qtbot):
        """Test that dialog should be shown for non-Pro users."""

        class FreeUserLM:
            is_pro = False

        assert GetProPersuasionDialog.should_show(license_manager_fn=FreeUserLM) == True

    @pytest.mark.qt
    def test_pro_persuasion_dialog_should_not_show_pro_user(self, qtbot):
        """Test that dialog should not be shown for Pro users."""

        class ProUserLM:
            is_pro = True

        assert GetProPersuasionDialog.should_show(license_manager_fn=ProUserLM) == False

    @pytest.mark.qt
    def test_pro_persuasion_dialog_initialization(self, qtbot, parent_widget, stub_lm):
        """Test Pro persuasion dialog initializes correctly."""
        dialog = GetProPersuasionDialog(parent=parent_widget, license_manager=stub_lm)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Upgrade to MBD Pro"
        assert dialog.isModal()
        assert dialog.objectName() == "proPersuasionDialog"

    @pytest.mark.qt
    def test_pro_persuasion_dialog_get_pro_button_opens_browser(
        self, qtbot, parent_widget, stub_lm
    ):
        """Test that Get Pro button opens browser correctly."""
        stub_lm.checkout_url = "https://checkout.stripe.com/test-checkout-url"

        opened_urls = []

        dialog = GetProPersuasionDialog(
            parent=parent_widget,
            license_manager=stub_lm,
            browser_open_fn=opened_urls.append,
        )
        qtbot.addWidget(dialog)

        with patch.object(dialog, "accept") as mock_accept:
            dialog._handle_get_pro()

            assert stub_lm.checkout_calls == 1
            assert opened_urls == ["https://checkout.stripe.com/test-checkout-url"]
            mock_accept.assert_called_once()

    @pytest.mark.qt
    def test_pro_persuasion_dialog_get_pro_button_handles_browser_failure(
        self, qtbot, parent_widget, stub_lm, caplog
    ):
        """Test graceful handling of checkout URL retrieval failure."""
        stub_lm.configure_checkout_failure(reason="Checkout server error")

        stub_error = StubErrorDialog()
        error_calls = []

        def error_factory(parent, message=None, title=None):
            error_calls.append((parent, message, title))
            return stub_error

        dialog = GetProPersuasionDialog(
            parent=parent_widget,
            license_manager=stub_lm,
            error_dialog_factory=error_factory,
        )
        qtbot.addWidget(dialog)

        with patch.object(dialog, "accept") as mock_accept:
            with caplog.at_level(logging.ERROR):
                dialog._handle_get_pro()

            assert len(error_calls) == 1
            assert stub_error.exec_called
            assert "Failed to retrieve checkout URL" in caplog.text
            mock_accept.assert_called_once()

    @pytest.mark.qt
    def test_pro_persuasion_dialog_no_thanks_button(self, qtbot, parent_widget, stub_lm):
        """Test that No thanks button dismisses the dialog."""
        dialog = GetProPersuasionDialog(parent=parent_widget, license_manager=stub_lm)
        qtbot.addWidget(dialog)

        with patch.object(dialog, "reject") as mock_reject:
            qtbot.mouseClick(dialog.no_thanks_button, Qt.MouseButton.LeftButton)
            mock_reject.assert_called_once()


class StubPersuasionDialog:
    """Stub for GetProPersuasionDialog that records calls without showing UI."""

    _should_show: bool = True
    instances: list["StubPersuasionDialog"] = []

    def __init__(self, parent=None) -> None:
        self.exec_called = False
        StubPersuasionDialog.instances.append(self)

    @classmethod
    def should_show(cls) -> bool:
        return cls._should_show

    def exec(self) -> None:
        self.exec_called = True


class TestDialogIntegration:
    """Test cases for dialog integration with main application."""

    @pytest.mark.qt
    def test_cloudcast_widget_shows_dialog_for_non_pro_users(self, qtbot):
        """Test that cloudcast widget shows Pro dialog for non-Pro users."""
        from app.custom_widgets.cloudcast_q_tree_widget import CloudcastQTreeWidget

        StubPersuasionDialog._should_show = True
        StubPersuasionDialog.instances.clear()

        widget = CloudcastQTreeWidget(dialog_factory=StubPersuasionDialog)
        qtbot.addWidget(widget)

        widget.show_pro_persuasion_dialog()

        assert len(StubPersuasionDialog.instances) == 1
        assert StubPersuasionDialog.instances[0].exec_called

    @pytest.mark.qt
    def test_cloudcast_widget_skips_dialog_for_pro_users(self, qtbot):
        """Test that cloudcast widget skips Pro dialog for Pro users."""
        from app.custom_widgets.cloudcast_q_tree_widget import CloudcastQTreeWidget

        StubPersuasionDialog._should_show = False
        StubPersuasionDialog.instances.clear()

        widget = CloudcastQTreeWidget(dialog_factory=StubPersuasionDialog)
        qtbot.addWidget(widget)

        widget.show_pro_persuasion_dialog()

        assert len(StubPersuasionDialog.instances) == 0
