"""Audio playback for wakepy alarms."""

from pathlib import Path
from typing import Any
import platform

try:
    from playsound3 import playsound
    PLAYSOUND_AVAILABLE = True
except ImportError:
    PLAYSOUND_AVAILABLE = False


class AudioPlayer:
    """Handles audio playback for alarms."""

    def __init__(self, config: dict[str, Any]):
        """Initialize audio player with configuration."""
        self.sound_path = Path(config.get("sound_path", "~/.wakepy/sounds/")).expanduser()
        self.default_sound = "default"

    def is_available(self) -> bool:
        """Check if audio playback is available."""
        return PLAYSOUND_AVAILABLE

    def play(self, sound: str = "default", loop: bool = False) -> bool:
        """Play a sound.

        Args:
            sound: Name of the sound file or "default"
            loop: If True, loop the sound (not yet implemented)
        """
        if not self.is_available():
            print("Audio playback is not available.")
            return False

        sound_path = self._get_sound_path(sound)

        if not sound_path.exists():
            print(f"Sound file not found: {sound_path}")
            # Try to play a system beep as fallback
            self._system_beep()
            return False

        try:
            playsound(str(sound_path), block=not loop)
            return True
        except Exception as e:
            print(f"Failed to play sound: {e}")
            self._system_beep()
            return False

    def _get_sound_path(self, sound: str) -> Path:
        """Get the full path to a sound file."""
        if sound == "default":
            sound = "alarm.mp3"

        sound_path = self.sound_path / sound

        # Try different extensions
        if not sound_path.exists():
            for ext in [".mp3", ".wav", ".ogg", ".m4a"]:
                alt_path = self.sound_path / f"{sound}{ext}"
                if alt_path.exists():
                    return alt_path

        return sound_path

    def _system_beep(self) -> None:
        """Play a system beep as fallback."""
        try:
            if platform.system() == "Darwin":  # macOS
                import os
                os.system("afplay /System/Library/Sounds/Glass.aiff 2>/dev/null &")
            elif platform.system() == "Linux":
                print("\a")  # ASCII bell
            elif platform.system() == "Windows":
                import winsound
                winsound.Beep(1000, 500)
        except Exception:
            print("\a")  # Final fallback

    def stop(self) -> None:
        """Stop playing sound.

        Note: This is a placeholder for future implementation.
        playsound3 doesn't support stopping in the current version.
        """
        pass

    def list_sounds(self) -> list[str]:
        """List available sound files."""
        if not self.sound_path.exists():
            return []

        sounds = []
        for ext in ["*.mp3", "*.wav", "*.ogg", "*.m4a"]:
            sounds.extend(self.sound_path.glob(ext))

        return [s.name for s in sounds]
