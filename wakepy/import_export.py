"""Import and export functionality for wakepy alarms."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from rich.console import Console

console = Console()


class ImportExport:
    """Handle alarm import and export operations."""

    @staticmethod
    def export_alarms(
        alarms_file: Path | str,
        output_file: Path | str | None = None,
        format: str = "yaml",
    ) -> bool:
        """Export alarms to a file.

        Args:
            alarms_file: Path to alarms storage file
            output_file: Output file path (defaults to timestamped file)
            format: Export format (yaml or json)

        Returns:
            True if successful
        """
        alarms_file = Path(alarms_file)

        if not alarms_file.exists():
            console.print(f"[red]Error:[/red] Alarms file not found: {alarms_file}")
            return False

        try:
            with open(alarms_file, "r") as f:
                data = yaml.safe_load(f) or {}

            alarms = data.get("alarms", [])

            if not alarms:
                console.print("[yellow]No alarms to export[/yellow]")
                return False

            # Generate output filename if not provided
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ext = ".yaml" if format == "yaml" else ".json"
                output_file = Path.cwd() / f"wakepy_alarms_backup_{timestamp}{ext}"
            else:
                output_file = Path(output_file)

            if format == "json":
                with open(output_file, "w") as f:
                    json.dump({"alarms": alarms, "exported_at": datetime.now().isoformat()}, f, indent=2)
            else:
                with open(output_file, "w") as f:
                    yaml.dump({"alarms": alarms, "exported_at": datetime.now().isoformat()}, f)

            console.print(f"[green]✓[/green] Exported {len(alarms)} alarm(s) to: {output_file}")
            return True

        except Exception as e:
            console.print(f"[red]Error exporting alarms:[/red] {e}")
            return False

    @staticmethod
    def import_alarms(
        import_file: Path | str,
        alarms_file: Path | str,
        merge: bool = True,
        dry_run: bool = False,
    ) -> bool:
        """Import alarms from a file.

        Args:
            import_file: Path to import file
            alarms_file: Path to alarms storage file
            merge: If True, merge with existing alarms; if False, replace all
            dry_run: If True, show what would be imported without importing

        Returns:
            True if successful
        """
        import_file = Path(import_file)
        alarms_file = Path(alarms_file)

        if not import_file.exists():
            console.print(f"[red]Error:[/red] Import file not found: {import_file}")
            return False

        try:
            # Read import file
            if import_file.suffix == ".json":
                with open(import_file, "r") as f:
                    import_data = json.load(f)
            else:
                with open(import_file, "r") as f:
                    import_data = yaml.safe_load(f)

            imported_alarms = import_data.get("alarms", [])

            if not imported_alarms:
                console.print("[yellow]No alarms found in import file[/yellow]")
                return False

            console.print(f"Found {len(imported_alarms)} alarm(s) in import file")

            # Load existing alarms
            existing_alarms = []
            if merge and alarms_file.exists():
                with open(alarms_file, "r") as f:
                    existing_data = yaml.safe_load(f) or {}
                existing_alarms = existing_data.get("alarms", [])

            # Show what would be imported
            console.print("\n[bold]Alarms to import:[/bold]")
            for alarm in imported_alarms:
                name = alarm.get("name", "Unknown")
                time = alarm.get("time", "??:??")
                repeat = alarm.get("repeat", "once")
                console.print(f"  • {name} at {time} ({repeat})")

            if dry_run:
                console.print("\n[yellow]Dry run - no changes made[/yellow]")
                return True

            # Merge or replace
            if merge:
                # Update existing alarms or add new ones
                existing_ids = {a.get("id") for a in existing_alarms}
                new_alarms = existing_alarms.copy()

                added_count = 0
                updated_count = 0

                for alarm in imported_alarms:
                    alarm_id = alarm.get("id")
                    if alarm_id in existing_ids:
                        # Update existing
                        for i, a in enumerate(new_alarms):
                            if a.get("id") == alarm_id:
                                new_alarms[i] = alarm
                                updated_count += 1
                                break
                    else:
                        # Add new
                        new_alarms.append(alarm)
                        added_count += 1

                final_alarms = new_alarms
                console.print(f"\n[green]Added:[/green] {added_count} alarm(s)")
                console.print(f"[yellow]Updated:[/yellow] {updated_count} alarm(s)")
            else:
                # Replace all alarms
                final_alarms = imported_alarms
                console.print(f"\n[green]Replaced all alarms with {len(imported_alarms)} alarm(s)[/green]")

            # Save
            alarms_file.parent.mkdir(parents=True, exist_ok=True)
            output_data = {"alarms": final_alarms, "version": "1.0"}

            with open(alarms_file, "w") as f:
                yaml.dump(output_data, f)

            console.print(f"[green]✓[/green] Import complete")
            return True

        except Exception as e:
            console.print(f"[red]Error importing alarms:[/red] {e}")
            return False
