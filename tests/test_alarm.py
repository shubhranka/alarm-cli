"""Tests for wakepy alarm models and utilities."""

import pytest
from wakepy.models import Alarm, Action
from wakepy.utils import (
    parse_time,
    parse_relative_time,
    parse_weekdays,
    validate_repeat_pattern,
    format_alarm_time,
    get_repeat_description,
)


class TestAction:
    """Tests for Action model."""

    def test_action_creation(self):
        action = Action(type="email", target="test@example.com")
        assert action.type == "email"
        assert action.target == "test@example.com"
        assert action.enabled is True

    def test_action_serialization(self):
        action = Action(type="sms", target="+1234567890", message="Test")
        data = action.to_dict()

        assert data["type"] == "sms"
        assert data["target"] == "+1234567890"
        assert data["message"] == "Test"

        restored = Action.from_dict(data)
        assert restored.type == action.type
        assert restored.target == action.target


class TestAlarm:
    """Tests for Alarm model."""

    def test_alarm_creation(self):
        alarm = Alarm(name="Test", time="08:00")
        assert alarm.name == "Test"
        assert alarm.time == "08:00"
        assert alarm.enabled is True
        assert len(alarm.id) == 8

    def test_alarm_serialization(self):
        alarm = Alarm(name="Test", time="08:00", repeat="daily")
        data = alarm.to_dict()

        assert data["name"] == "Test"
        assert data["time"] == "08:00"
        assert data["repeat"] == "daily"

        restored = Alarm.from_dict(data)
        assert restored.name == alarm.name
        assert restored.time == alarm.time

    def test_should_trigger_today(self):
        # Daily alarm
        alarm = Alarm(name="Daily", time="08:00", repeat="daily")
        assert alarm.should_trigger_today(0)  # Monday
        assert alarm.should_trigger_today(6)  # Sunday

        # Weekdays only
        alarm = Alarm(name="Work", time="09:00", repeat="weekdays")
        assert alarm.should_trigger_today(0)  # Monday
        assert alarm.should_trigger_today(4)  # Friday
        assert not alarm.should_trigger_today(5)  # Saturday
        assert not alarm.should_trigger_today(6)  # Sunday

        # Weekends only
        alarm = Alarm(name="Weekend", time="10:00", repeat="weekends")
        assert not alarm.should_trigger_today(0)  # Monday
        assert alarm.should_trigger_today(5)  # Saturday
        assert alarm.should_trigger_today(6)  # Sunday

        # Custom days
        alarm = Alarm(name="Custom", time="11:00", repeat="custom", days=[0, 2, 4])
        assert alarm.should_trigger_today(0)  # Monday
        assert alarm.should_trigger_today(2)  # Wednesday
        assert alarm.should_trigger_today(4)  # Friday
        assert not alarm.should_trigger_today(1)  # Tuesday

        # Disabled alarm
        alarm = Alarm(name="Disabled", time="12:00", repeat="daily", enabled=False)
        assert not alarm.should_trigger_today(0)


class TestTimeParsing:
    """Tests for time parsing utilities."""

    def test_parse_time_24h(self):
        assert parse_time("08:00") == "08:00"
        assert parse_time("23:59") == "23:59"

    def test_parse_time_12h(self):
        assert parse_time("8:00am") == "08:00"
        assert parse_time("8:00pm") == "20:00"
        assert parse_time("12:00pm") == "12:00"
        assert parse_time("12:00am") == "00:00"

    def test_parse_time_invalid(self):
        with pytest.raises(ValueError):
            parse_time("25:00")

        with pytest.raises(ValueError):
            parse_time("invalid")

    def test_parse_relative_time(self):
        # Note: parse_relative_time depends on current time, so we test the parsing logic
        result = parse_relative_time("in 30m")
        assert ":" in result  # Should return HH:MM format

        result = parse_relative_time("in 1h 30m")
        assert ":" in result


class TestRepeatValidation:
    """Tests for repeat pattern validation."""

    def test_validate_repeat_pattern(self):
        assert validate_repeat_pattern("once")
        assert validate_repeat_pattern("daily")
        assert validate_repeat_pattern("weekdays")
        assert validate_repeat_pattern("weekends")
        assert validate_repeat_pattern("custom", days=[0, 2, 4])

        assert not validate_repeat_pattern("invalid")
        assert not validate_repeat_pattern("custom", days=[])


class TestWeekdayParsing:
    """Tests for weekday string parsing."""

    def test_parse_weekdays_single(self):
        assert parse_weekdays("mon") == [0]
        assert parse_weekdays("Monday") == [0]
        assert parse_weekdays("fri") == [4]

    def test_parse_weekdays_list(self):
        assert parse_weekdays("mon,wed,fri") == [0, 2, 4]
        assert parse_weekdays("tue,thu") == [1, 3]

    def test_parse_weekdays_range(self):
        assert parse_weekdays("mon-fri") == [0, 1, 2, 3, 4]
        assert parse_weekdays("mon-wed") == [0, 1, 2]


class TestTimeFormatting:
    """Tests for time formatting."""

    def test_format_alarm_time_24h(self):
        assert format_alarm_time("08:00", True) == "08:00"
        assert format_alarm_time("23:59", True) == "23:59"

    def test_format_alarm_time_12h(self):
        assert format_alarm_time("08:00", False) == "8:00AM"
        assert format_alarm_time("20:00", False) == "8:00PM"
        assert format_alarm_time("12:00", False) == "12:00PM"
        assert format_alarm_time("00:00", False) == "12:00AM"


class TestRepeatDescription:
    """Tests for repeat pattern descriptions."""

    def test_get_repeat_description(self):
        assert get_repeat_description("once") == "Once"
        assert get_repeat_description("daily") == "Daily"
        assert "Weekdays" in get_repeat_description("weekdays")
        assert "Weekends" in get_repeat_description("weekends")

    def test_get_repeat_description_custom(self):
        desc = get_repeat_description("custom", days=[0, 2, 4])
        assert "Custom" in desc
        assert "Mon" in desc or "Wed" in desc or "Fri" in desc
