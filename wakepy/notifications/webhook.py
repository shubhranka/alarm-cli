"""Webhook notification backend for Discord, Slack, and generic webhooks."""

import json
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class WebhookNotifier:
    """Handles webhook notifications (Discord, Slack, generic)."""

    # Color codes for Discord embeds
    COLOR_SUCCESS = 0x00FF00  # Green
    COLOR_WARNING = 0xFFFF00  # Yellow
    COLOR_ERROR = 0xFF0000    # Red
    COLOR_INFO = 0x0099FF     # Blue

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

    def send_discord(
        self,
        webhook_url: str,
        title: str,
        description: str,
        color: int = COLOR_INFO,
        fields: list[dict[str, Any]] | None = None,
        thumbnail_url: str | None = None,
    ) -> bool:
        """Send a Discord webhook notification with rich embed.

        Args:
            webhook_url: Discord webhook URL
            title: Embed title
            description: Embed description
            color: Embed color (default: blue)
            fields: Optional list of embed fields
            thumbnail_url: Optional thumbnail image URL
        """
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "footer": {"text": "Sent by Wakepy Alarm CLI"},
        }

        if fields:
            embed["fields"] = fields

        if thumbnail_url:
            embed["thumbnail"] = {"url": thumbnail_url}

        payload = {"embeds": [embed]}
        return self.send(webhook_url, payload)

    def send_slack(
        self,
        webhook_url: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Send a Slack webhook notification.

        Args:
            webhook_url: Slack webhook URL
            text: Main message text
            blocks: Optional Slack blocks for rich formatting
        """
        payload: dict[str, Any] = {"text": text}

        if blocks:
            payload["blocks"] = blocks

        return self.send(webhook_url, payload)

    def send_alarm_notification(
        self,
        alarm_name: str,
        alarm_time: str,
        webhook_url: str,
        platform: str = "generic",
        custom_message: str = "",
        color: int | None = None,
    ) -> bool:
        """Send an alarm notification via webhook.

        Args:
            alarm_name: Name of the alarm
            alarm_time: Time the alarm is set for
            webhook_url: Webhook URL
            platform: Target platform (discord, slack, generic)
            custom_message: Optional custom message
            color: Discord embed color
        """
        if custom_message:
            message = custom_message
        else:
            message = f"⏰ Your alarm **{alarm_name}** is going off at {alarm_time}."

        if platform == "discord":
            # Use success color (green) by default for alarms
            embed_color = color if color is not None else self.COLOR_SUCCESS

            # Add fields for more information
            fields = [
                {"name": "Alarm Name", "value": alarm_name, "inline": True},
                {"name": "Time", "value": alarm_time, "inline": True},
            ]

            return self.send_discord(
                webhook_url,
                title=f"⏰ Alarm: {alarm_name}",
                description=message,
                color=embed_color,
                fields=fields,
            )
        elif platform == "slack":
            # Create rich Slack blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"⏰ Alarm: {alarm_name}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Alarm Name:*\n{alarm_name}"},
                        {"type": "mrkdwn", "text": f"*Time:*\n{alarm_time}"},
                    ],
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": "Sent by Wakepy Alarm CLI"}
                    ],
                },
            ]

            return self.send_slack(webhook_url, message, blocks=blocks)
        else:
            # Generic webhook
            return self.send(
                webhook_url,
                {
                    "message": message,
                    "alarm": alarm_name,
                    "time": alarm_time,
                    "timestamp": datetime.now().isoformat(),
                    "source": "wakepy",
                },
            )

    def detect_platform(self, webhook_url: str) -> str:
        """Detect webhook platform from URL."""
        domain = urlparse(webhook_url).netloc.lower()

        if "discord" in domain or "discord.com" in webhook_url or "dis.gd" in webhook_url:
            return "discord"
        elif "slack" in domain or "hooks.slack.com" in webhook_url:
            return "slack"
        else:
            return "generic"
