#!/bin/bash
# MarzbanX management CLI.
# Adapted from Gozargah/Marzban-scripts' marzban.sh, trimmed down to what
# this fork actually needs: a single Docker Compose service, SQLite only,
# no multi-distro package management.

set -e

APP_DIR="${MARZBANX_DIR:-/opt/marzbanx}"
# Must match the host side of the volume in docker-compose.yml
DATA_DIR="/var/lib/marzban"
COMPOSE="docker compose"
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"

colorized_echo() {
    local color=$1
    local text=$2
    case $color in
        red) printf "\e[91m%s\e[0m\n" "$text" ;;
        green) printf "\e[92m%s\e[0m\n" "$text" ;;
        yellow) printf "\e[93m%s\e[0m\n" "$text" ;;
        blue) printf "\e[94m%s\e[0m\n" "$text" ;;
        magenta) printf "\e[95m%s\e[0m\n" "$text" ;;
        cyan) printf "\e[96m%s\e[0m\n" "$text" ;;
        *) echo "$text" ;;
    esac
}

cd_app_dir() {
    if [ ! -d "$APP_DIR" ]; then
        colorized_echo red "MarzbanX directory not found at $APP_DIR (set MARZBANX_DIR to override)"
        exit 1
    fi
    cd "$APP_DIR"
}

# Versions before the /var/lib/marzban defaults kept the Xray config and the
# SQLite database under /code inside the container. Copy them out of the
# existing container before it gets recreated, unless the host already has
# them -- after that the app reads only from the volume.
rescue_legacy_state() {
    mkdir -p "$DATA_DIR"
    local f
    for f in xray_config.json db.sqlite3; do
        [ -e "$DATA_DIR/$f" ] && continue
        if $COMPOSE cp "marzban:/code/$f" "$DATA_DIR/$f" 2>/dev/null; then
            colorized_echo yellow "Copied $f out of the existing container into $DATA_DIR"
        fi
    done
}

# Starts the container, waits (up to a minute) until the panel has finished
# starting or crashed, then shows the last lines of its log.
up_and_show_logs() {
    local since i
    since="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    $COMPOSE up -d
    colorized_echo blue "Waiting for MarzbanX to start..."
    for i in $(seq 60); do
        $COMPOSE logs --since "$since" marzban 2>/dev/null \
            | grep -qE "Application startup complete|Traceback" && break
        sleep 1
    done
    $COMPOSE logs --tail 40 marzban
}

edit_file() {
    "${EDITOR:-$(command -v nano || echo vi)}" "$1"
}

usage() {
    local line="=============================================="
    colorized_echo cyan "$line"
    colorized_echo magenta "               MarzbanX Help"
    colorized_echo cyan "$line"
    colorized_echo cyan "Usage:"
    echo "  marzbanx [command]"
    echo
    colorized_echo cyan "Commands:"
    local cmd desc
    while IFS='|' read -r cmd desc; do
        printf "  \e[93m%-16s\e[0m– %s\n" "$cmd" "$desc"
    done <<'EOF'
up|Start services
down|Stop services
restart|Restart services (re-reads .env)
status|Show status
logs|Show logs (follow)
cli|MarzbanX CLI, e.g. marzbanx cli admin list
update|Update to latest version (git pull, rebuild, restart)
build|Rebuild the image without pulling
backup|Manual backup of the data directory and .env
install-script|Install the marzbanx command into /usr/local/bin
edit|Edit docker-compose.yml (via nano or vi editor)
edit-env|Edit environment file (via nano or vi editor)
help|Show this help message
EOF
    echo
    colorized_echo cyan "Directories:"
    colorized_echo magenta "  App directory: $APP_DIR"
    colorized_echo magenta "  Data directory: $DATA_DIR"
    colorized_echo cyan "$line"
}

case "$1" in
    up)
        cd_app_dir
        rescue_legacy_state
        up_and_show_logs
        ;;
    down)
        cd_app_dir
        rescue_legacy_state
        $COMPOSE down
        ;;
    restart)
        cd_app_dir
        rescue_legacy_state
        $COMPOSE down
        up_and_show_logs
        ;;
    status)
        cd_app_dir
        $COMPOSE ps
        ;;
    logs)
        cd_app_dir
        shift
        $COMPOSE logs -f --tail 200 "$@"
        ;;
    cli)
        cd_app_dir
        shift
        $COMPOSE exec marzban marzban-cli "$@"
        ;;
    update)
        cd_app_dir
        colorized_echo blue "Pulling latest changes..."
        git pull
        colorized_echo blue "Rebuilding image..."
        $COMPOSE build
        rescue_legacy_state
        colorized_echo blue "Restarting..."
        up_and_show_logs
        ;;
    build)
        cd_app_dir
        $COMPOSE build
        ;;
    edit)
        cd_app_dir
        edit_file docker-compose.yml
        ;;
    edit-env)
        cd_app_dir
        edit_file .env
        ;;
    backup)
        cd_app_dir
        dest="${MARZBANX_BACKUP_DIR:-/opt/marzbanx-backups}"
        mkdir -p "$dest"
        archive="$dest/marzbanx-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
        tar czf "$archive" "$DATA_DIR" "$APP_DIR/.env"
        colorized_echo green "Backup saved to $archive"
        ;;
    install-script)
        if [ "$(id -u)" -ne 0 ]; then
            colorized_echo red "Run as root: sudo bash $SCRIPT_PATH install-script"
            exit 1
        fi
        chmod +x "$SCRIPT_PATH"
        ln -sf "$SCRIPT_PATH" /usr/local/bin/marzbanx
        colorized_echo green "Installed: /usr/local/bin/marzbanx -> $SCRIPT_PATH"
        ;;
    help|"")
        usage
        ;;
    *)
        colorized_echo red "Unknown command: $1"
        usage
        exit 1
        ;;
esac
