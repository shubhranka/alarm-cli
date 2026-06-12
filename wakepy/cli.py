"""Main CLI entry point for wakepy."""

import sys
import time
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
    tags: Annotated[
        Optional[str],
        typer.Option("--tags", "-t", help="Comma-separated tags for grouping"),
    ] = None,
    timezone: Annotated[
        str,
        typer.Option("--timezone", "-tz", help="Timezone (e.g., 'America/New_York')"),
    ] = "local",
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

    # Handle webhooks - use from config if not specified
    if webhook:
        platform = "discord" if "discord" in webhook.lower() else "generic"
        actions.append(Action(type="webhook", target=webhook, metadata={"platform": platform}))
    elif cfg.get("webhooks", "discord", "default_url"):
        # Use default Discord webhook from config
        actions.append(Action(
            type="webhook",
            target=cfg.get("webhooks", "discord", "default_url"),
            metadata={"platform": "discord"},
        ))

    if slack_webhook:
        actions.append(Action(type="slack", target=slack_webhook))
    elif cfg.get("webhooks", "slack", "default_url"):
        # Use default Slack webhook from config
        actions.append(Action(
            type="slack",
            target=cfg.get("webhooks", "slack", "default_url"),
        ))

    # Always add desktop notification
    actions.append(Action(type="desktop", target=""))

    # Parse tags
    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]

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
        tags=tag_list,
        timezone=timezone,
    )

    manager.add_alarm(alarm)

    console.print(f"[green]✓[/green] Alarm created: [bold]{alarm.name}[/bold]")
    console.print(f"  Time: {format_alarm_time(alarm_time, cfg.get('alarm', '24h_format', default=True))}")
    console.print(f"  Repeat: {get_repeat_description(repeat, day_list)}")
    console.print(f"  ID: {alarm.id}")
    if tag_list:
        console.print(f"  Tags: {', '.join(tag_list)}")


# List alarms command
@app.command("list")
def list_alarms(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed info")] = False,
    tag: Annotated[Optional[str], typer.Option("--tag", help="Filter by tag")] = None,
    enabled: Annotated[Optional[bool], typer.Option("--enabled/--disabled", help="Filter by status")] = None,
) -> None:
    """List all alarms.

    Examples:
        wake list
        wake list --verbose
        wake list --tag work
        wake list --enabled
    """
    manager = get_alarm_manager()
    cfg = get_global_config()

    alarms = manager.get_all_alarms()

    # Apply filters
    if tag is not None:
        alarms = [a for a in alarms if tag in a.tags]
    if enabled is not None:
        alarms = [a for a in alarms if a.enabled == enabled]

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
    table.add_column("Tags", style="dim")
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
            ", ".join(alarm.tags) if alarm.tags else "-",
            status,
        )

    console.print(table)

    if verbose:
        console.print("\n[bold]Detailed information:[/bold]")
        for alarm in alarms:
            console.print(f"\n[cyan]{alarm.name}[/cyan] ({alarm.id})")
            console.print(f"  Time: {alarm.time}")
            console.print(f"  Repeat: {get_repeat_description(alarm.repeat, alarm.days)}")
            console.print(f"  Enabled: {alarm.enabled}")
            console.print(f"  Snooze: {alarm.snooze} minutes")
            console.print(f"  One-time: {alarm.one_time}")
            if alarm.tags:
                console.print(f"  Tags: {', '.join(alarm.tags)}")
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
    if alarm.tags:
        console.print(f"Tags: {', '.join(alarm.tags)}")
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
    tags: Annotated[
        Optional[str],
        typer.Option("--tags", "-t", help="Replace tags (comma-separated)"),
    ] = None,
    add_tags: Annotated[
        Optional[str],
        typer.Option("--add-tags", help="Add tags (comma-separated)"),
    ] = None,
    remove_tags: Annotated[
        Optional[str],
        typer.Option("--remove-tags", help="Remove tags (comma-separated)"),
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

    if tags is not None:
        alarm.tags = [t.strip() for t in tags.split(",")]
        changes.append("tags")

    if add_tags is not None:
        new_tags = [t.strip() for t in add_tags.split(",")]
        for tag in new_tags:
            if tag not in alarm.tags:
                alarm.tags.append(tag)
        changes.append("added tags")

    if remove_tags is not None:
        tags_to_remove = [t.strip() for t in remove_tags.split(",")]
        alarm.tags = [t for t in alarm.tags if t not in tags_to_remove]
        changes.append("removed tags")

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


@app.command("test-webhook")
def test_webhook_cmd(
    url: Annotated[str, typer.Argument(help="Webhook URL to test")] = ...,
    platform: Annotated[
        str,
        typer.Option("--platform", "-p", help="Platform: discord, slack, or generic"),
    ] = "auto",
) -> None:
    """Test webhook configuration.

    Examples:
        wake test-webhook https://discord.com/api/webhooks/...
        wake test-webhook https://hooks.slack.com/... --platform slack
    """
    from wakepy.notifications.webhook import WebhookNotifier

    cfg = get_global_config()
    webhook_notifier = WebhookNotifier(cfg.config)

    # Auto-detect platform if needed
    if platform == "auto":
        platform = webhook_notifier.detect_platform(url)

    console.print(f"Testing webhook to: {url[:50]}...")
    console.print(f"Platform: {platform}")

    success = webhook_notifier.send_alarm_notification(
        alarm_name="Test Alarm",
        alarm_time="12:00",
        webhook_url=url,
        platform=platform,
        custom_message="This is a test notification from Wakepy.",
    )

    if success:
        console.print("[green]✓[/green] Test webhook sent successfully")
    else:
        console.print("[red]✗[/red] Failed to send test webhook")
        raise typer.Exit(1)


# Config command
@app.command("config")
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


# Timer command
@app.command("timer")
def timer_cmd(
    duration: Annotated[str, typer.Argument(help="Duration (e.g., 5m, 1h, 30m)")],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Timer name")] = None,
    silent: Annotated[bool, typer.Option("--silent", "-s", help="Run without progress bar")] = False,
) -> None:
    """Start a countdown timer.

    Examples:
        wake timer 5m
        wake timer 1h --name "Focus session"
        wake timer 30m --silent
    """
    from wakepy.timer import CountdownTimer, parse_duration

    minutes = parse_duration(duration)
    if minutes <= 0:
        console.print("[red]Error:[/red] Invalid duration")
        raise typer.Exit(1)

    timer = CountdownTimer(minutes, name or "", silent)
    timer.start()


# Stopwatch command
@app.command()
def stopwatch(
    action: Annotated[
        str,
        typer.Argument(help="Action: start, stop, reset, status"),
    ] = "status",
) -> None:
    """Stopwatch functionality.

    Examples:
        wake stopwatch start
        wake stopwatch stop
        wake stopwatch reset
        wake stopwatch status
    """
    from wakepy.timer import Stopwatch

    # For simplicity, we'll use a new instance each time
    # In a real implementation, you'd persist the state
    if action == "start":
        stopwatch = Stopwatch()
        stopwatch.start()
        console.print("\nPress Ctrl+C to stop...")
        try:
            while True:
                time.sleep(1)
                stopwatch._display()
        except KeyboardInterrupt:
            stopwatch.stop()
    elif action == "stop":
        console.print("[yellow]Note: Stopwatch state is not persistent[/yellow]")
        console.print("Use 'wake stopwatch start' and stop with Ctrl+C")
    elif action == "reset":
        console.print("[yellow]Note: Stopwatch state is not persistent[/yellow]")
    elif action == "status":
        console.print("[yellow]Note: Stopwatch state is not persistent[/yellow]")
        console.print("Use 'wake stopwatch start' to begin")
    else:
        console.print(f"[red]Unknown action:[/red] {action}")
        raise typer.Exit(1)


# World clock command
@app.command()
def worldclock(
    add: Annotated[
        Optional[str],
        typer.Option("--add", "-a", help="Add timezone to display"),
    ] = None,
    list_zones: Annotated[
        bool,
        typer.Option("--list", "-l", help="List available timezones"),
    ] = False,
) -> None:
    """Show world clock in multiple timezones.

    Examples:
        wake worldclock
        wake worldclock --add America/New_York
        wake worldclock --add Europe/London --add Asia/Tokyo
    """
    from datetime import datetime
    from rich.table import Table
    import pytz

    if list_zones:
        console.print("[bold]Common timezones:[/bold]")
        common_zones = [
            "America/New_York",
            "America/Los_Angeles",
            "America/Chicago",
            "Europe/London",
            "Europe/Paris",
            "Europe/Berlin",
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Asia/Dubai",
            "Australia/Sydney",
        ]
        for zone in common_zones:
            console.print(f"  {zone}")
        return

    # Default zones to show
    zones = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"]

    if add:
        zones.append(add)

    table = Table(title="World Clock")
    table.add_column("Timezone")
    table.add_column("Current Time")
    table.add_column("Offset")

    utc_now = datetime.now(pytz.UTC)

    for zone in zones:
        try:
            tz = pytz.timezone(zone)
            local_time = utc_now.astimezone(tz)
            offset = local_time.strftime("%z")
            time_str = local_time.strftime("%H:%M:%S")
            table.add_row(zone, time_str, offset)
        except Exception as e:
            table.add_row(zone, f"[red]Error: {e}[/red]", "-")

    console.print(table)


# Pomodoro command
@app.command()
def pomodoro(
    work: Annotated[
        int,
        typer.Option("--work", "-w", help="Work duration in minutes"),
    ] = 25,
    break_duration: Annotated[
        int,
        typer.Option("--break", "-b", help="Break duration in minutes"),
    ] = 5,
    sessions: Annotated[
        int,
        typer.Option("--sessions", "-s", help="Number of work sessions"),
    ] = 4,
) -> None:
    """Start a Pomodoro timer.

    Examples:
        wake pomodoro
        wake pomodoro --work 50 --break 10
        wake pomodoro --sessions 2
    """
    from wakepy.timer import PomodoroTimer

    pomodoro = PomodoroTimer(
        work_minutes=work,
        break_minutes=break_duration,
        sessions=sessions,
    )
    pomodoro.run()


# Statistics command
@app.command("stats")
def stats_cmd(
    reset: Annotated[bool, typer.Option("--reset", help="Reset all statistics")] = False,
    history: Annotated[
        int,
        typer.Option("--history", "-h", help="Show N recent history entries"),
    ] = 0,
) -> None:
    """Show alarm statistics.

    Examples:
        wake stats
        wake stats --history 5
        wake stats --reset
    """
    from wakepy.statistics import Statistics

    cfg = get_global_config()
    stats_file = cfg.get("advanced", "stats_file", default="~/.wakepy/statistics.json")

    stats = Statistics(stats_file)

    if reset:
        if typer.confirm("Are you sure you want to reset all statistics?"):
            stats.reset()
        return

    if history > 0:
        entries = stats.get_history(history)
        if entries:
            console.print(f"[bold]Recent History (last {len(entries)}):[/bold]")
            for entry in reversed(entries):
                timestamp = entry.get("timestamp", "")[:19]
                event_type = entry.get("type", "unknown")
                alarm_name = entry.get("alarm_name", "Unknown")
                console.print(f"  [{timestamp}] {event_type.title()}: {alarm_name}")
        else:
            console.print("No history available")
    else:
        stats.display_summary()


# Export command
@app.command("export")
def export_cmd(
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Export format (yaml or json)"),
    ] = "yaml",
) -> None:
    """Export alarms to a file.

    Examples:
        wake export
        wake export --output backup.yaml
        wake export --format json --output backup.json
    """
    from wakepy.import_export import ImportExport

    cfg = get_global_config()
    alarms_file = cfg.storage_file

    ImportExport.export_alarms(alarms_file, output, format)


# Import command
@app.command("import")
def import_cmd(
    import_file: Annotated[str, typer.Argument(help="File to import from")],
    merge: Annotated[
        bool,
        typer.Option("--merge/--replace", help="Merge with existing or replace all"),
    ] = True,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be imported without importing"),
    ] = False,
) -> None:
    """Import alarms from a file.

    Examples:
        wake import backup.yaml
        wake import backup.yaml --replace
        wake import backup.yaml --dry-run
    """
    from wakepy.import_export import ImportExport

    cfg = get_global_config()
    alarms_file = cfg.storage_file

    ImportExport.import_alarms(import_file, alarms_file, merge, dry_run)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
