"""Desktop notification backend using plyer."""

from typing import Any

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False


class DesktopNotifier:
    """Handles desktop notifications."""

    def __init__(self, config: dict[str, Any]):
        """Initialize desktop notifier with configuration."""
        self.enabled = config.get("desktop", True)
        self.app_name = "Wakepy"
        self.app_icon = None  # Could be path to an icon file

    def is_available(self) -> bool:
        """Check if desktop notifications are available."""
        return PLYER_AVAILABLE and self.enabled

    def send(self, title: str, message: str, timeout: int = 10) -> bool:
        """Send a desktop notification."""
        if not self.is_available():
            return False

        try:
            notification.notify(
                title=title,
                message=message,
                app_name=self.app_name,
                app_icon=self.app_icon,
                timeout=timeout,
            )
            return True
        except Exception as e:
            print(f"Failed to send desktop notification: {e}")
            return False

    def send_alarm_notification(self, alarm_name: str, alarm_time: str) -> bool:
        """Send an alarm notification."""
        title = f"⏰ Alarm: {alarm_name}"
        message = f"Your alarm is going off at {alarm_time}!"
        return self.send(title, message)
