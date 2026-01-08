"""Tests for pro feature gating and functionality."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.decorators import pro_feature_gate, requires_pro
from app.services.license_manager import LicenseManager


@pytest.fixture
def mock_license_manager():
    """Create a mock license manager for testing."""
    mock_manager = Mock(spec=LicenseManager)
    mock_manager.is_pro = False  # Default to free user
    return mock_manager


@pytest.fixture
def pro_license_manager():
    """Create a mock license manager for Pro user testing."""
    mock_manager = Mock(spec=LicenseManager)
    mock_manager.is_pro = True
    return mock_manager


class TestRequiresProDecorator:
    """Test suite for @requires_pro decorator."""

    def test_requires_pro_allows_pro_users(self, pro_license_manager):
        """Test that @requires_pro allows Pro users to access features."""
        with patch("app.decorators.license_manager", pro_license_manager):

            @requires_pro
            def premium_feature():
                return "premium_result"

            result = premium_feature()
            assert result == "premium_result"

    def test_requires_pro_blocks_free_users(self, mock_license_manager):
        """Test that @requires_pro blocks free users from accessing features."""
        with patch("app.decorators.license_manager", mock_license_manager):

            @requires_pro
            def premium_feature():
                return "premium_result"

            result = premium_feature()
            assert result is None

    def test_requires_pro_with_widget_shows_upgrade_prompt(self, mock_license_manager):
        """Test that @requires_pro shows upgrade prompt for widget methods."""
        mock_widget = Mock()
        mock_widget.parent = Mock(return_value=None)

        with patch("app.decorators.license_manager", mock_license_manager):
            with patch("app.custom_widgets.dialogs.get_pro_dialog.GetProDialog") as mock_dialog:

                @requires_pro
                def widget_method(self):
                    return "premium_result"

                result = widget_method(mock_widget)
                assert result is None
                # Upgrade dialog should have been shown
                mock_dialog.assert_called_once()


class TestProFeatureGateDecorator:
    """Test suite for @pro_feature_gate decorator."""

    def test_pro_feature_gate_with_custom_name(self, mock_license_manager):
        """Test @pro_feature_gate with custom feature name."""
        with patch("app.decorators.license_manager", mock_license_manager):

            @pro_feature_gate("advanced downloads")
            def advanced_download():
                return "advanced_result"

            result = advanced_download()
            assert result is None

    def test_pro_feature_gate_allows_pro_users(self, pro_license_manager):
        """Test that @pro_feature_gate allows Pro users."""
        with patch("app.decorators.license_manager", pro_license_manager):

            @pro_feature_gate("advanced downloads")
            def advanced_download():
                return "advanced_result"

            result = advanced_download()
            assert result == "advanced_result"


class MockWidget:
    """Mock widget class for testing ProFeatureWidget functionality."""

    def __init__(self):
        self.enabled = True
        self.tooltip = ""
        self.object_name = ""
        self.parent_widget = None

    def setEnabled(self, enabled):
        self.enabled = enabled

    def setToolTip(self, tooltip):
        self.tooltip = tooltip

    def setObjectName(self, name):
        self.object_name = name

    def parent(self):
        return self.parent_widget


@pytest.mark.qt
class TestProFeatureWidget:
    """Test suite for ProFeatureWidget mixin class."""

    @pytest.fixture
    def mock_widget(self):
        """Create a mock widget for testing."""
        return MockWidget()

    @pytest.fixture
    def test_pro_widget(self, qtbot, mock_license_manager):
        """Create a test widget with ProFeatureWidget mixin."""
        from PySide6.QtWidgets import QWidget

        from app.custom_widgets.pro_feature_widget import ProFeatureWidget

        class TestWidget(ProFeatureWidget, QWidget):
            def __init__(self, license_manager, parent=None):
                QWidget.__init__(self, parent)
                ProFeatureWidget.__init__(self, license_manager, parent)

        widget = TestWidget(license_manager=mock_license_manager)
        qtbot.addWidget(widget)
        return widget

    def test_pro_feature_widget_initialization(self, test_pro_widget, mock_license_manager):
        """Test ProFeatureWidget initialization."""
        widget = test_pro_widget
        assert widget.license_manager == mock_license_manager
        assert isinstance(widget._pro_widgets, list)
        assert isinstance(widget._lock_labels, list)

    def test_register_pro_widget_free_user(self, test_pro_widget, mock_widget):
        """Test registering widget as pro feature for free user."""
        pro_widget = test_pro_widget
        pro_widget.register_pro_widget(mock_widget)

        assert mock_widget in pro_widget._pro_widgets
        assert not mock_widget.enabled
        assert "🔒" in mock_widget.tooltip
        assert mock_widget.object_name == "proFeatureDisabled"

    def test_register_pro_widget_pro_user(self, qtbot, pro_license_manager, mock_widget):
        """Test registering widget as pro feature for Pro user."""
        from PySide6.QtWidgets import QWidget

        from app.custom_widgets.pro_feature_widget import ProFeatureWidget

        class TestWidget(ProFeatureWidget, QWidget):
            def __init__(self, license_manager, parent=None):
                QWidget.__init__(self, parent)
                ProFeatureWidget.__init__(self, license_manager, parent)

        pro_widget = TestWidget(license_manager=pro_license_manager)
        qtbot.addWidget(pro_widget)
        pro_widget.register_pro_widget(mock_widget)

        assert mock_widget in pro_widget._pro_widgets
        assert mock_widget.enabled
        assert mock_widget.tooltip == ""
        assert mock_widget.object_name == ""

    def test_unregister_pro_widget(self, test_pro_widget, mock_widget):
        """Test unregistering widget from pro features."""
        pro_widget = test_pro_widget
        pro_widget.register_pro_widget(mock_widget)
        pro_widget.unregister_pro_widget(mock_widget)

        assert mock_widget not in pro_widget._pro_widgets
        assert mock_widget.enabled
        assert mock_widget.tooltip == ""
        assert mock_widget.object_name == ""


@pytest.mark.qt
class TestProFeatureIntegration:
    """Integration tests for pro feature system."""

    def test_decorator_with_widget_integration(self, qtbot, mock_license_manager):
        """Test integration between decorators and widgets."""
        from PySide6.QtWidgets import QWidget

        from app.custom_widgets.pro_feature_widget import ProFeatureWidget

        class TestWidget(ProFeatureWidget, QWidget):
            def __init__(self, license_manager):
                QWidget.__init__(self)
                ProFeatureWidget.__init__(self, license_manager)

            @requires_pro
            def premium_method(self):
                return "premium_functionality"

        # Mock the global license_manager that the decorator uses
        with patch("app.decorators.license_manager", mock_license_manager):
            with patch("app.custom_widgets.dialogs.get_pro_dialog.GetProDialog") as mock_dialog:
                widget = TestWidget(mock_license_manager)
                qtbot.addWidget(widget)
                result = widget.premium_method()

                assert result is None  # Should be blocked for free user
                mock_dialog.assert_called_once()

    def test_pro_widget_with_pro_license(self, qtbot, pro_license_manager):
        """Test pro widget behavior with Pro license."""
        from PySide6.QtWidgets import QWidget

        from app.custom_widgets.pro_feature_widget import ProFeatureWidget

        class TestWidget(ProFeatureWidget, QWidget):
            def __init__(self, license_manager):
                QWidget.__init__(self)
                ProFeatureWidget.__init__(self, license_manager)

        mock_child_widget = MockWidget()

        widget = TestWidget(license_manager=pro_license_manager)
        qtbot.addWidget(widget)
        widget.register_pro_widget(mock_child_widget)

        # Pro user should have full access
        assert mock_child_widget.enabled
        assert mock_child_widget.tooltip == ""
        assert mock_child_widget.object_name == ""
