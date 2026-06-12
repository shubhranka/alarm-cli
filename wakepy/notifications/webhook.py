"""Webhook notification backend for Discord, Slack, and generic webhooks."""

import json
from typing import Any
from urllib.parse import urlparse

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class WebhookNotifier:
    """Handles webhook notifications (Discord, Slack, generic)."""

    def __init__(self, config: dict[str, Any]):
        """Initialize webhook notifier with configuration."""
        self.webhooks = config.get("webhooks", {})

    def send(self, url: str, payload: dict[str, Any]) -> bool:
        """Send a generic webhook POST request."""
        if not REQUESTS_AVAILABLE:
            print("Requests library not available. Cannot send webhook.")
            return False

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to send webhook: {e}")
            return False

    def send_discord(self, webhook_url: str, title: str, description: str, color: int = 0xFF0000) -> bool:
        """Send a Discord webhook notification."""
        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": description,
                    "color": color,
                    "footer": {"text": "Sent by Wakepy Alarm CLI"},
                }
            ]
        }
        return self.send(webhook_url, payload)

    def send_slack(self, webhook_url: str, text: str) -> bool:
        """Send a Slack webhook notification."""
        payload = {"text": text}
        return self.send(webhook_url, payload)

    def send_alarm_notification(
        self,
        alarm_name: str,
        alarm_time: str,
        webhook_url: str,
        platform: str = "generic",
        custom_message: str = "",
    ) -> bool:
        """Send an alarm notification via webhook."""
        message = custom_message or f"⏰ Your alarm '{alarm_name}' is going off at {alarm_time}."

        if platform == "discord":
            return self.send_discord(webhook_url, f"Alarm: {alarm_name}", message)
        elif platform == "slack":
            return self.send_slack(webhook_url, message)
        else:
            return self.send(webhook_url, {"message": message, "alarm": alarm_name, "time": alarm_time})

    def detect_platform(self, webhook_url: str) -> str:
        """Detect webhook platform from URL."""
        domain = urlparse(webhook_url).netloc.lower()

        if "discord" in domain or "discord.com" in webhook_url or "dis.gd" in webhook_url:
            return "discord"
        elif "slack" in domain or "hooks.slack.com" in webhook_url:
            return "slack"
        else:
            return "generic"
