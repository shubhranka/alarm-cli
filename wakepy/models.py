"""Data models for wakepy alarm system."""

from dataclasses import dataclass, field
from datetime import time
from typing import Any
from uuid import uuid4


@dataclass
class Action:
    """Represents a notification action when an alarm triggers."""

    type: str  # email, sms, call, webhook, command, desktop
    target: str  # recipient, URL, or command
    message: str = ""  # custom message template
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type,
            "target": self.target,
            "message": self.message,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Action":
        """Create from dictionary."""
        return cls(
            type=data["type"],
            target=data["target"],
            message=data.get("message", ""),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Alarm:
    """Represents a single alarm."""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    time: str = "08:00"  # "08:00" or "20:30"
    enabled: bool = True
    repeat: str = "once"  # once, daily, weekdays, weekends, custom
    days: list[int] = field(default_factory=list)  # [0,2,4] = Mon, Wed, Fri (0=Monday)
    snooze: int = 5  # minutes
    sound: str = "default"
    actions: list[Action] = field(default_factory=list)
    timezone: str = "local"
    one_time: bool = False  # Delete after triggering
    tags: list[str] = field(default_factory=list)  # Tags for grouping/organizing
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "time": self.time,
            "enabled": self.enabled,
            "repeat": self.repeat,
            "days": self.days,
            "snooze": self.snooze,
            "sound": self.sound,
            "actions": [a.to_dict() for a in self.actions],
            "timezone": self.timezone,
            "one_time": self.one_time,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Alarm":
        """Create from dictionary."""
        actions = [Action.from_dict(a) for a in data.get("actions", [])]
        return cls(
            id=data.get("id", str(uuid4())[:8]),
            name=data.get("name", ""),
            time=data.get("time", "08:00"),
            enabled=data.get("enabled", True),
            repeat=data.get("repeat", "once"),
            days=data.get("days", []),
            snooze=data.get("snooze", 5),
            sound=data.get("sound", "default"),
            actions=actions,
            timezone=data.get("timezone", "local"),
            one_time=data.get("one_time", False),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    def should_trigger_today(self, current_weekday: int) -> bool:
        """Check if alarm should trigger on given weekday (0=Monday)."""
        if not self.enabled:
            return False

        if self.repeat == "daily":
            return True
        elif self.repeat == "weekdays":
            return current_weekday < 5  # Mon-Fri
        elif self.repeat == "weekends":
            return current_weekday >= 5  # Sat-Sun
        elif self.repeat == "custom":
            return current_weekday in self.days
        elif self.repeat == "once":
            return True  # Will be deleted after trigger

        return False
