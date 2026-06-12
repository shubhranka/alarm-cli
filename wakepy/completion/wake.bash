# Bash completion for wakepy

_wake_completion() {
    local cur prev words cword
    _init_completion || return

    # Commands
    local commands="init create list show edit delete enable disable start stop status restart test-email test-twilio test-webhook config version timer stopwatch worldclock pomodoro stats export import"

    # Timer subcommands
    local timer_actions="start stop reset status"

    # Check if we're completing a command
    if [[ ${COMP_WORDS[1]} == "" ]] || [[ ${COMP_WORDS[1]} == "help" ]]; then
        COMPREPLY=($(compgen -W "$commands" -- "${cur}"))
        return
    fi

    # Command-specific completions
    case "${COMP_WORDS[1]}" in
        create)
            COMPREPLY=($(compgen -W "--name --repeat --days --snooze --sound --email --sms --call --webhook --slack-webhook --one-time --tags --timezone" -- "${cur}"))
            ;;
        edit|show|delete|enable|disable)
            # Suggest alarm IDs (if we could list them)
            COMPREPLY=($(compgen -W "--name --time --repeat --snooze --tags --add-tags --remove-tags" -- "${cur}"))
            ;;
        list)
            COMPREPLY=($(compgen -W "--verbose --tag --enabled --disabled" -- "${cur}"))
            ;;
        timer)
            COMPREPLY=($(compgen -W "--name --silent" -- "${cur}"))
            ;;
        stopwatch)
            COMPREPLY=($(compgen -W "start stop reset status" -- "${cur}"))
            ;;
        worldclock)
            COMPREPLY=($(compgen -W "--add --list" -- "${cur}"))
            ;;
        pomodoro)
            COMPREPLY=($(compgen -W "--work --break --sessions" -- "${cur}"))
            ;;
        stats)
            COMPREPLY=($(compgen -W "--reset --history" -- "${cur}"))
            ;;
        export)
            COMPREPLY=($(compgen -W "--output --format" -- "${cur}"))
            ;;
        import)
            COMPREPLY=($(compgen -W "--merge --replace --dry-run" -- "${cur}"))
            ;;
        config)
            COMPREPLY=($(compgen -W "--key --value" -- "${cur}"))
            ;;
        start)
            COMPREPLY=($(compgen -W "--foreground" -- "${cur}"))
            ;;
        test-webhook)
            COMPREPLY=($(compgen -W "--platform" -- "${cur}"))
            ;;
        test-email|test-twilio)
            # No specific options
            ;;
        *)
            ;;
    esac
}

complete -F _wake_completion wake
