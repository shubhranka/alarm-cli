"""Configuration management for wakepy."""

from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class Config:
    """Manages wakepy configuration from file and environment variables."""

    DEFAULT_CONFIG = {
        "alarm": {
            "sound_path": "~/.wakepy/sounds/",
            "default_snooze": 5,
            "24h_format": True,
            "persistent": True,
            "check_interval": 10,
        },
        "storage": {
            "file": "~/.wakepy/alarms.yaml",
        },
        "email": {
            "enabled": False,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "",
            "password": "",
            "from_name": "Wakepy Alarm",
            "default_subject": "Alarm: {name} at {time}",
        },
        "twilio": {
            "enabled": False,
            "account_sid": "",
            "auth_token": "",
            "from_number": "",
        },
        "webhooks": {
            "discord": {"default_url": ""},
            "slack": {"default_url": ""},
        },
        "notifications": {
            "desktop": True,
            "osd": True,
        },
        "advanced": {
            "wake_challenge": False,
            "gradual_volume": False,
            "pre_alarm_warning": 0,
            "statistics": True,
            "stats_file": "~/.wakepy/statistics.json",
        },
        "daemon": {
            "pid_file": "~/.wakepy/wakepy.pid",
            "log_file": "~/.wakepy/wakepy.log",
        },
    }

    def __init__(self, config_path: Path | str | None = None, load_env: bool = True):
        """Initialize configuration."""
        if load_env:
            load_dotenv()

        if config_path is None:
            config_path = Path.home() / ".wakepy" / "config.yaml"

        self.config_path = Path(config_path)
        self.config: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from file."""
        if not self.config_path.exists():
            self.config = self.DEFAULT_CONFIG.copy()
            return

        try:
            with open(self.config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}

            # Merge with defaults
            self.config = self._deep_merge(self.DEFAULT_CONFIG.copy(), user_config)
        except yaml.YAMLError as e:
            print(f"Warning: Failed to load config: {e}")
            self.config = self.DEFAULT_CONFIG.copy()

    def save(self) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get nested config value."""
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        return value if value is not None else default

    def set(self, *keys: str, value: Any) -> None:
        """Set nested config value."""
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        self.save()

    def get_env(self, key: str, default: str = "") -> str:
        """Get environment variable."""
        import os

        return os.getenv(key, default)

    @staticmethod
    def _deep_merge(base: dict, update: dict) -> dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @property
    def storage_file(self) -> Path:
        """Get the storage file path."""
        path_str = self.get("storage", "file", default="~/.wakepy/alarms.yaml")
        return Path(path_str).expanduser()

    @property
    def sound_path(self) -> Path:
        """Get the sound directory path."""
        path_str = self.get("alarm", "sound_path", default="~/.wakepy/sounds/")
        return Path(path_str).expanduser()

    @property
    def pid_file(self) -> Path:
        """Get the daemon PID file path."""
        path_str = self.get("daemon", "pid_file", default="~/.wakepy/wakepy.pid")
        return Path(path_str).expanduser()

    @property
    def log_file(self) -> Path:
        """Get the daemon log file path."""
        path_str = self.get("daemon", "log_file", default="~/.wakepy/wakepy.log")
        return Path(path_str).expanduser()

    def ensure_dirs(self) -> None:
        """Create necessary directories."""
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.sound_path.mkdir(parents=True, exist_ok=True)
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
