"""Statistics tracking for wakepy alarms."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


class Statistics:
    """Track and manage alarm statistics."""

    def __init__(self, stats_file: Path | str | None = None):
        """Initialize statistics tracker.

        Args:
            stats_file: Path to statistics JSON file
        """
        if stats_file is None:
            stats_file = Path.home() / ".wakepy" / "statistics.json"

        self.stats_file = Path(stats_file)
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)

        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        """Load statistics from file."""
        if not self.stats_file.exists():
            return {
                "version": "1.0",
                "alarms": {},
                "totals": {
                    "triggers": 0,
                    "snoozes": 0,
                    "dismissals": 0,
                },
                "history": [],
            }

        try:
            with open(self.stats_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            return self._get_default_data()

    def _get_default_data(self) -> dict[str, Any]:
        """Get default statistics structure."""
        return {
            "version": "1.0",
            "alarms": {},
            "totals": {
                "triggers": 0,
                "snoozes": 0,
                "dismissals": 0,
            },
            "history": [],
        }

    def save(self) -> None:
        """Save statistics to file."""
        with open(self.stats_file, "w") as f:
            json.dump(self.data, f, indent=2, default=str)

    def record_trigger(self, alarm_id: str, alarm_name: str) -> None:
        """Record an alarm trigger."""
        # Update totals
        self.data["totals"]["triggers"] += 1

        # Update per-alarm stats
        if alarm_id not in self.data["alarms"]:
            self.data["alarms"][alarm_id] = {
                "name": alarm_name,
                "triggers": 0,
                "snoozes": 0,
                "dismissals": 0,
                "first_trigger": None,
                "last_trigger": None,
            }

        alarm_stats = self.data["alarms"][alarm_id]
        alarm_stats["triggers"] += 1
        alarm_stats["last_trigger"] = datetime.now().isoformat()
        if alarm_stats["first_trigger"] is None:
            alarm_stats["first_trigger"] = datetime.now().isoformat()

        # Add to history
        self.data["history"].append({
            "type": "trigger",
            "alarm_id": alarm_id,
            "alarm_name": alarm_name,
            "timestamp": datetime.now().isoformat(),
        })

        # Keep only last 100 history entries
        if len(self.data["history"]) > 100:
            self.data["history"] = self.data["history"][-100:]

        self.save()

    def record_snooze(self, alarm_id: str) -> None:
        """Record a snooze action."""
        # Update totals
        self.data["totals"]["snoozes"] += 1

        # Update per-alarm stats
        if alarm_id in self.data["alarms"]:
            self.data["alarms"][alarm_id]["snoozes"] += 1

        # Add to history
        alarm_name = self.data["alarms"].get(alarm_id, {}).get("name", "Unknown")
        self.data["history"].append({
            "type": "snooze",
            "alarm_id": alarm_id,
            "alarm_name": alarm_name,
            "timestamp": datetime.now().isoformat(),
        })

        # Keep only last 100 history entries
        if len(self.data["history"]) > 100:
            self.data["history"] = self.data["history"][-100:]

        self.save()

    def record_dismissal(self, alarm_id: str) -> None:
        """Record an alarm dismissal."""
        # Update totals
        self.data["totals"]["dismissals"] += 1

        # Update per-alarm stats
        if alarm_id in self.data["alarms"]:
            self.data["alarms"][alarm_id]["dismissals"] += 1

        # Add to history
        alarm_name = self.data["alarms"].get(alarm_id, {}).get("name", "Unknown")
        self.data["history"].append({
            "type": "dismissal",
            "alarm_id": alarm_id,
            "alarm_name": alarm_name,
            "timestamp": datetime.now().isoformat(),
        })

        # Keep only last 100 history entries
        if len(self.data["history"]) > 100:
            self.data["history"] = self.data["history"][-100:]

        self.save()

    def get_alarm_stats(self, alarm_id: str) -> dict[str, Any] | None:
        """Get statistics for a specific alarm."""
        return self.data["alarms"].get(alarm_id)

    def get_totals(self) -> dict[str, int]:
        """Get total statistics."""
        return self.data["totals"]

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent history."""
        return self.data["history"][-limit:]

    def display_summary(self) -> None:
        """Display a summary of statistics."""
        console.print("[bold]Statistics Summary[/bold]")
        console.print()

        # Totals
        totals = self.data["totals"]
        console.print(f"Total Triggers: [cyan]{totals['triggers']}[/cyan]")
        console.print(f"Total Snoozes: [yellow]{totals['snoozes']}[/yellow]")
        console.print(f"Total Dismissals: [green]{totals['dismissals']}[/green]")

        # Calculate snooze percentage
        if totals["triggers"] > 0:
            snooze_pct = (totals["snoozes"] / totals["triggers"]) * 100
            console.print(f"Snooze Rate: {snooze_pct:.1f}%")

        console.print()

        # Per-alarm stats
        if self.data["alarms"]:
            table = Table(title="Alarm Statistics")
            table.add_column("Alarm")
            table.add_column("Triggers")
            table.add_column("Snoozes")
            table.add_column("Dismissals")

            for alarm_id, stats in self.data["alarms"].items():
                name = stats.get("name", "Unknown")[:20]
                triggers = stats.get("triggers", 0)
                snoozes = stats.get("snoozes", 0)
                dismissals = stats.get("dismissals", 0)

                table.add_row(name, str(triggers), str(snoozes), str(dismissals))

            console.print(table)

    def reset(self) -> None:
        """Reset all statistics."""
        self.data = self._get_default_data()
        self.save()
        console.print("[yellow]Statistics reset[/yellow]")
