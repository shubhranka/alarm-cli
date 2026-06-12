"""Email notification backend using SMTP."""

import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Any


class EmailNotifier:
    """Handles email notifications via SMTP."""

    def __init__(self, config: dict[str, Any]):
        """Initialize email notifier with configuration."""
        self.enabled = config.get("enabled", False)
        self.smtp_server = config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.from_name = config.get("from_name", "Wakepy Alarm")
        self.default_subject = config.get("default_subject", "Alarm: {name} at {time}")

    def is_configured(self) -> bool:
        """Check if email is properly configured."""
        return self.enabled and bool(self.username and self.password)

    def send(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        html: bool = False,
    ) -> bool:
        """Send an email."""
        if not self.is_configured():
            print("Email is not configured. Skipping.")
            return False

        try:
            msg = EmailMessage()
            msg["From"] = formataddr((self.from_name, self.username))
            msg["To"] = to if isinstance(to, str) else ", ".join(to)
            msg["Subject"] = subject

            if html:
                msg.set_content(body, subtype="html")
            else:
                msg.set_content(body)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    def send_alarm_notification(
        self,
        alarm_name: str,
        alarm_time: str,
        recipient: str | list[str],
        custom_message: str = "",
    ) -> bool:
        """Send an alarm notification email."""
        subject = self.default_subject.format(name=alarm_name, time=alarm_time)

        if custom_message:
            body = custom_message
        else:
            body = f"""Your alarm "{alarm_name}" is going off at {alarm_time}.

Time to wake up!

---
This notification was sent by Wakepy Alarm CLI.
"""

        return self.send(recipient, subject, body)
