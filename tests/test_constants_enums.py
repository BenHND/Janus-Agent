"""
Test suite for TICKET B4 - Magic String Elimination
Tests the new enums added to constants.py
"""
import pytest

from janus.constants import ActionStatus, ErrorCategory, IntentType


class TestErrorCategory:
    """Test ErrorCategory enum"""

    def test_error_category_values(self):
        """Test that ErrorCategory has expected values"""
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.PERMISSION.value == "permission"
        assert ErrorCategory.USER_INPUT.value == "user_input"
        assert ErrorCategory.INTERNAL.value == "internal"

    def test_error_category_members(self):
        """Test that ErrorCategory has all expected members"""
        expected_members = {"NETWORK", "PERMISSION", "USER_INPUT", "INTERNAL"}
        actual_members = set(ErrorCategory.__members__.keys())
        assert actual_members == expected_members


class TestActionStatus:
    """Test ActionStatus enum"""

    def test_action_status_values(self):
        """Test that ActionStatus has expected values"""
        assert ActionStatus.SUCCESS.value == "success"
        assert ActionStatus.FAILED.value == "failed"
        assert ActionStatus.IN_PROGRESS.value == "in_progress"
        assert ActionStatus.PENDING.value == "pending"

    def test_action_status_members(self):
        """Test that ActionStatus has all expected members"""
        expected_members = {"SUCCESS", "FAILED", "IN_PROGRESS", "PENDING"}
        actual_members = set(ActionStatus.__members__.keys())
        assert actual_members == expected_members


class TestIntentType:
    """Test IntentType enum"""

    def test_intent_type_has_open_file(self):
        """Test that IntentType includes OPEN_FILE"""
        assert IntentType.OPEN_FILE.value == "open_file"

    def test_intent_type_has_common_intents(self):
        """Test that IntentType has common intents"""
        assert IntentType.OPEN_APP.value == "open_app"
        assert IntentType.CLOSE_APP.value == "close_app"
        assert IntentType.CLICK_ELEMENT.value == "click"
        assert IntentType.COPY_TEXT.value == "copy"
        assert IntentType.PASTE_TEXT.value == "paste"

    def test_intent_type_members_include_required(self):
        """Test that IntentType has all required members"""
        required_members = {
            "OPEN_APP",
            "CLOSE_APP",
            "OPEN_FILE",
            "NAVIGATE_URL",
            "SEARCH_WEB",
            "CLICK_ELEMENT",
            "TYPE_TEXT",
            "COPY_TEXT",
            "PASTE_TEXT",
            "EXECUTE_COMMAND",
            "UNKNOWN",
        }
        actual_members = set(IntentType.__members__.keys())
        assert required_members.issubset(actual_members)


class TestEnumUsage:
    """Test that enums can be used correctly"""

    def test_error_category_in_dict(self):
        """Test using ErrorCategory in a dictionary"""
        result = {
            "status": ActionStatus.FAILED.value,
            "error_type": ErrorCategory.USER_INPUT.value,
            "message": "Invalid input",
        }
        assert result["status"] == "failed"
        assert result["error_type"] == "user_input"

    def test_action_status_comparison(self):
        """Test comparing ActionStatus values"""
        status = "success"
        assert status == ActionStatus.SUCCESS.value
        assert status != ActionStatus.FAILED.value

    def test_intent_type_in_conditions(self):
        """Test using IntentType in conditional logic"""
        intent = IntentType.OPEN_APP.value

        if intent == IntentType.OPEN_APP.value:
            result = "open_app matched"
        else:
            result = "no match"

        assert result == "open_app matched"

    def test_enum_values_are_strings(self):
        """Test that all enum values are strings"""
        assert isinstance(ErrorCategory.NETWORK.value, str)
        assert isinstance(ActionStatus.SUCCESS.value, str)
        assert isinstance(IntentType.OPEN_APP.value, str)
