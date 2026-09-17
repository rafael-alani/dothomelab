function kew --description 'Open Kew after restoring the homelab music share'
    switch "$argv[1]"
        case -h --help -v --version path theme
            command kew $argv
            return $status
    end
    if not "$HOME/Library/Application Support/dothomelab-media/media-reconnect"
        echo 'Music share unavailable. Reconnect to the home LAN and try kew again.' >&2
        return 1
    end
    command kew $argv
end
