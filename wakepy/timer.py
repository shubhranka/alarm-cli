"""Timer and stopwatch functionality for wakepy."""

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

console = Console()


def parse_duration(duration_str: str) -> int:
    """Parse duration string to minutes.

    Supports:
    - 5m, 30m, 1h, 2h
    - 1h 30m, 2h 15m
    - Just a number (interpreted as minutes)

    Returns:
        Duration in minutes
    """
    duration_str = duration_str.strip().lower()

    # Try parsing as just minutes (e.g., "5" or "30")
    try:
        return int(duration_str)
    except ValueError:
        pass

    # Parse with units
    total_minutes = 0

    # Parse hours
    if "h" in duration_str:
        parts = duration_str.split("h")
        hours = int(parts[0].strip())
        total_minutes += hours * 60
        duration_str = parts[1] if len(parts) > 1 else ""

    # Parse remaining minutes
    if "m" in duration_str:
        minutes_part = duration_str.split("m")[0].strip()
        if minutes_part:
            try:
                total_minutes += int(minutes_part)
            except ValueError:
                pass

    return total_minutes


def format_duration(minutes: int) -> str:
    """Format duration in minutes to human-readable string."""
    if minutes < 60:
        return f"{minutes}m"
    elif minutes % 60 == 0:
        return f"{minutes // 60}h"
    else:
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"


class CountdownTimer:
    """Countdown timer with progress display."""

    def __init__(self, duration_minutes: int, name: str = "", silent: bool = False):
        """Initialize countdown timer.

        Args:
            duration_minutes: Duration in minutes
            name: Optional name for the timer
            silent: If True, don't show progress bar
        """
        self.duration_minutes = duration_minutes
        self.name = name
        self.silent = silent
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None

    def start(self) -> None:
        """Start the countdown timer."""
        self._start_time = datetime.now()
        self._end_time = self._start_time + timedelta(minutes=self.duration_minutes)

        duration_seconds = self.duration_minutes * 60

        if self.name:
            console.print(f"[bold cyan]Timer:[/bold cyan] {self.name}")
        console.print(f"[bold]Starting countdown:[/bold] {format_duration(self.duration_minutes)}")

        if self.silent:
            # Just wait without progress bar
            time.sleep(duration_seconds)
        else:
            # Show progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Counting down...",
                    total=duration_seconds,
                )

                remaining = duration_seconds
                while remaining > 0:
                    time.sleep(1)
                    remaining -= 1
                    progress.update(task, completed=duration_seconds - remaining)

        # Timer finished
        self._finished()

    def _finished(self) -> None:
        """Called when timer finishes."""
        console.print()
        console.print("[bold green]✓ Timer finished![/bold green]")

        # Play notification sound
        try:
            from wakepy.player import AudioPlayer
            from wakepy.config import Config

            cfg = Config()
            player = AudioPlayer(cfg.config.get("alarm", {}))
            player.play("default")

            # Send desktop notification
            try:
                from wakepy.notifications.desktop import DesktopNotifier

                notifier = DesktopNotifier(cfg.config.get("notifications", {}))
                notifier.send(
                    title=f"Timer Finished: {self.name}" if self.name else "Timer Finished",
                    message=f"Your {format_duration(self.duration_minutes)} timer is done!",
                )
            except Exception:
                pass
        except Exception:
            # Fallback to system beep
            print("\a")


class Stopwatch:
    """Simple stopwatch functionality."""

    def __init__(self):
        """Initialize stopwatch."""
        self._start_time: Optional[float] = None
        self._elapsed: float = 0
        self._running: bool = False

    def start(self) -> None:
        """Start the stopwatch."""
        if self._running:
            console.print("[yellow]Stopwatch is already running[/yellow]")
            return

        self._start_time = time.time()
        self._running = True
        console.print("[bold green]Stopwatch started[/bold green]")
        self._display()

    def stop(self) -> None:
        """Stop the stopwatch."""
        if not self._running:
            console.print("[yellow]Stopwatch is not running[/yellow]")
            return

        if self._start_time:
            self._elapsed += time.time() - self._start_time
        self._start_time = None
        self._running = False
        console.print("[bold red]Stopwatch stopped[/bold red]")
        self._display()

    def reset(self) -> None:
        """Reset the stopwatch."""
        self._start_time = None
        self._elapsed = 0
        self._running = False
        console.print("[bold yellow]Stopwatch reset[/bold yellow]")

    def _display(self) -> None:
        """Display current elapsed time."""
        elapsed = self._elapsed
        if self._running and self._start_time:
            elapsed += time.time() - self._start_time

        # Format elapsed time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)

        if hours > 0:
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            time_str = f"{minutes:02d}:{seconds:02d}"

        console.print(f"  [cyan]Elapsed:[/cyan] {time_str}")

    def status(self) -> None:
        """Show current status."""
        if self._running:
            console.print("[green]Running[/green]")
        else:
            console.print("[red]Stopped[/red]")
        self._display()


class PomodoroTimer:
    """Pomodoro technique timer."""

    def __init__(
        self,
        work_minutes: int = 25,
        break_minutes: int = 5,
        sessions: int = 4,
    ):
        """Initialize Pomodoro timer.

        Args:
            work_minutes: Duration of work session
            break_minutes: Duration of break session
            sessions: Number of work sessions before long break
        """
        self.work_minutes = work_minutes
        self.break_minutes = break_minutes
        self.sessions = sessions
        self._current_session = 0

    def run(self) -> None:
        """Run the Pomodoro timer."""
        console.print(f"[bold cyan]Pomodoro Timer[/bold cyan]")
        console.print(f"  Work: {format_duration(self.work_minutes)}")
        console.print(f"  Break: {format_duration(self.break_minutes)}")
        console.print(f"  Sessions: {self.sessions}")
        console.print()

        for session in range(1, self.sessions + 1):
            self._current_session = session

            # Work session
            console.print(f"[bold green]Session {session}/{self.sessions} - Work Time[/bold green]")
            timer = CountdownTimer(
                self.work_minutes,
                name=f"Work Session {session}",
                silent=True,
            )
            timer.start()

            if session < self.sessions:
                # Break (skip after last session)
                console.print()
                console.print(f"[bold yellow]Break Time[/bold yellow]")
                console.print("Press Enter to start break...")
                input()

                timer = CountdownTimer(
                    self.break_minutes,
                    name=f"Break {session}",
                    silent=True,
                )
                timer.start()
                console.print()

        console.print("[bold green]All Pomodoro sessions complete![/bold green]")
        console.print(f"Total focus time: {format_duration(self.work_minutes * self.sessions)}")
