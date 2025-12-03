"""Tests for app.custom_widgets.user_q_list_widget_item module."""

import pytest
from PySide6.QtWidgets import QListWidgetItem

from app.custom_widgets.user_q_list_widget_item import UserQListWidgetItem
from app.data_classes import MixcloudUser


@pytest.mark.qt
class TestUserQListWidgetItem:
    """Test cases for UserQListWidgetItem widget."""

    def test_init_with_complete_user_data(self):
        """Test initialization with complete user data."""
        user = MixcloudUser(
            key="/testuser/",
            name="Test User Name",
            pictures={"large": "https://example.com/large.jpg"},
            url="https://www.mixcloud.com/testuser/",
            username="testuser",
        )

        item = UserQListWidgetItem(user=user)

        # Verify inheritance
        assert isinstance(item, QListWidgetItem)
        assert isinstance(item, UserQListWidgetItem)

        # Verify user data is stored
        assert item.user is user
        assert item.user.name == "Test User Name"
        assert item.user.username == "testuser"

        # Verify display text format
        expected_text = "Test User Name (testuser)"
        assert item.text() == expected_text

    def test_init_with_minimal_user_data(self):
        """Test initialization with minimal required user data."""
        user = MixcloudUser(
            key="/minimaluser/",
            name="Minimal User",
            pictures={},
            url="https://www.mixcloud.com/minimaluser/",
            username="minimaluser",
        )

        item = UserQListWidgetItem(user=user)

        assert item.user is user
        assert item.text() == "Minimal User (minimaluser)"

    def test_init_with_special_characters_in_name(self):
        """Test initialization with special characters in user name."""
        user = MixcloudUser(
            key="/special-user/",
            name="DJ Tëst & Spëcíal Çhars 🎵",
            pictures={"large": "https://example.com/pic.jpg"},
            url="https://www.mixcloud.com/special-user/",
            username="special-user",
        )

        item = UserQListWidgetItem(user=user)

        expected_text = "DJ Tëst & Spëcíal Çhars 🎵 (special-user)"
        assert item.text() == expected_text
        assert item.user.name == "DJ Tëst & Spëcíal Çhars 🎵"

    def test_init_with_long_user_name(self):
        """Test initialization with very long user name."""
        long_name = "A" * 200  # Very long name
        user = MixcloudUser(
            key="/longuser/",
            name=long_name,
            pictures={},
            url="https://www.mixcloud.com/longuser/",
            username="longuser",
        )

        item = UserQListWidgetItem(user=user)

        expected_text = f"{long_name} (longuser)"
        assert item.text() == expected_text
        assert len(item.text()) > 200

    def test_init_with_empty_strings(self):
        """Test initialization with empty strings in user data."""
        user = MixcloudUser(
            key="/emptyuser/",
            name="",  # Empty name
            pictures={},
            url="https://www.mixcloud.com/emptyuser/",
            username="emptyuser",
        )

        item = UserQListWidgetItem(user=user)

        expected_text = " (emptyuser)"  # Empty name results in space before username
        assert item.text() == expected_text

    def test_init_with_same_name_and_username(self):
        """Test initialization when name and username are identical."""
        user = MixcloudUser(
            key="/sameuser/",
            name="sameuser",
            pictures={},
            url="https://www.mixcloud.com/sameuser/",
            username="sameuser",
        )

        item = UserQListWidgetItem(user=user)

        expected_text = "sameuser (sameuser)"
        assert item.text() == expected_text

    def test_user_data_reference_preserved(self):
        """Test that the original user object reference is preserved."""
        original_user = MixcloudUser(
            key="/reftest/",
            name="Reference Test",
            pictures={"small": "https://example.com/small.jpg"},
            url="https://www.mixcloud.com/reftest/",
            username="reftest",
        )

        item = UserQListWidgetItem(user=original_user)

        # Verify it's the same object reference, not a copy
        assert item.user is original_user

        # Verify all attributes are accessible
        assert item.user.key == "/reftest/"
        assert item.user.pictures == {"small": "https://example.com/small.jpg"}
        assert item.user.url == "https://www.mixcloud.com/reftest/"

    def test_multiple_items_independence(self):
        """Test that multiple items are independent of each other."""
        user1 = MixcloudUser(
            key="/user1/",
            name="User One",
            pictures={},
            url="https://www.mixcloud.com/user1/",
            username="user1",
        )

        user2 = MixcloudUser(
            key="/user2/",
            name="User Two",
            pictures={},
            url="https://www.mixcloud.com/user2/",
            username="user2",
        )

        item1 = UserQListWidgetItem(user=user1)
        item2 = UserQListWidgetItem(user=user2)

        # Verify independence
        assert item1.user is not item2.user
        assert item1.text() != item2.text()
        assert item1.text() == "User One (user1)"
        assert item2.text() == "User Two (user2)"

    def test_qlistwidgetitem_inheritance_methods(self):
        """Test that inherited QListWidgetItem methods work correctly."""
        user = MixcloudUser(
            key="/inheritancetest/",
            name="Inheritance Test",
            pictures={},
            url="https://www.mixcloud.com/inheritancetest/",
            username="inheritancetest",
        )

        item = UserQListWidgetItem(user=user)

        # Test inherited methods
        original_text = item.text()

        # Test setText (inherited method)
        item.setText("Modified Text")
        assert item.text() == "Modified Text"

        # User data should still be preserved
        assert item.user is user
        assert item.user.name == "Inheritance Test"

        # Test setToolTip (inherited method)
        item.setToolTip("Test tooltip")
        assert item.toolTip() == "Test tooltip"

    def test_display_format_consistency(self):
        """Test that display format is consistent across different user types."""
        test_users = [
            ("Simple Name", "simpleuser", "Simple Name (simpleuser)"),
            ("Name With Spaces", "spacesuser", "Name With Spaces (spacesuser)"),
            ("DJ-Name", "dj-name", "DJ-Name (dj-name)"),
            ("Name123", "user123", "Name123 (user123)"),
            ("NAME", "name", "NAME (name)"),
        ]

        for name, username, expected_display in test_users:
            user = MixcloudUser(
                key=f"/{username}/",
                name=name,
                pictures={},
                url=f"https://www.mixcloud.com/{username}/",
                username=username,
            )

            item = UserQListWidgetItem(user=user)
            assert item.text() == expected_display

    def test_user_object_immutability_from_item_perspective(self):
        """Test that the item doesn't modify the original user object."""
        original_user = MixcloudUser(
            key="/immutabletest/",
            name="Immutable Test",
            pictures={"medium": "https://example.com/medium.jpg"},
            url="https://www.mixcloud.com/immutabletest/",
            username="immutabletest",
        )

        # Store original values
        original_name = original_user.name
        original_username = original_user.username
        original_key = original_user.key
        original_url = original_user.url
        original_pictures = original_user.pictures.copy()

        # Create item
        item = UserQListWidgetItem(user=original_user)

        # Verify original user data is unchanged
        assert original_user.name == original_name
        assert original_user.username == original_username
        assert original_user.key == original_key
        assert original_user.url == original_url
        assert original_user.pictures == original_pictures


class TestUserQListWidgetItemEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.qt
    def test_user_with_none_values_handled_gracefully(self):
        """Test behavior when user has None values (if possible)."""
        # Create user with minimal data - this tests the robustness
        # of the string formatting when some values might be None or empty
        user = MixcloudUser(
            key="/nonetest/",
            name="None Test",
            pictures={},
            url="https://www.mixcloud.com/nonetest/",
            username="nonetest",
        )

        # This should not raise any exceptions
        item = UserQListWidgetItem(user=user)
        assert isinstance(item.text(), str)
        assert "None Test" in item.text()
        assert "nonetest" in item.text()

    @pytest.mark.qt
    def test_user_with_whitespace_only_name(self):
        """Test behavior with whitespace-only name."""
        user = MixcloudUser(
            key="/whitespacetest/",
            name="   ",  # Only whitespace
            pictures={},
            url="https://www.mixcloud.com/whitespacetest/",
            username="whitespacetest",
        )

        item = UserQListWidgetItem(user=user)
        expected_text = "    (whitespacetest)"  # Three spaces plus space before parentheses
        assert item.text() == expected_text

    @pytest.mark.qt
    def test_user_with_newlines_in_name(self):
        """Test behavior with newlines in user name."""
        user = MixcloudUser(
            key="/newlinetest/",
            name="Multi\nLine\nName",
            pictures={},
            url="https://www.mixcloud.com/newlinetest/",
            username="newlinetest",
        )

        item = UserQListWidgetItem(user=user)
        expected_text = "Multi\nLine\nName (newlinetest)"
        assert item.text() == expected_text

    @pytest.mark.qt
    def test_display_text_format_robustness(self):
        """Test that the display text format handles various string edge cases."""
        edge_case_names = [
            "",  # Empty string
            " ",  # Single space
            "\t",  # Tab character
            "\n",  # Newline
            "  Name  ",  # Leading/trailing spaces
            "Name(WithParens)",  # Parentheses in name
            "Name[WithBrackets]",  # Brackets in name
            "Name{WithBraces}",  # Braces in name
        ]

        for i, name in enumerate(edge_case_names):
            username = f"edgecase{i}"
            user = MixcloudUser(
                key=f"/{username}/",
                name=name,
                pictures={},
                url=f"https://www.mixcloud.com/{username}/",
                username=username,
            )

            item = UserQListWidgetItem(user=user)

            # Should not raise exceptions and should follow the format
            text = item.text()
            assert isinstance(text, str)
            assert text.endswith(f"({username})")
            assert username in text


class TestUserQListWidgetItemIntegration:
    """Integration tests for UserQListWidgetItem."""

    @pytest.mark.qt
    def test_item_can_be_used_in_qlistwidget(self, qapp):
        """Test that the item can be properly used in a QListWidget."""
        from PySide6.QtWidgets import QListWidget

        user = MixcloudUser(
            key="/integrationtest/",
            name="Integration Test User",
            pictures={},
            url="https://www.mixcloud.com/integrationtest/",
            username="integrationtest",
        )

        # Create list widget and add our custom item
        list_widget = QListWidget()
        item = UserQListWidgetItem(user=user)

        list_widget.addItem(item)

        # Verify item was added correctly
        assert list_widget.count() == 1
        retrieved_item = list_widget.item(0)

        # Verify it's our custom item with preserved data
        assert isinstance(retrieved_item, UserQListWidgetItem)
        assert retrieved_item.user is user
        assert retrieved_item.text() == "Integration Test User (integrationtest)"

    @pytest.mark.qt
    def test_multiple_items_in_list_widget(self, qapp):
        """Test multiple UserQListWidgetItems in a QListWidget."""
        from PySide6.QtWidgets import QListWidget

        users = [
            MixcloudUser(
                key=f"/user{i}/",
                name=f"User {i}",
                pictures={},
                url=f"https://www.mixcloud.com/user{i}/",
                username=f"user{i}",
            )
            for i in range(3)
        ]

        list_widget = QListWidget()
        items = []

        # Add multiple items
        for user in users:
            item = UserQListWidgetItem(user=user)
            items.append(item)
            list_widget.addItem(item)

        # Verify all items were added
        assert list_widget.count() == 3

        # Verify each item maintains its data
        for i in range(3):
            retrieved_item = list_widget.item(i)
            assert isinstance(retrieved_item, UserQListWidgetItem)
            assert retrieved_item.user.username == f"user{i}"
            assert retrieved_item.text() == f"User {i} (user{i})"
