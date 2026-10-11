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

colorized_echo() {
    local color=$1
    local text=$2
    case $color in
        red) printf "\e[91m%s\e[0m\n" "$text" ;;
        green) printf "\e[92m%s\e[0m\n" "$text" ;;
        yellow) printf "\e[93m%s\e[0m\n" "$text" ;;
        blue) printf "\e[94m%s\e[0m\n" "$text" ;;
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

usage() {
    cat <<EOF
Usage: marzbanx COMMAND [args]

  up              Start MarzbanX (docker compose up -d)
  down            Stop and remove the container
  restart         Restart the running container
  status          Show container status
  logs [args]     Follow container logs (passed to docker compose logs)
  cli [args]      Run marzban-cli inside the container, e.g.:
                    marzbanx cli admin create --sudo
                    marzbanx cli admin list
  update          git pull, rebuild the image, restart
  build           Rebuild the image without pulling
  edit            Edit docker-compose.yml
  edit-env        Edit .env
  backup          Tar up /var/lib/marzban and .env into a timestamped archive
  help            Show this message
EOF
}

case "$1" in
    up)
        cd_app_dir
        rescue_legacy_state
        $COMPOSE up -d
        ;;
    down)
        cd_app_dir
        $COMPOSE down
        ;;
    restart)
        cd_app_dir
        $COMPOSE restart
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
        $COMPOSE up -d
        colorized_echo green "Done."
        ;;
    build)
        cd_app_dir
        $COMPOSE build
        ;;
    edit)
        cd_app_dir
        "${EDITOR:-nano}" docker-compose.yml
        ;;
    edit-env)
        cd_app_dir
        "${EDITOR:-nano}" .env
        ;;
    backup)
        cd_app_dir
        dest="${MARZBANX_BACKUP_DIR:-/opt/marzbanx-backups}"
        mkdir -p "$dest"
        archive="$dest/marzbanx-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
        tar czf "$archive" "$DATA_DIR" "$APP_DIR/.env"
        colorized_echo green "Backup saved to $archive"
        ;;
    help|""|*)
        usage
        ;;
esac
