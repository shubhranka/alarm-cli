"""Main CLI entry point for wakepy."""

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from wakepy import __version__
from wakepy.alarm import AlarmManager
from wakepy.config import Config
from wakepy.daemon import AlarmDaemon
from wakepy.models import Action, Alarm
from wakepy.notifications import EmailNotifier, TwilioNotifier
from wakepy.utils import (
    format_alarm_time,
    get_repeat_description,
    parse_time,
    parse_weekdays,
    validate_repeat_pattern,
)

# Initialize CLI
app = typer.Typer(
    name="wake",
    add_completion=True,
    rich_markup_mode="rich",
    help="Wakepy - A comprehensive alarm clock CLI with notifications",
)

console = Console()

# Global config and manager
config: Config | None = None
alarm_manager: AlarmManager | None = None


def get_global_config() -> Config:
    """Get or create global config."""
    global config
    if config is None:
        config = Config()
    return config


def get_alarm_manager() -> AlarmManager:
    """Get or create alarm manager."""
    global alarm_manager
    if alarm_manager is None:
        cfg = get_global_config()
        alarm_manager = AlarmManager(cfg.storage_file)
    return alarm_manager


# Initialize command
@app.command()
def init(
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing config")] = False,
) -> None:
    """Initialize wakepy configuration.

    Creates the default configuration file at ~/.wakepy/config.yaml
    """
    cfg = get_global_config()

    if cfg.config_path.exists() and not force:
        console.print("[yellow]Config file already exists.[/yellow]")
        console.print(f"Location: {cfg.config_path}")
        console.print("Use --force to overwrite.")
        raise typer.Exit(1)

    cfg.config_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.save()

    console.print(f"[green]✓[/green] Config file created at: {cfg.config_path}")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Edit the config file to add your email/Twilio credentials")
    console.print("2. Run: [cyan]wake start[/cyan] to start the daemon")
    console.print("3. Run: [cyan]wake create 08:00[/cyan] to create your first alarm")


# Create alarm command
@app.command()
def create(
    time: Annotated[str, typer.Argument(help="Alarm time (HH:MM or 'in 30m')")],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Alarm name")] = None,
    repeat: Annotated[
        str,
        typer.Option(
            "--repeat",
            "-r",
            help="Repeat pattern: once, daily, weekdays, weekends, custom"
        ),
    ] = "once",
    days: Annotated[
        Optional[str],
        typer.Option("--days", "-d", help="Days for custom repeat (e.g., mon,wed,fri)"),
    ] = None,
    snooze: Annotated[
        int, typer.Option("--snooze", "-s", help="Snooze duration in minutes")
    ] = 5,
    sound: Annotated[str, typer.Option("--sound", help="Sound file name")] = "default",
    email: Annotated[
        Optional[str],
        typer.Option("--email", "-e", help="Email recipient(s), comma-separated"),
    ] = None,
    sms: Annotated[
        Optional[str], typer.Option("--sms", help="SMS recipient (phone number)")
    ] = None,
    call: Annotated[
        Optional[str], typer.Option("--call", help="Call recipient (phone number)")
    ] = None,
    webhook: Annotated[
        Optional[str], typer.Option("--webhook", help="Webhook URL")
    ] = None,
    slack_webhook: Annotated[
        Optional[str], typer.Option("--slack-webhook", help="Slack webhook URL")
    ] = None,
    one_time: Annotated[
        bool, typer.Option("--one-time", help="Delete after triggering")
    ] = False,
) -> None:
    """Create a new alarm.

    Examples:
        wake create 08:00 --name "Wake up"
        wake create "in 30m" --email me@example.com
        wake create 09:00 --repeat weekdays --sms +1234567890
    """
    manager = get_alarm_manager()
    cfg = get_global_config()

    # Parse time
    try:
        alarm_time = parse_time(time)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Validate repeat pattern
    day_list = None
    if repeat == "custom" and days:
        day_list = parse_weekdays(days)

    if not validate_repeat_pattern(repeat, day_list):
        console.print(f"[red]Error:[/red] Invalid repeat pattern: {repeat}")
        raise typer.Exit(1)

    # Create actions
    actions = []

    if email:
        actions.append(Action(type="email", target=email))

    if sms:
        actions.append(Action(type="sms", target=sms))

    if call:
        actions.append(Action(type="call", target=call))

    if webhook:
        platform = "discord" if "discord" in webhook.lower() else "generic"
        actions.append(Action(type="webhook", target=webhook, metadata={"platform": platform}))

    if slack_webhook:
        actions.append(Action(type="slack", target=slack_webhook))

    # Always add desktop notification
    actions.append(Action(type="desktop", target=""))

    # Create alarm
    alarm = Alarm(
        name=name or f"Alarm at {alarm_time}",
        time=alarm_time,
        repeat=repeat,
        days=day_list or [],
        snooze=snooze,
        sound=sound,
        actions=actions,
        one_time=one_time,
    )

    manager.add_alarm(alarm)

    console.print(f"[green]✓[/green] Alarm created: [bold]{alarm.name}[/bold]")
    console.print(f"  Time: {format_alarm_time(alarm_time, cfg.get('alarm', '24h_format', default=True))}")
    console.print(f"  Repeat: {get_repeat_description(repeat, day_list)}")
    console.print(f"  ID: {alarm.id}")


# List alarms command
@app.command("list")
def list_alarms(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed info")] = False,
) -> None:
    """List all alarms.

    Examples:
        wake list
        wake list --verbose
    """
    manager = get_alarm_manager()
    cfg = get_global_config()

    alarms = manager.get_all_alarms()

    if not alarms:
        console.print("[yellow]No alarms found.[/yellow]")
        console.print("Create one with: [cyan]wake create 08:00[/cyan]")
        return

    format_24h = cfg.get("alarm", "24h_format", default=True)

    table = Table(title="Alarms")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Name")
    table.add_column("Time")
    table.add_column("Repeat")
    table.add_column("Status")

    for alarm in alarms:
        status = "[green]✓[/green]" if alarm.enabled else "[red]✗[/red]"
        repeat_desc = get_repeat_description(alarm.repeat, alarm.days)
        time_display = format_alarm_time(alarm.time, format_24h)

        table.add_row(
            alarm.id,
            alarm.name or "-",
            time_display,
            repeat_desc,
            status,
        )

    console.print(table)

    if verbose:
        console.print("\n[bold]Detailed information:[/bold]")
        for alarm in alarms:
            console.print(f"\n[cyan]{alarm.name}[/cyan] ({alarm.id})")
            console.print(f"  Time: {alarm.time}")
            console.print(f"  Enabled: {alarm.enabled}")
            console.print(f"  Snooze: {alarm.snooze} minutes")
            console.print(f"  One-time: {alarm.one_time}")
            if alarm.actions:
                console.print(f"  Actions:")
                for action in alarm.actions:
                    console.print(f"    - {action.type}: {action.target}")


# Show alarm command
@app.command()
def show(
    alarm_id: Annotated[str, typer.Argument(help="Alarm ID")] = ...,
) -> None:
    """Show details of a specific alarm.

    Examples:
        wake show abc12345
    """
    manager = get_alarm_manager()

    alarm = manager.get_alarm(alarm_id)
    if not alarm:
        console.print(f"[red]Error:[/red] Alarm not found: {alarm_id}")
        raise typer.Exit(1)

    console.print(f"[bold]Alarm:[/bold] {alarm.name}")
    console.print(f"[dim]ID:[/dim] {alarm.id}")
    console.print()
    console.print(f"Time: {alarm.time}")
    console.print(f"Repeat: {get_repeat_description(alarm.repeat, alarm.days)}")
    console.print(f"Enabled: {'Yes' if alarm.enabled else 'No'}")
    console.print(f"Snooze: {alarm.snooze} minutes")
    console.print(f"Sound: {alarm.sound}")
    console.print(f"One-time: {'Yes' if alarm.one_time else 'No'}")
    console.print()

    if alarm.actions:
        console.print("[bold]Notifications:[/bold]")
        for action in alarm.actions:
            if action.enabled:
                console.print(f"  • {action.type}: {action.target}")


# Edit alarm command
@app.command()
def edit(
    alarm_id: Annotated[str, typer.Argument(help="Alarm ID")] = ...,
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="New alarm name")] = None,
    time: Annotated[Optional[str], typer.Option("--time", "-t", help="New alarm time")] = None,
    repeat: Annotated[
        Optional[str],
        typer.Option("--repeat", "-r", help="New repeat pattern"),
    ] = None,
    snooze: Annotated[
        Optional[int],
        typer.Option("--snooze", "-s", help="New snooze duration")
    ] = None,
) -> None:
    """Edit an existing alarm.

    Examples:
        wake edit abc12345 --time 09:00
        wake edit abc12345 --name "New name" --repeat daily
    """
    manager = get_alarm_manager()
    cfg = get_global_config()

    alarm = manager.get_alarm(alarm_id)
    if not alarm:
        console.print(f"[red]Error:[/red] Alarm not found: {alarm_id}")
        raise typer.Exit(1)

    # Apply changes
    changes = []

    if name is not None:
        alarm.name = name
        changes.append("name")

    if time is not None:
        try:
            alarm.time = parse_time(time)
            changes.append("time")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    if repeat is not None:
        alarm.repeat = repeat
        changes.append("repeat")

    if snooze is not None:
        alarm.snooze = snooze
        changes.append("snooze")

    manager.update_alarm(alarm)

    console.print(f"[green]✓[/green] Alarm updated: {alarm_id}")
    if changes:
        console.print(f"  Changed: {', '.join(changes)}")


# Delete alarm command
@app.command()
def delete(
    alarm_id: Annotated[str, typer.Argument(help="Alarm ID")] = ...,
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete an alarm.

    Examples:
        wake delete abc12345
        wake delete abc12345 --force
    """
    manager = get_alarm_manager()

    alarm = manager.get_alarm(alarm_id)
    if not alarm:
        console.print(f"[red]Error:[/red] Alarm not found: {alarm_id}")
        raise typer.Exit(1)

    if not force:
        console.print(f"Delete alarm '{alarm.name}' ({alarm_id})?")
        if not typer.confirm("Are you sure?"):
            console.print("Cancelled.")
            raise typer.Exit(0)

    manager.delete_alarm(alarm_id)
    console.print(f"[green]✓[/green] Alarm deleted: {alarm_id}")


# Enable alarm command
@app.command()
def enable(
    alarm_id: Annotated[str, typer.Argument(help="Alarm ID")] = ...,
) -> None:
    """Enable an alarm.

    Examples:
        wake enable abc12345
    """
    manager = get_alarm_manager()

    alarm = manager.get_alarm(alarm_id)
    if not alarm:
        console.print(f"[red]Error:[/red] Alarm not found: {alarm_id}")
        raise typer.Exit(1)

    alarm.enabled = True
    manager.update_alarm(alarm)

    console.print(f"[green]✓[/green] Alarm enabled: {alarm_id}")


# Disable alarm command
@app.command()
def disable(
    alarm_id: Annotated[str, typer.Argument(help="Alarm ID")] = ...,
) -> None:
    """Disable an alarm.

    Examples:
        wake disable abc12345
    """
    manager = get_alarm_manager()

    alarm = manager.get_alarm(alarm_id)
    if not alarm:
        console.print(f"[red]Error:[/red] Alarm not found: {alarm_id}")
        raise typer.Exit(1)

    alarm.enabled = False
    manager.update_alarm(alarm)

    console.print(f"[green]✓[/green] Alarm disabled: {alarm_id}")


# Daemon commands
@app.command()
def start(
    foreground: Annotated[
        bool,
        typer.Option("--foreground", "-f", help="Run in foreground")
    ] = False,
) -> None:
    """Start the wakepy daemon.

    Examples:
        wake start
        wake start --foreground
    """
    cfg = get_global_config()
    cfg.ensure_dirs()

    daemon = AlarmDaemon(cfg)
    daemon.start(foreground=foreground)


@app.command()
def stop() -> None:
    """Stop the wakepy daemon.

    Examples:
        wake stop
    """
    cfg = get_global_config()
    daemon = AlarmDaemon(cfg)
    daemon.stop()


@app.command()
def status() -> None:
    """Show daemon status.

    Examples:
        wake status
    """
    cfg = get_global_config()
    daemon = AlarmDaemon(cfg)

    status_info = daemon.status()

    if status_info["running"]:
        console.print(f"[green]✓[/green] Daemon is running")
        console.print(f"  PID: {status_info['pid']}")
        console.print(f"  Enabled alarms: {status_info['enabled_alarms']}")
        console.print(f"  Total alarms: {status_info['total_alarms']}")
    else:
        console.print("[red]✗[/red] Daemon is not running")
        if "message" in status_info:
            console.print(f"  {status_info['message']}")


@app.command()
def restart() -> None:
    """Restart the wakepy daemon.

    Examples:
        wake restart
    """
    cfg = get_global_config()
    daemon = AlarmDaemon(cfg)
    daemon.restart()


# Test commands
@app.command()
def test_email(
    recipient: Annotated[str, typer.Argument(help="Email recipient")] = ...,
) -> None:
    """Test email configuration.

    Examples:
        wake test-email me@example.com
    """
    cfg = get_global_config()
    email_config = cfg.config.get("email", {})

    notifier = EmailNotifier(email_config)

    if not notifier.is_configured():
        console.print("[red]Error:[/red] Email is not configured")
        console.print("Please configure email in: ~/.wakepy/config.yaml")
        raise typer.Exit(1)

    console.print("Sending test email...")

    success = notifier.send_alarm_notification(
        alarm_name="Test Alarm",
        alarm_time="12:00",
        recipient=recipient,
    )

    if success:
        console.print("[green]✓[/green] Test email sent successfully")
    else:
        console.print("[red]✗[/red] Failed to send test email")
        raise typer.Exit(1)


@app.command()
def test_twilio() -> None:
    """Test Twilio configuration.

    Examples:
        wake test-twilio
    """
    cfg = get_global_config()
    twilio_config = cfg.config.get("twilio", {})

    notifier = TwilioNotifier(twilio_config)
    notifier.test()


# Config command
@app.command()
def config_cmd(
    key: Annotated[Optional[str], typer.Option("--key", "-k", help="Config key")] = None,
    value: Annotated[Optional[str], typer.Option("--value", "-v", help="Config value")] = None,
) -> None:
    """Show or set configuration.

    Examples:
        wake config
        wake config --key alarm.24h_format --value false
    """
    cfg = get_global_config()

    if key and value:
        # Set config value
        keys = key.split(".")
        cfg.set(*keys, value=value)
        console.print(f"[green]✓[/green] Set {key} = {value}")
    elif key:
        # Get specific config value
        keys = key.split(".")
        value = cfg.get(*keys)
        console.print(f"{key}: {value}")
    else:
        # Show all config
        console.print(f"Config file: {cfg.config_path}")
        console.print()
        console.print("[bold]Current configuration:[/bold]")
        console.print(cfg.config_path.read_text() if cfg.config_path.exists() else "Not yet initialized")


# Version command
@app.command()
def version() -> None:
    """Show version information.

    Examples:
        wake version
    """
    console.print(f" wakepy v{__version__} ")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
