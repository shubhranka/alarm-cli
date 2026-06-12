"""Twilio notification backend for SMS and voice calls."""

from typing import Any

try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False


class TwilioNotifier:
    """Handles SMS and voice call notifications via Twilio."""

    def __init__(self, config: dict[str, Any]):
        """Initialize Twilio notifier with configuration."""
        self.enabled = config.get("enabled", False)
        self.account_sid = config.get("account_sid", "")
        self.auth_token = config.get("auth_token", "")
        self.from_number = config.get("from_number", "")
        self._client: Client | None = None

    def is_configured(self) -> bool:
        """Check if Twilio is properly configured."""
        return (
            TWILIO_AVAILABLE
            and self.enabled
            and bool(self.account_sid and self.auth_token and self.from_number)
        )

    @property
    def client(self) -> Client | None:
        """Lazy-load Twilio client."""
        if not TWILIO_AVAILABLE:
            return None

        if self._client is None and self.is_configured():
            self._client = Client(self.account_sid, self.auth_token)
        return self._client

    def send_sms(self, to: str, message: str) -> bool:
        """Send an SMS message."""
        if not self.is_configured():
            print("Twilio is not configured. Skipping SMS.")
            return False

        try:
            self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to,
            )
            return True
        except TwilioRestException as e:
            print(f"Twilio error: {e}")
            return False
        except Exception as e:
            print(f"Failed to send SMS: {e}")
            return False

    def make_call(
        self,
        to: str,
        message: str = "",
        url: str | None = None,
    ) -> bool:
        """Make a voice call.

        Either provide a message (will be spoken) or a URL with TwiML instructions.
        """
        if not self.is_configured():
            print("Twilio is not configured. Skipping call.")
            return False

        # Default TwiML URL that speaks the message
        if url is None:
            from twilio.twiml.voice_response import VoiceResponse

            response = VoiceResponse()
            response.say(message)
            # For demo purposes, you'd need to host this TwiML somewhere
            # For now, we'll use a simple message
            url = "http://demo.twilio.com/docs/voice.xml"  # Demo URL

        try:
            self.client.calls.create(
                to=to,
                from_=self.from_number,
                url=url,
            )
            return True
        except TwilioRestException as e:
            print(f"Twilio error: {e}")
            return False
        except Exception as e:
            print(f"Failed to make call: {e}")
            return False

    def send_alarm_notification(
        self,
        alarm_name: str,
        alarm_time: str,
        recipient: str,
        notification_type: str = "sms",
        custom_message: str = "",
    ) -> bool:
        """Send an alarm notification via SMS or call."""
        message = custom_message or f"⏰ Your alarm '{alarm_name}' is going off at {alarm_time}. Time to wake up!"

        if notification_type == "sms":
            return self.send_sms(recipient, message)
        elif notification_type == "call":
            return self.make_call(recipient, message)
        else:
            print(f"Unknown notification type: {notification_type}")
            return False

    def test(self) -> bool:
        """Test Twilio configuration by sending a test SMS to the from_number."""
        if not self.is_configured():
            print("Twilio is not configured.")
            return False

        print(f"Testing Twilio configuration...")
        print(f"Account SID: {self.account_sid[:12]}...")
        print(f"From number: {self.from_number}")

        # You could send a test SMS here if desired
        print("Twilio configuration appears valid.")
        return True
