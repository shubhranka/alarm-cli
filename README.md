# Wakepy

> A comprehensive alarm clock CLI with email, SMS, voice, and webhook notifications

Wakepy is a powerful command-line alarm clock that runs in the background and can notify you through multiple channels when your alarms go off.

## Features

- 🕐 **Flexible Time Input**: `08:00`, `8:00am`, `in 30m`, `in 1h 30m`
- 🔁 **Repeat Patterns**: Once, daily, weekdays, weekends, or custom days
- 🏷️ **Tags & Groups**: Organize alarms with tags
- 🔔 **Multiple Notifications**: Email, SMS, voice calls, Discord, Slack
- 🖥️ **Desktop Notifications**: Native OS notifications
- ⏱️ **Timers**: Countdown, stopwatch, Pomodoro, world clock
- 📊 **Statistics**: Track alarm triggers and snoozes
- 💾 **Import/Export**: Backup and restore alarm configurations
- 🔄 **Background Daemon**: Runs as a background service
- 💾 **Persistent Storage**: Alarms saved across restarts

## Installation

```bash
pip install wakepy
```

## Quick Start

1. Initialize configuration:
```bash
wake init
```

2. Start the daemon:
```bash
wake start
```

3. Create your first alarm:
```bash
wake create 08:00 --name "Wake up"
```

## Commands

### Core Commands

| Command | Description |
|---------|-------------|
| `wake init` | Initialize configuration |
| `wake create <time>` | Create a new alarm |
| `wake list` | List all alarms |
| `wake show <id>` | Show alarm details |
| `wake edit <id>` | Edit an alarm |
| `wake delete <id>` | Delete an alarm |
| `wake enable <id>` | Enable an alarm |
| `wake disable <id>` | Disable an alarm |

### Daemon Commands

| Command | Description |
|---------|-------------|
| `wake start` | Start the daemon |
| `wake stop` | Stop the daemon |
| `wake restart` | Restart the daemon |
| `wake status` | Show daemon status |

### Test Commands

| Command | Description |
|---------|-------------|
| `wake test-email <addr>` | Test email configuration |
| `wake test-twilio` | Test Twilio configuration |
| `wake test-webhook <url>` | Test webhook configuration |

### Timer Commands

| Command | Description |
|---------|-------------|
| `wake timer <duration>` | Countdown timer |
| `wake stopwatch` | Stopwatch (start/stop/reset) |
| `wake worldclock` | World clock in multiple timezones |
| `wake pomodoro` | Pomodoro technique timer |

### Utility Commands

| Command | Description |
|---------|-------------|
| `wake stats` | Show alarm statistics |
| `wake export` | Export alarms to file |
| `wake import <file>` | Import alarms from file |
| `wake config` | Show/set configuration |

## Shell Completion

Install shell completion for better CLI experience:

### Bash
```bash
# Add to ~/.bashrc or ~/.bash_completion.d/wake.sh
wake completion bash > ~/.bash_completion.d/wake.sh
source ~/.bash_completion.d/wake.sh
```

### Zsh
```bash
# Add to ~/.zfunc/_wake
wake completion zsh > ~/.zfunc/_wake

# Add to ~/.zshrc
fpath=(~/.zfunc $fpath)
autoload -U compinit && compinit
```

## Examples

### Basic Alarm

```bash
wake create 08:00 --name "Morning alarm"
```

### Relative Time

```bash
wake create "in 30m" --name "Reminder"
wake create "in 1h 30m" --name "Meeting"
```

### Repeating Alarms

```bash
# Daily
wake create 08:00 --repeat daily

# Weekdays only
wake create 09:00 --repeat weekdays

# Custom days
wake create 10:00 --repeat custom --days mon,wed,fri
```

### With Notifications

```bash
# Email
wake create 08:00 --email me@example.com

# SMS (requires Twilio)
wake create 08:00 --sms +1234567890

# Voice call (requires Twilio)
wake create 08:00 --call +1234567890

# Discord webhook
wake create 08:00 --webhook https://discord.com/api/webhooks/...

# Multiple notifications
wake create 08:00 --email me@example.com --sms +1234567890
```

### Managing Alarms

```bash
# List all alarms
wake list

# Show details
wake show abc12345

# Edit alarm
wake edit abc12345 --time 09:00

# Disable temporarily
wake disable abc12345

# Delete
wake delete abc12345
```

## Configuration

Configuration is stored in `~/.wakepy/config.yaml`. Run `wake init` to create it.

### Email Configuration

For Gmail, use an App Password:
1. Go to https://myaccount.google.com/apppasswords
2. Generate an app password
3. Add to config or environment variable:

```yaml
email:
  enabled: true
  smtp_server: smtp.gmail.com
  smtp_port: 587
  username: your-email@gmail.com
  password: ${ALARM_EMAIL_PASSWORD}  # Or set in env
```

### Twilio Configuration

```yaml
twilio:
  enabled: true
  account_sid: ${TWILIO_ACCOUNT_SID}
  auth_token: ${TWILIO_AUTH_TOKEN}
  from_number: ${TWILIO_FROM_NUMBER}
```

Set environment variables or edit config directly.

## Development

```bash
# Clone and install
git clone https://github.com/yourusername/wakepy
cd wakepy
pip install -e .

# Run tests
pytest

# Run in development mode
wake start --foreground
```

## License

MIT License - see LICENSE file for details.
