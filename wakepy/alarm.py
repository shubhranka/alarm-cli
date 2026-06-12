"""Alarm management logic for wakepy."""

from pathlib import Path
from typing import Optional

from wakepy.models import Alarm
from wakepy.storage import Storage


class AlarmManager:
    """High-level alarm management."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize alarm manager.

        Args:
            storage_path: Path to alarms storage file
        """
        self.storage = Storage(storage_path)

    def add_alarm(self, alarm: Alarm) -> None:
        """Add a new alarm."""
        self.storage.add_alarm(alarm)

    def update_alarm(self, alarm: Alarm) -> bool:
        """Update an existing alarm."""
        return self.storage.update_alarm(alarm.id, alarm)

    def delete_alarm(self, alarm_id: str) -> bool:
        """Delete an alarm."""
        return self.storage.delete_alarm(alarm_id)

    def get_alarm(self, alarm_id: str) -> Optional[Alarm]:
        """Get a specific alarm."""
        return self.storage.get_alarm(alarm_id)

    def get_all_alarms(self) -> list[Alarm]:
        """Get all alarms."""
        return self.storage.load_alarms()

    def find_by_name(self, name: str) -> Optional[Alarm]:
        """Find alarm by name."""
        return self.storage.find_alarm_by_name(name)

    def get_enabled_alarms(self) -> list[Alarm]:
        """Get only enabled alarms."""
        return [a for a in self.get_all_alarms() if a.enabled]
