"""Utility functions for wakepy."""

import re
from datetime import datetime, timedelta
from typing import Literal


def parse_time(time_str: str) -> str:
    """Parse various time formats into HH:MM format.

    Supports:
    - HH:MM (24-hour)
    - H:MMam/pm (12-hour)
    - HH:MMam/pm (12-hour)
    - in Xm (relative time, X minutes from now)
    - in Xh Ym (relative time, hours and minutes)

    Returns:
        Time string in HH:MM (24-hour) format

    Raises:
        ValueError: If time format is invalid
    """
    time_str = time_str.strip().lower()

    # Relative time: "in Xm" or "in Xh Ym"
    if time_str.startswith("in "):
        return parse_relative_time(time_str)

    # 12-hour format with AM/PM
    ampm_match = re.match(r"^(\d{1,2}):(\d{2})(am|pm)a?$", time_str)
    if ampm_match:
        hour = int(ampm_match.group(1))
        minute = int(ampm_match.group(2))
        period = ampm_match.group(3)

        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"

    # 24-hour format HH:MM
    time_match = re.match(r"^(\d{1,2}):(\d{2})$", time_str)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))

        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError(f"Invalid time: {time_str}")

        return f"{hour:02d}:{minute:02d}"

    raise ValueError(f"Unknown time format: {time_str}")


def parse_relative_time(time_str: str) -> str:
    """Parse relative time like 'in 30m' or 'in 1h 30m'.

    Returns:
        Time string in HH:MM (24-hour) format representing the future time
    """
    time_str = time_str.replace("in ", "").strip()

    total_minutes = 0

    # Parse hours and minutes
    hour_match = re.search(r"(\d+)\s*h", time_str)
    minute_match = re.search(r"(\d+)\s*m", time_str)

    if hour_match:
        total_minutes += int(hour_match.group(1)) * 60
    if minute_match:
        total_minutes += int(minute_match.group(1))

    # If no match, assume minutes
    if not hour_match and not minute_match:
        num_match = re.match(r"(\d+)", time_str)
        if num_match:
            total_minutes = int(num_match.group(1))
        else:
            raise ValueError(f"Invalid relative time: {time_str}")

    # Calculate future time
    future = datetime.now() + timedelta(minutes=total_minutes)
    return future.strftime("%H:%M")


def validate_repeat_pattern(repeat: str, days: list[int] | None = None) -> bool:
    """Validate repeat pattern.

    Args:
        repeat: one of 'once', 'daily', 'weekdays', 'weekends', 'custom'
        days: list of weekdays (0-6) for custom patterns

    Returns:
        True if valid, False otherwise
    """
    valid_patterns = {"once", "daily", "weekdays", "weekends", "custom"}

    if repeat not in valid_patterns:
        return False

    if repeat == "custom":
        if not days or not all(0 <= d <= 6 for d in days):
            return False

    return True


def format_alarm_time(alarm_time: str, format_24h: bool = True) -> str:
    """Format alarm time for display.

    Args:
        alarm_time: Time string in HH:MM format
        format_24h: If True, use 24-hour format; otherwise use 12-hour

    Returns:
        Formatted time string
    """
    hour, minute = map(int, alarm_time.split(":"))

    if format_24h:
        return f"{hour:02d}:{minute:02d}"

    period = "AM" if hour < 12 else "PM"
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12

    return f"{display_hour}:{minute:02d}{period}"


def weekday_name(day: int, short: bool = False) -> str:
    """Get weekday name.

    Args:
        day: Weekday number (0=Monday, 6=Sunday)
        short: If True, return short name (Mon, Tue, etc.)

    Returns:
        Weekday name
    """
    names = {
        0: "Monday" if not short else "Mon",
        1: "Tuesday" if not short else "Tue",
        2: "Wednesday" if not short else "Wed",
        3: "Thursday" if not short else "Thu",
        4: "Friday" if not short else "Fri",
        5: "Saturday" if not short else "Sat",
        6: "Sunday" if not short else "Sun",
    }
    return names.get(day, "Unknown")


def parse_weekdays(day_str: str) -> list[int]:
    """Parse weekday string to list of day numbers.

    Supports:
    - Single day: "mon", "Monday", "Mon"
    - Comma-separated: "mon,wed,fri"
    - Range: "mon-fri"

    Args:
        day_str: String representation of weekdays

    Returns:
        List of day numbers (0=Monday, 6=Sunday)
    """
    day_map = {
        "mon": 0, "monday": 0,
        "tue": 1, "tuesday": 1,
        "wed": 2, "wednesday": 2,
        "thu": 3, "thursday": 3,
        "fri": 4, "friday": 4,
        "sat": 5, "saturday": 5,
        "sun": 6, "sunday": 6,
    }

    days = []
    parts = day_str.lower().split(",")

    for part in parts:
        part = part.strip()

        # Handle range
        if "-" in part:
            start, end = part.split("-")
            start_day = day_map.get(start.strip())
            end_day = day_map.get(end.strip())

            if start_day is not None and end_day is not None:
                if start_day <= end_day:
                    days.extend(range(start_day, end_day + 1))
                else:
                    # Wrap around (e.g., fri-mon)
                    days.extend(range(start_day, 7))
                    days.extend(range(0, end_day + 1))

        # Handle single day
        elif part in day_map:
            days.append(day_map[part])

    return sorted(set(days))


RepeatType = Literal["once", "daily", "weekdays", "weekends", "custom"]


def get_repeat_description(repeat: str, days: list[int] | None = None) -> str:
    """Get human-readable description of repeat pattern.

    Args:
        repeat: Repeat pattern
        days: List of weekdays for custom patterns

    Returns:
        Human-readable description
    """
    if repeat == "once":
        return "Once"
    elif repeat == "daily":
        return "Daily"
    elif repeat == "weekdays":
        return "Weekdays (Mon-Fri)"
    elif repeat == "weekends":
        return "Weekends (Sat-Sun)"
    elif repeat == "custom" and days:
        day_names = [weekday_name(d, short=True) for d in days]
        return f"Custom ({', '.join(day_names)})"
    else:
        return "Unknown"
