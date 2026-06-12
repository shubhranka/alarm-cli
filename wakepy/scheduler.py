"""Background alarm scheduler for wakepy."""

from datetime import datetime, time as dt_time
from typing import Callable

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False


class AlarmScheduler:
    """Manages alarm scheduling and triggering."""

    def __init__(self, check_interval: int = 10):
        """Initialize alarm scheduler.

        Args:
            check_interval: How often to check for alarms (seconds)
        """
        self.check_interval = check_interval
        self.scheduler: BackgroundScheduler | None = None
        self.trigger_callback: Callable | None = None
        self._running = False

    def is_available(self) -> bool:
        """Check if scheduler is available."""
        return APSCHEDULER_AVAILABLE

    def start(self, trigger_callback: Callable) -> bool:
        """Start the background scheduler.

        Args:
            trigger_callback: Function to call when an alarm triggers
        """
        if not self.is_available():
            print("Scheduler is not available. Install apscheduler.")
            return False

        if self._running:
            print("Scheduler is already running.")
            return True

        self.trigger_callback = trigger_callback
        self.scheduler = BackgroundScheduler()

        # Add a job to check alarms periodically
        self.scheduler.add_job(
            self._check_alarms,
            'interval',
            seconds=self.check_interval,
            id='alarm_checker',
            name='Alarm Checker',
        )

        self.scheduler.start()
        self._running = True
        return True

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler and self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            self.scheduler = None

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    def _check_alarms(self) -> None:
        """Check for alarms that should trigger now.

        This is called periodically by the scheduler.
        It's a placeholder - actual implementation would be in daemon.py.
        """
        if self.trigger_callback:
            self.trigger_callback()

    def schedule_alarm(self, alarm_id: str, alarm_time: str, days: list[int] | None = None) -> bool:
        """Schedule a specific alarm.

        Args:
            alarm_id: Unique alarm identifier
            alarm_time: Time in "HH:MM" format
            days: List of weekdays (0=Monday, 6=Sunday) or None for one-time

        Note: This is a simplified version. Full implementation would parse
        the alarm_time and create appropriate cron jobs.
        """
        if not self._running or not self.scheduler:
            print("Scheduler is not running.")
            return False

        # Parse the time
        try:
            hour, minute = map(int, alarm_time.split(":"))
        except ValueError:
            print(f"Invalid time format: {alarm_time}")
            return False

        job_id = f"alarm_{alarm_id}"

        # Remove existing job if any
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass

        # For one-time alarms, we'd use DateTrigger
        # For recurring, use CronTrigger
        # This is simplified - full implementation would handle this properly

        return True

    def unschedule_alarm(self, alarm_id: str) -> None:
        """Remove a scheduled alarm."""
        if not self._running or not self.scheduler:
            return

        job_id = f"alarm_{alarm_id}"
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass
