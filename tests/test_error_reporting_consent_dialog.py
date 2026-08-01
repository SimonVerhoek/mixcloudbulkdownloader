"""Qt widget tests for ErrorReportingConsentDialog."""

import pytest

from app.custom_widgets.dialogs.error_reporting_consent_dialog import ErrorReportingConsentDialog


@pytest.mark.qt
class TestErrorReportingConsentDialogStructure:
    """Tests for the structure and properties of ErrorReportingConsentDialog."""

    @pytest.fixture
    def dialog(self, qapp, qtbot):
        """Create an ErrorReportingConsentDialog instance for testing."""
        d = ErrorReportingConsentDialog(parent=None)
        qtbot.addWidget(d)
        return d

    def test_dialog_is_modal(self, dialog):
        """Dialog should be configured as modal."""
        assert dialog.isModal() is True

    def test_dialog_fixed_width(self, dialog):
        """Dialog should have a fixed width of 480 px."""
        assert dialog.width() == 480

    def test_dialog_title(self, dialog):
        """Dialog window title should match the expected string."""
        assert dialog.windowTitle() == "Help improve Mixcloud Bulk Downloader"

    def test_yes_button_exists(self, dialog):
        """Dialog should expose a yes_button attribute."""
        assert dialog.yes_button is not None

    def test_no_button_exists(self, dialog):
        """Dialog should expose a no_button attribute."""
        assert dialog.no_button is not None

    def test_yes_button_is_default(self, dialog):
        """yes_button should be the default button (activated by Return key)."""
        assert dialog.yes_button.isDefault() is True


@pytest.mark.qt
class TestErrorReportingConsentDialogInteraction:
    """Tests for button interactions in ErrorReportingConsentDialog."""

    @pytest.fixture
    def dialog(self, qapp, qtbot):
        """Create an ErrorReportingConsentDialog instance for testing."""
        d = ErrorReportingConsentDialog(parent=None)
        qtbot.addWidget(d)
        return d

    def test_yes_button_emits_accepted(self, dialog, qtbot):
        """Clicking yes_button should emit the QDialog.accepted signal."""
        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            dialog.yes_button.click()

    def test_no_button_emits_rejected(self, dialog, qtbot):
        """Clicking no_button should emit the QDialog.rejected signal."""
        with qtbot.waitSignal(dialog.rejected, timeout=1000):
            dialog.no_button.click()
