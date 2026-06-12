"""Storage backend for wakepy alarms."""

from pathlib import Path
from typing import Any

import yaml

from wakepy.models import Alarm


class Storage:
    """Handles alarm persistence to YAML file."""

    def __init__(self, storage_path: Path | str | None = None):
        """Initialize storage with optional custom path."""
        if storage_path is None:
            # Default to ~/.wakepy/alarms.yaml
            home = Path.home()
            storage_path = home / ".wakepy" / "alarms.yaml"

        self.storage_path = Path(storage_path)
        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Create storage directory if it doesn't exist."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def load_alarms(self) -> list[Alarm]:
        """Load all alarms from storage."""
        if not self.storage_path.exists():
            return []

        try:
            with open(self.storage_path, "r") as f:
                data = yaml.safe_load(f) or {}

            return [Alarm.from_dict(alarm_data) for alarm_data in data.get("alarms", [])]
        except (yaml.YAMLError, KeyError) as e:
            print(f"Warning: Failed to load alarms: {e}")
            return []

    def save_alarms(self, alarms: list[Alarm]) -> None:
        """Save all alarms to storage."""
        data: dict[str, Any] = {
            "alarms": [alarm.to_dict() for alarm in alarms],
            "version": "1.0",
        }

        with open(self.storage_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def add_alarm(self, alarm: Alarm) -> None:
        """Add a new alarm to storage."""
        alarms = self.load_alarms()
        alarms.append(alarm)
        self.save_alarms(alarms)

    def update_alarm(self, alarm_id: str, updated_alarm: Alarm) -> bool:
        """Update an existing alarm."""
        alarms = self.load_alarms()
        for i, alarm in enumerate(alarms):
            if alarm.id == alarm_id:
                alarms[i] = updated_alarm
                self.save_alarms(alarms)
                return True
        return False

    def delete_alarm(self, alarm_id: str) -> bool:
        """Delete an alarm by ID."""
        alarms = self.load_alarms()
        filtered_alarms = [a for a in alarms if a.id != alarm_id]

        if len(filtered_alarms) == len(alarms):
            return False  # No alarm was deleted

        self.save_alarms(filtered_alarms)
        return True

    def get_alarm(self, alarm_id: str) -> Alarm | None:
        """Get a specific alarm by ID."""
        alarms = self.load_alarms()
        for alarm in alarms:
            if alarm.id == alarm_id:
                return alarm
        return None

    def find_alarm_by_name(self, name: str) -> Alarm | None:
        """Find an alarm by name (returns first match)."""
        alarms = self.load_alarms()
        for alarm in alarms:
            if alarm.name == name:
                return alarm
        return None
