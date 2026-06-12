# zsh completion for wakepy

_wake() {
    local -a commands
    commands=(
        'init:Initialize configuration'
        'create:Create a new alarm'
        'list:List all alarms'
        'show:Show alarm details'
        'edit:Edit an alarm'
        'delete:Delete an alarm'
        'enable:Enable an alarm'
        'disable:Disable an alarm'
        'start:Start daemon'
        'stop:Stop daemon'
        'status:Show daemon status'
        'restart:Restart daemon'
        'test-email:Test email configuration'
        'test-twilio:Test Twilio configuration'
        'test-webhook:Test webhook'
        'config:Show/set configuration'
        'version:Show version'
        'timer:Countdown timer'
        'stopwatch:Stopwatch'
        'worldclock:World clock'
        'pomodoro:Pomodoro timer'
        'stats:Statistics'
        'export:Export alarms'
        'import:Import alarms'
    )

    if (( CURRENT == 2 )); then
        _describe 'command' commands
    else
        case $words[2] in
            create)
                _arguments -s \
                    '--name[Alarm name]' \
                    '--repeat[Repeat pattern:once,daily,weekdays,weekends,custom]' \
                    '--days[Days for custom repeat]' \
                    '--snooze[Snooze duration in minutes]' \
                    '--sound[Sound file name]' \
                    '--email[Email recipient]' \
                    '--sms[SMS recipient]' \
                    '--call[Call recipient]' \
                    '--webhook[Webhook URL]' \
                    '--slack-webhook[Slack webhook URL]' \
                    '--one-time[Delete after triggering]' \
                    '--tags[Comma-separated tags]' \
                    '--timezone[Timezone]' \
                    ':time:HH:MM or "in Xm"'
                ;;
            list)
                _arguments -s \
                    '--verbose[Show detailed info]' \
                    '--tag[Filter by tag]' \
                    '--enabled[Show only enabled]' \
                    '--disabled[Show only disabled]'
                ;;
            edit|show|delete|enable|disable)
                _arguments -s \
                    '--name[Alarm name]' \
                    '--time[Alarm time]' \
                    '--repeat[Repeat pattern]' \
                    '--snooze[Snooze duration]' \
                    '--tags[Replace tags]' \
                    '--add-tags[Add tags]' \
                    '--remove-tags[Remove tags]' \
                    ':alarm_id:Alarm ID'
                ;;
            start)
                _arguments -s '--foreground[Run in foreground]'
                ;;
            timer)
                _arguments -s \
                    '--name[Timer name]' \
                    '--silent[Run without progress bar]' \
                    ':duration:5m, 1h, etc.'
                ;;
            stopwatch)
                _values 'action' start stop reset status
                ;;
            worldclock)
                _arguments \
                    '--add[Add timezone]' \
                    '--list[List available timezones]'
                ;;
            pomodoro)
                _arguments -s \
                    '--work[Work duration in minutes]: :(25 50 45)' \
                    '--break[Break duration in minutes]: :(5 10 15)' \
                    '--sessions[Number of sessions]: :(2 4 6 8)'
                ;;
            stats)
                _arguments -s \
                    '--reset[Reset statistics]' \
                    '--history[Show N history entries]'
                ;;
            export)
                _arguments -s \
                    '--output[Output file]' \
                    '--format[Export format]:(yaml json)'
                ;;
            import)
                _arguments -s \
                    '--merge[Merge with existing]' \
                    '--replace[Replace all alarms]' \
                    '--dry-run[Preview import]' \
                    ':import_file:Import file'
                ;;
            config)
                _arguments -s \
                    '--key[Config key]' \
                    '--value[Config value]'
                ;;
            test-webhook)
                _arguments -s '--platform[Platform]:(auto discord slack generic)'
                ;;
            test-email)
                ':recipient:Email address'
                ;;
        esac
    fi
}

_wake
