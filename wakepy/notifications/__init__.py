"""Notification backends for wakepy."""

from wakepy.notifications.email import EmailNotifier
from wakepy.notifications.twilio import TwilioNotifier
from wakepy.notifications.webhook import WebhookNotifier
from wakepy.notifications.desktop import DesktopNotifier

__all__ = [
    "EmailNotifier",
    "TwilioNotifier",
    "WebhookNotifier",
    "DesktopNotifier",
]


class NotificationManager:
    """Manages all notification backends."""

    def __init__(self, config: dict):
        """Initialize notification manager with configuration."""
        self.email = EmailNotifier(config.get("email", {}))
        self.twilio = TwilioNotifier(config.get("twilio", {}))
        self.webhook = WebhookNotifier(config)
        self.desktop = DesktopNotifier(config.get("notifications", {}))

    def send_alarm_notifications(self, alarm) -> dict[str, bool]:
        """Send notifications for an alarm based on its actions."""
        results = {}

        for action in alarm.actions:
            if not action.enabled:
                continue

            success = False
            alarm_time = alarm.time
            alarm_name = alarm.name or "Unnamed Alarm"
            message = action.message

            if action.type == "email":
                success = self.email.send_alarm_notification(
                    alarm_name=alarm_name,
                    alarm_time=alarm_time,
                    recipient=action.target,
                    custom_message=message,
                )
                results["email"] = success

            elif action.type == "sms":
                success = self.twilio.send_alarm_notification(
                    alarm_name=alarm_name,
                    alarm_time=alarm_time,
                    recipient=action.target,
                    notification_type="sms",
                    custom_message=message,
                )
                results["sms"] = success

            elif action.type == "call":
                success = self.twilio.send_alarm_notification(
                    alarm_name=alarm_name,
                    alarm_time=alarm_time,
                    recipient=action.target,
                    notification_type="call",
                    custom_message=message,
                )
                results["call"] = success

            elif action.type == "webhook":
                platform = action.metadata.get("platform") or self.webhook.detect_platform(action.target)
                success = self.webhook.send_alarm_notification(
                    alarm_name=alarm_name,
                    alarm_time=alarm_time,
                    webhook_url=action.target,
                    platform=platform,
                    custom_message=message,
                )
                results["webhook"] = success

            elif action.type == "slack":
                success = self.webhook.send_alarm_notification(
                    alarm_name=alarm_name,
                    alarm_time=alarm_time,
                    webhook_url=action.target,
                    platform="slack",
                    custom_message=message,
                )
                results["slack"] = success

            elif action.type == "desktop":
                success = self.desktop.send_alarm_notification(alarm_name, alarm_time)
                results["desktop"] = success

            # Always send desktop notification if enabled
            if self.desktop.is_available() and "desktop" not in results:
                results["desktop"] = self.desktop.send_alarm_notification(alarm_name, alarm_time)

        return results
