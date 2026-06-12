"""Wakepy - A comprehensive alarm clock CLI with notifications."""

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

from wakepy.models import Alarm, Action
from wakepy.alarm import AlarmManager
from wakepy.config import Config
from wakepy.storage import Storage

__all__ = [
    "__version__",
    "Alarm",
    "Action",
    "AlarmManager",
    "Config",
    "Storage",
]
