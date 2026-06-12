"""Daemon service management for wakepy."""

import atexit
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from wakepy.config import Config
from wakepy.storage import Storage
from wakepy.models import Alarm
from wakepy.notifications import NotificationManager
from wakepy.player import AudioPlayer


class AlarmDaemon:
    """Background daemon for managing alarms."""

    def __init__(self, config: Config | None = None):
        """Initialize alarm daemon."""
        self.config = config or Config()
        self.storage = Storage(self.config.storage_file)
        self.notifications = NotificationManager(self.config.config)
        self.player = AudioPlayer(self.config.config.get("alarm", {}))

        self.pid_file = self.config.pid_file
        self.log_file = self.config.log_file
        self._running = False
        self._check_interval = self.config.get("alarm", "check_interval", default=10)

        # Setup logging
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_file = self.log_file
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout),
            ],
        )
        self.logger = logging.getLogger("wakepy-daemon")

    def start(self, foreground: bool = False) -> bool:
        """Start the daemon.

        Args:
            foreground: If True, run in foreground (don't fork)
        """
        if self._is_running():
            self.logger.info("Daemon is already running")
            return False

        # Write PID file
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

        atexit.register(self._cleanup)

        if not foreground:
            self._daemonize()

        self._running = True
        self.logger.info("Wakepy daemon started")

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Main loop
        self._run()

        return True

    def stop(self) -> bool:
        """Stop the daemon."""
        pid = self._read_pid()
        if not pid:
            print("Daemon is not running")
            return False

        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to daemon (PID: {pid})")

            # Wait for process to exit
            for _ in range(10):
                time.sleep(0.1)
                if not self._is_process_alive(pid):
                    self._cleanup_pid_file()
                    print("Daemon stopped")
                    return True

            print("Daemon did not stop gracefully")
            return False
        except OSError as e:
            print(f"Failed to stop daemon: {e}")
            return False

    def status(self) -> dict[str, Any]:
        """Get daemon status."""
        pid = self._read_pid()

        if not pid:
            return {"running": False, "message": "Daemon is not running"}

        if self._is_process_alive(pid):
            # Get some stats from storage
            alarms = self.storage.load_alarms()
            enabled_alarms = [a for a in alarms if a.enabled]

            return {
                "running": True,
                "pid": pid,
                "enabled_alarms": len(enabled_alarms),
                "total_alarms": len(alarms),
            }

        # Stale PID file
        self._cleanup_pid_file()
        return {"running": False, "message": "Daemon is not running (cleaned stale PID file)"}

    def _run(self) -> None:
        """Main daemon loop."""
        self.logger.info("Entering main loop")

        # Track triggered alarms to avoid repeat triggers
        triggered_alarms: set[str] = set()

        while self._running:
            try:
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                current_weekday = now.weekday()  # 0=Monday, 6=Sunday

                # Check each alarm
                alarms = self.storage.load_alarms()
                for alarm in alarms:
                    if not alarm.enabled:
                        continue

                    # Skip if already triggered this minute
                    trigger_key = f"{alarm.id}_{current_time}"
                    if trigger_key in triggered_alarms:
                        continue

                    # Check if alarm should trigger today
                    if not alarm.should_trigger_today(current_weekday):
                        continue

                    # Check if time matches
                    if alarm.time == current_time:
                        self.logger.info(f"Triggering alarm: {alarm.name} ({alarm.id})")
                        self._trigger_alarm(alarm)
                        triggered_alarms.add(trigger_key)

                        # Remove one-time alarms
                        if alarm.one_time:
                            self.logger.info(f"Removing one-time alarm: {alarm.id}")
                            self.storage.delete_alarm(alarm.id)

                # Clean up old trigger keys (older than 2 minutes)
                old_keys = {
                    k for k in triggered_alarms
                    if k.split("_")[1] != current_time
                }
                triggered_alarms -= old_keys

                # Wait before next check
                time.sleep(self._check_interval)

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(self._check_interval)

    def _trigger_alarm(self, alarm: Alarm) -> None:
        """Trigger an alarm (play sound, send notifications)."""
        self.logger.info(f"Alarm triggered: {alarm.name}")

        # Play sound
        if alarm.sound != "mute":
            self.player.play(alarm.sound)

        # Send notifications
        if alarm.actions:
            results = self.notifications.send_alarm_notifications(alarm)
            self.logger.info(f"Notification results: {results}")

    def _daemonize(self) -> None:
        """Fork the process to background."""
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            print(f"Fork failed: {e}")
            sys.exit(1)

        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # Second fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            print(f"Second fork failed: {e}")
            sys.exit(1)

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle termination signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self._running = False
        self._cleanup()

    def _cleanup(self) -> None:
        """Cleanup on exit."""
        self._cleanup_pid_file()
        self.logger.info("Daemon stopped")

    def _cleanup_pid_file(self) -> None:
        """Remove PID file."""
        if self.pid_file.exists():
            self.pid_file.unlink()

    def _read_pid(self) -> int | None:
        """Read PID from file."""
        if not self.pid_file.exists():
            return None

        try:
            with open(self.pid_file, "r") as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            return None

    def _is_running(self) -> bool:
        """Check if daemon is running."""
        pid = self._read_pid()
        return pid is not None and self._is_process_alive(pid)

    def _is_process_alive(self, pid: int) -> bool:
        """Check if process with given PID is alive."""
        try:
            os.kill(pid, 0)  # Signal 0 doesn't actually send a signal
            return True
        except OSError:
            return False

    def restart(self) -> bool:
        """Restart the daemon."""
        if self._is_running():
            if not self.stop():
                return False
            time.sleep(1)
        return self.start()
