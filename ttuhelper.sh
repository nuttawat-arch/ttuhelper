#!/usr/bin/env bash
set -Eeuo pipefail

HELPER_VERSION="1.5.0"
CONFIG_FILE="${TTU_HELPER_CONFIG:-/etc/default/ttuhelper}"
if [[ -r "$CONFIG_FILE" ]]; then
  # shellcheck disable=SC1090
  . "$CONFIG_FILE"
fi

IMAGE_REPO="${TTU_IMAGE_REPO:-nuttawat0295/sntalkbot}"
IMAGE_TAG="${TTU_TAG:-latest}"
IMAGE_NAME="${IMAGE_REPO}:${IMAGE_TAG}"
API_PORT_MIN="${TTU_API_PORT_MIN:-20000}"
API_PORT_MAX="${TTU_API_PORT_MAX:-27999}"
LEGACY_BOTS_ROOT="/opt/ttutilities-bots"
DEFAULT_BOTS_ROOT="/opt/sntalkbot-bots"
if [[ -n "${TTU_BOTS_ROOT:-}" ]]; then
  BOTS_ROOT="$TTU_BOTS_ROOT"
elif [[ -d "$LEGACY_BOTS_ROOT" && ! -e "$DEFAULT_BOTS_ROOT" ]]; then
  BOTS_ROOT="$LEGACY_BOTS_ROOT"
else
  BOTS_ROOT="$DEFAULT_BOTS_ROOT"
fi
LABEL_KEY="com.ttutilities.helper"
LABEL_VALUE="true"
BOT_LABEL="com.ttutilities.bot"
DATA_LABEL="com.ttutilities.data"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATOR_PATH="${TTU_MIGRATOR_PATH:-/usr/local/lib/ttuhelper/migrate_ttmediabot.py}"
if [[ ! -f "$MIGRATOR_PATH" && -f "$SCRIPT_DIR/tools/migrate_ttmediabot.py" ]]; then
  MIGRATOR_PATH="$SCRIPT_DIR/tools/migrate_ttmediabot.py"
fi

say() { printf '%s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
command_exists() { command -v "$1" >/dev/null 2>&1; }

need_root() {
  [[ "$EUID" -eq 0 ]] || fail "Please run with sudo/root, for example: sudo ttuhelper $*"
}

validate_name() {
  local name="$1"
  [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$ ]] || \
    fail "Bot name must start with a letter/number and contain only A-Z, a-z, 0-9, _, . or - (max 63 chars; no spaces/slashes)."
}

bot_dir() { printf '%s/%s' "$BOTS_ROOT" "$1"; }

conf_get() {
  local file="$1" key="$2"
  [[ -r "$file" ]] || return 0
  awk -F= -v k="$key" '$1==k {sub(/^[^=]*=/, ""); print; exit}' "$file"
}

conf_set() {
  local file="$1" key="$2" value="$3" tmp
  tmp="$(mktemp)"
  if [[ -f "$file" ]]; then
    awk -F= -v k="$key" '$1!=k {print}' "$file" > "$tmp"
  fi
  printf '%s=%s\n' "$key" "$value" >> "$tmp"
  install -m 0640 "$tmp" "$file"
  rm -f "$tmp"
}

port_is_free() {
  python3 - "$1" <<'PYPORT'
import socket, sys
port=int(sys.argv[1])
s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(('127.0.0.1', port))
except OSError:
    raise SystemExit(1)
finally:
    s.close()
PYPORT
}

allocate_api_port() {
  TTU_BOTS_ROOT_PY="$BOTS_ROOT" TTU_API_MIN_PY="$API_PORT_MIN" TTU_API_MAX_PY="$API_PORT_MAX" python3 <<'PYPORT'
import configparser, os, random, socket
from pathlib import Path
root=Path(os.environ['TTU_BOTS_ROOT_PY'])
lo=int(os.environ['TTU_API_MIN_PY']); hi=int(os.environ['TTU_API_MAX_PY'])
if not (1024 <= lo <= hi <= 65535):
    raise SystemExit('invalid TTU API port range')
reserved=set()
for f in root.glob('*/instance.conf') if root.exists() else []:
    for line in f.read_text(encoding='utf-8', errors='ignore').splitlines():
        if line.startswith('api_port='):
            try: reserved.add(int(line.split('=',1)[1]))
            except ValueError: pass
ports=list(range(lo, hi+1)); random.SystemRandom().shuffle(ports)
for port in ports:
    if port in reserved: continue
    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', port))
    except OSError:
        s.close(); continue
    s.close(); print(port); raise SystemExit(0)
raise SystemExit('no free API port in configured range')
PYPORT
}

generate_api_token() { python3 - <<'PYTOKEN'
import secrets
print(secrets.token_urlsafe(48))
PYTOKEN
}

ensure_api_metadata() {
  local name="$1" dir="$2" conf="$dir/instance.conf" port token
  api_lock_acquire
  port="$(conf_get "$conf" api_port || true)"
  token="$(conf_get "$conf" api_token || true)"
  if [[ ! "$port" =~ ^[0-9]+$ ]] || (( port < API_PORT_MIN || port > API_PORT_MAX )); then
    port="$(allocate_api_port)"
    conf_set "$conf" api_port "$port"
  elif ! port_is_free "$port"; then
    # A running container legitimately owns its port. For a stopped/recreated
    # instance an occupied port belongs to something else, so choose a new one.
    if ! docker container inspect "$name" >/dev/null 2>&1 || [[ "$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null || true)" != "true" ]]; then
      port="$(allocate_api_port)"
      conf_set "$conf" api_port "$port"
    fi
  fi
  if [[ -z "$token" ]]; then
    token="$(generate_api_token)"
    conf_set "$conf" api_token "$token"
  fi
  conf_set "$conf" api_bind "127.0.0.1"
  chmod 0640 "$conf"
  API_PORT="$port"
  API_TOKEN="$token"
  api_lock_release
}

ensure_layout() {
  mkdir -p "$BOTS_ROOT"
  chown root:10001 "$BOTS_ROOT" 2>/dev/null || true
  chmod 2770 "$BOTS_ROOT"
}

api_lock_acquire() {
  mkdir -p /run/lock
  exec 9>/run/lock/ttuhelper-api.lock
  flock -x 9
}

api_lock_release() {
  flock -u 9 || true
  exec 9>&-
}

ensure_python() {
  command_exists python3 || fail "python3 is required. Run the helper installer first: sudo ./install.sh"
}

ensure_docker_running() {
  command_exists docker || fail "Docker is not installed. Run: sudo ./install.sh"
  if command_exists systemctl && ! systemctl is-active --quiet docker; then
    systemctl start docker
  fi
  docker info >/dev/null 2>&1 || fail "Docker daemon is unavailable."
}

pull_image() {
  say "Pulling $IMAGE_NAME ..."
  docker pull "$IMAGE_NAME"
}

ensure_image() {
  if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    pull_image
  fi
}

make_empty_cookie_file() {
  local path="$1"
  cat > "$path" <<'COOKIES'
# Netscape HTTP Cookie File
# This file may be replaced with cookies exported in Netscape format.
COOKIES
}

configure_from_template() {
  local path="$1"
  TTU_CFG="$path" \
  TTU_HOSTNAME="$2" TTU_TCP="$3" TTU_UDP="$4" TTU_ENCRYPTED="$5" \
  TTU_NICKNAME="$6" TTU_USERNAME="$7" TTU_PASSWORD="$8" \
  TTU_CHANNEL="$9" TTU_CHANNEL_PASSWORD="${10}" TTU_AUTHORIZED_USERS="${11}" \
  TTU_PLAYER_ENABLED="${12}" TTU_SERVER_MANAGEMENT_ENABLED="${13}" \
  python3 <<'PY'
import configparser, os
from pathlib import Path
path = Path(os.environ['TTU_CFG'])
cfg = configparser.ConfigParser(interpolation=None)
with path.open('r', encoding='utf-8') as f:
    cfg.read_file(f)

def ensure(section):
    if not cfg.has_section(section):
        cfg.add_section(section)

def setv(section, key, value):
    ensure(section)
    cfg.set(section, key, str(value))

setv('server', 'address', os.environ['TTU_HOSTNAME'])
setv('server', 'tcp_port', os.environ['TTU_TCP'])
setv('server', 'udp_port', os.environ['TTU_UDP'])
setv('server', 'encrypted', os.environ['TTU_ENCRYPTED'])
setv('server', 'username', os.environ['TTU_USERNAME'])
setv('server', 'password', os.environ['TTU_PASSWORD'])
setv('bot', 'language', 'th')
setv('bot', 'nickname', os.environ['TTU_NICKNAME'])
setv('bot', 'default_channel', os.environ['TTU_CHANNEL'])
setv('bot', 'channel_password', os.environ['TTU_CHANNEL_PASSWORD'])
setv('accounts', 'authorized_users', os.environ['TTU_AUTHORIZED_USERS'])
setv('accounts', 'detect_server_admins', 'True')
setv('features', 'player_enabled', os.environ['TTU_PLAYER_ENABLED'])
setv('features', 'server_management_enabled', os.environ['TTU_SERVER_MANAGEMENT_ENABLED'])
if os.environ['TTU_SERVER_MANAGEMENT_ENABLED'].strip().lower() not in ('1','true','yes','on'):
    setv('bot', 'intercept_channel_messages', 'False')
    setv('bot', 'welcome_broadcast', 'False')
    setv('bot', 'welcome_mode', '0')
    setv('bot', 'profanity_filter_enabled', 'False')
setv('playback', 'input_device', 'auto')
setv('playback', 'output_device', 'auto')
setv('playback', 'cookiefile_path', '/app/data/cookies.txt')
setv('playback', 'announce_tracks', 'True')
setv('playback', 'announce_queue', 'True')
setv('playback', 'announcement_voice', 'th-TH-PremwadeeNeural')
with path.open('w', encoding='utf-8') as f:
    cfg.write(f)
PY
}

create_bot() {
  ensure_image
  ensure_python
  local name nickname hostname tcp udp encrypted username password channel channel_password authorized answer dir tmp mode_choice player_enabled server_management_enabled mode_name

  read -rp "Bot/instance name: " name
  [[ -n "$name" ]] || fail "Bot name cannot be empty."
  validate_name "$name"
  dir="$(bot_dir "$name")"
  [[ ! -e "$dir" ]] || fail "Instance '$name' already exists at $dir"

  read -rp "Nickname (default: TTUtilities): " nickname; nickname="${nickname:-TTUtilities}"
  read -rp "TeamTalk hostname/IP: " hostname; [[ -n "$hostname" ]] || fail "Hostname is required."
  read -rp "TCP port (default: 10333): " tcp; tcp="${tcp:-10333}"
  read -rp "UDP port (default: 10333): " udp; udp="${udp:-10333}"
  read -rp "Encrypted TeamTalk connection? [y/N]: " answer
  case "${answer,,}" in y|yes) encrypted=True ;; *) encrypted=False ;; esac
  read -rp "TeamTalk username (optional): " username
  read -rsp "TeamTalk password (optional): " password; echo
  read -rp "Channel path (default: /): " channel; channel="${channel:-/}"
  read -rsp "Channel password (optional): " channel_password; echo
  read -rp "Bot admin usernames, comma-separated (optional): " authorized

  say "Choose bot mode:"
  say "  1) Full Bot        - Player + Server Management"
  say "  2) Player Bot      - Music/queue features only"
  say "  3) Server Manager  - Server-management features only"
  read -rp "Mode [1/2/3] (default: 1): " mode_choice
  case "${mode_choice:-1}" in
    1) player_enabled=True; server_management_enabled=True; mode_name='full' ;;
    2) player_enabled=True; server_management_enabled=False; mode_name='player' ;;
    3) player_enabled=False; server_management_enabled=True; mode_name='manager' ;;
    *) fail "Invalid mode. Please choose 1, 2, or 3." ;;
  esac

  tmp="$(mktemp -d)"
  docker run --rm --entrypoint cat "$IMAGE_NAME" /app/config_default.ini > "$tmp/config.ini"
  configure_from_template "$tmp/config.ini" "$hostname" "$tcp" "$udp" "$encrypted" "$nickname" "$username" "$password" "$channel" "$channel_password" "$authorized" "$player_enabled" "$server_management_enabled"
  make_empty_cookie_file "$tmp/cookies.txt"

  mkdir -p "$dir"
  install -m 0640 "$tmp/config.ini" "$dir/config.ini"
  install -m 0640 "$tmp/cookies.txt" "$dir/cookies.txt"
  api_lock_acquire
  api_port_new="$(allocate_api_port)"
  api_token_new="$(generate_api_token)"
  cat > "$dir/instance.conf" <<CONF
image=$IMAGE_NAME
created=$(date -Is)
mode=$mode_name
player_enabled=$player_enabled
server_management_enabled=$server_management_enabled
api_port=$api_port_new
api_token=$api_token_new
api_bind=127.0.0.1
CONF
  api_lock_release
  chown -R 10001:10001 "$dir"
  chmod 2770 "$dir"
  chmod 0660 "$dir/config.ini"
  chmod 0640 "$dir/cookies.txt" "$dir/instance.conf"
  rm -rf "$tmp"

  say "Created instance: $name"
  say "Data directory: $dir"
  say "Run it with: sudo ttuhelper run $name"
}

read_limits() {
  local dir="$1" cpu="" memory=""
  LIMIT_ARGS=()
  if [[ -r "$dir/limits.conf" ]]; then
    while IFS='=' read -r k v; do
      case "$k" in
        cpu) cpu="$v" ;;
        memory) memory="$v" ;;
      esac
    done < "$dir/limits.conf"
  fi
  if [[ -n "$cpu" ]]; then LIMIT_ARGS+=(--cpus "$cpu"); fi
  if [[ -n "$memory" ]]; then LIMIT_ARGS+=(--memory "$memory"); fi
  return 0
}

run_bot() {
  local name="$1" force="${2:-0}" dir sink
  [[ -n "$name" ]] || fail "Usage: ttuhelper run <name>"
  validate_name "$name"
  dir="$(bot_dir "$name")"
  [[ -d "$dir" && -f "$dir/config.ini" ]] || fail "Instance '$name' not found in $BOTS_ROOT"
  ensure_image

  if docker container inspect "$name" >/dev/null 2>&1; then
    if [[ "$force" == "1" ]]; then
      docker rm -f "$name" >/dev/null
    elif [[ "$(docker inspect -f '{{.State.Running}}' "$name")" == "true" ]]; then
      say "Instance '$name' is already running."
      return 0
    else
      docker rm "$name" >/dev/null
    fi
  fi

  chown -R 10001:10001 "$dir"
  chmod 2770 "$dir"
  [[ -f "$dir/config.ini" ]] && chmod 0660 "$dir/config.ini"
  ensure_api_metadata "$name" "$dir"
  # instance.conf contains the local API token and stays local to the host.
  chmod 0640 "$dir/instance.conf"
  read_limits "$dir"
  sink="ttu_${name//[^A-Za-z0-9_]/_}"

  docker run -d \
    --name "$name" \
    --network host \
    --restart unless-stopped \
    --label "$LABEL_KEY=$LABEL_VALUE" \
    --label "$BOT_LABEL=$name" \
    --label "$DATA_LABEL=$dir" \
    "${LIMIT_ARGS[@]}" \
    -v "$dir:/app/data" \
    -e TTUTIL_CONFIG=/app/data/config.ini \
    -e TTUTIL_DATA_DIR=/app/data \
    -e "TTUTIL_PULSE_SINK=$sink" \
    -e TTUTIL_MPV_AO=pulse \
    -e SNTALKBOT_API_BIND=127.0.0.1 \
    -e "SNTALKBOT_API_PORT=$API_PORT" \
    -e "SNTALKBOT_API_TOKEN=$API_TOKEN" \
    "$IMAGE_NAME" >/dev/null

  say "Started '$name' with image $IMAGE_NAME"
  say "Local realtime API: 127.0.0.1:$API_PORT (loopback only)"
  say "Logs: sudo ttuhelper logs $name"
}

stop_bot() {
  local name="$1"
  [[ -n "$name" ]] || fail "Usage: ttuhelper stop <name>"
  if docker container inspect "$name" >/dev/null 2>&1; then
    docker rm -f "$name" >/dev/null
    say "Stopped and removed container '$name'. Persistent data was kept."
  else
    say "Container '$name' is not running/created. Persistent data was not changed."
  fi
}

restart_bot() {
  local name="$1"
  [[ -n "$name" ]] || fail "Usage: ttuhelper restart <name>"
  stop_bot "$name"
  run_bot "$name" 1
}

delete_bot() {
  local name="$1" yes="${2:-}" dir real_root real_dir backup_root backup
  [[ -n "$name" ]] || fail "Usage: ttuhelper delete <name> [--yes]"
  validate_name "$name"
  dir="$(bot_dir "$name")"
  [[ -d "$dir" && ! -L "$dir" ]] || fail "Instance '$name' not found."
  real_root="$(realpath -m "$BOTS_ROOT")"
  real_dir="$(realpath -m "$dir")"
  [[ "$real_dir" == "$real_root/"* && "$real_dir" != "$real_root" ]] || fail "Refusing unsafe delete path: $real_dir"
  if [[ "$yes" != "--yes" ]]; then
    say "WARNING: this removes the instance config/data after making a root-only backup."
    read -rp "Type the exact instance name '$name' to confirm: " answer
    [[ "$answer" == "$name" ]] || fail "Delete cancelled."
  fi
  if docker container inspect "$name" >/dev/null 2>&1; then
    docker rm -f "$name" >/dev/null
  fi
  backup_root="${TTU_DELETE_BACKUP_ROOT:-/opt/sntalkbot-deleted-backups}"
  install -d -m 0700 "$backup_root"
  backup="$backup_root/${name}-$(date +%Y%m%d-%H%M%S).tar.gz"
  tar -C "$BOTS_ROOT" -czf "$backup" -- "$name"
  chmod 0600 "$backup"
  rm -rf --one-file-system -- "$real_dir"
  say "Deleted instance '$name'."
  say "Backup: $backup"
}

logs_bot() {
  local name="$1"
  [[ -n "$name" ]] || fail "Usage: ttuhelper logs <name>"
  docker logs -f "$name"
}

list_bots() {
  ensure_layout
  say "Instances in $BOTS_ROOT:"
  local found=0 d name status
  shopt -s nullglob
  for d in "$BOTS_ROOT"/*; do
    [[ -d "$d" && -f "$d/config.ini" ]] || continue
    found=1
    name="$(basename "$d")"
    status="stopped"
    if docker container inspect "$name" >/dev/null 2>&1; then
      status="$(docker inspect -f '{{if .State.Running}}running{{else}}stopped{{end}}' "$name")"
    fi
    printf '%s\t%s\n' "$name" "$status"
  done
  (( found )) || say "(none)"
}

list_containers() {
  docker ps -a --filter "label=$LABEL_KEY=$LABEL_VALUE" --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
}

instance_has_player() {
  local dir="$1" mode value
  if [[ -f "$dir/instance.conf" ]]; then
    mode="$(awk -F= '$1=="mode" {gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print tolower($2); exit}' "$dir/instance.conf")"
    case "$mode" in
      player|full) return 0 ;;
      manager) return 1 ;;
    esac
  fi
  if [[ -f "$dir/config.ini" ]]; then
    value="$(awk -F= 'tolower($1) ~ /^[[:space:]]*player_enabled[[:space:]]*$/ {gsub(/[[:space:]]/, "", $2); print tolower($2); exit}' "$dir/config.ini")"
    case "$value" in
      true|1|yes|on) return 0 ;;
      false|0|no|off) return 1 ;;
    esac
  fi
  # Legacy/unknown instances are treated as compatible instead of being bricked.
  return 0
}

validate_cookie_file() {
  local path="$1" first data_rows youtube_rows
  [[ -s "$path" ]] || fail "Cookie file is empty: $path"
  # Normalize Windows CRLF because Netscape cookie files are consumed inside Linux.
  sed -i 's/\r$//' "$path"
  first="$(head -n 1 "$path" | sed 's/^\xEF\xBB\xBF//')"
  case "$first" in
    '# Netscape HTTP Cookie File'|'# HTTP Cookie File') ;;
    *) fail "Invalid cookies file. First line must be '# Netscape HTTP Cookie File' or '# HTTP Cookie File'." ;;
  esac
  data_rows="$(awk -F '\t' 'BEGIN{c=0} (!/^#/ || /^#HttpOnly_/) && NF>=7 {c++} END{print c}' "$path")"
  [[ "$data_rows" -gt 0 ]] || fail "No Netscape cookie records were found (expected tab-separated 7-field rows)."
  youtube_rows="$(awk -F '\t' 'BEGIN{c=0} (!/^#/ || /^#HttpOnly_/) && NF>=7 {d=$1; sub(/^#HttpOnly_/, "", d); if (d ~ /(^|\.)youtube\.com$/) c++} END{print c}' "$path")"
  if [[ "$youtube_rows" -eq 0 ]]; then
    warn "The file is valid Netscape format but contains no youtube.com cookie rows."
  fi
  COOKIE_DATA_ROWS="$data_rows"
  COOKIE_YOUTUBE_ROWS="$youtube_rows"
}

install_cookie_file() {
  local source="$1" destination="$2" tmp
  [[ -f "$source" ]] || fail "Cookie source file not found: $source"
  tmp="$(mktemp)"
  cp -- "$source" "$tmp"
  validate_cookie_file "$tmp"
  install -o 10001 -g 10001 -m 0640 "$tmp" "$destination"
  rm -f "$tmp"
}

update_cookies() {
  local name="$1" source="${2:-}" dir tmp
  [[ -n "$name" ]] || fail "Usage: ttuhelper cks <name> [cookies.txt]"
  dir="$(bot_dir "$name")"
  [[ -d "$dir" ]] || fail "Instance '$name' not found."
  instance_has_player "$dir" || fail "Instance '$name' is Server Manager-only; YouTube cookies belong only to Player/Full Bot."
  if [[ -n "$source" ]]; then
    install_cookie_file "$source" "$dir/cookies.txt"
  else
    say "Paste Netscape-format cookies, then press Ctrl+D:"
    tmp="$(mktemp)"
    cat > "$tmp"
    validate_cookie_file "$tmp"
    install -o 10001 -g 10001 -m 0640 "$tmp" "$dir/cookies.txt"
    rm -f "$tmp"
  fi
  say "Updated cookies for '$name' ($COOKIE_DATA_ROWS records; $COOKIE_YOUTUBE_ROWS YouTube records)."
  say "Restart the instance to force yt-dlp to reload the new session: sudo ttuhelper restart $name"
}

update_all_cookies() {
  local source="${1:-}" tmp d count=0 skipped=0
  tmp="$(mktemp)"
  if [[ -n "$source" ]]; then
    [[ -f "$source" ]] || { rm -f "$tmp"; fail "Cookie source file not found: $source"; }
    cp -- "$source" "$tmp"
  else
    say "Paste Netscape-format cookies once, then press Ctrl+D. It will be copied to every instance:"
    cat > "$tmp"
  fi
  validate_cookie_file "$tmp"
  shopt -s nullglob
  for d in "$BOTS_ROOT"/*; do
    [[ -d "$d" && -f "$d/config.ini" ]] || continue
    if ! instance_has_player "$d"; then
      skipped=$((skipped+1))
      continue
    fi
    install -o 10001 -g 10001 -m 0640 "$tmp" "$d/cookies.txt"
    count=$((count+1))
  done
  rm -f "$tmp"
  say "Updated cookies for $count Player/Full instance(s) ($COOKIE_DATA_ROWS records; $COOKIE_YOUTUBE_ROWS YouTube records); skipped $skipped Server Manager instance(s)."
  say "Restart running Player/Full instances (or run sudo ttuhelper update) so yt-dlp reloads the new session."
}

check_cookies() {
  local name="$1" dir tmp
  [[ -n "$name" ]] || fail "Usage: ttuhelper cks-check <name>"
  dir="$(bot_dir "$name")"
  [[ -d "$dir" ]] || fail "Instance '$name' not found."
  instance_has_player "$dir" || fail "Instance '$name' is Server Manager-only; YouTube cookies belong only to Player/Full Bot."
  [[ -f "$dir/cookies.txt" ]] || fail "cookies.txt not found for '$name'."
  tmp="$(mktemp)"
  cp -- "$dir/cookies.txt" "$tmp"
  validate_cookie_file "$tmp"
  rm -f "$tmp"
  say "cookies.txt for '$name': format OK; $COOKIE_DATA_ROWS records; $COOKIE_YOUTUBE_ROWS YouTube records."
  say "Cookie values are intentionally not displayed."
}

set_limits() {
  local name="$1" dir cpu memory
  [[ -n "$name" ]] || fail "Usage: ttuhelper limit <name>"
  dir="$(bot_dir "$name")"
  [[ -d "$dir" ]] || fail "Instance '$name' not found."
  read -rp "CPU limit, e.g. 0.5 (empty = no CPU limit): " cpu
  read -rp "Memory limit, e.g. 512m or 1g (empty = no memory limit): " memory
  if [[ -n "$cpu" && ! "$cpu" =~ ^[0-9]+([.][0-9]+)?$ ]]; then fail "Invalid CPU limit."; fi
  if [[ -n "$memory" && "$memory" =~ ^[0-9]+$ ]]; then memory="${memory}m"; fi
  if [[ -n "$memory" && ! "$memory" =~ ^[0-9]+([kKmMgG])?$ ]]; then fail "Invalid memory limit."; fi
  {
    if [[ -n "$cpu" ]]; then printf 'cpu=%s\n' "$cpu"; fi
    if [[ -n "$memory" ]]; then printf 'memory=%s\n' "$memory"; fi
  } > "$dir/limits.conf"
  chown 10001:10001 "$dir/limits.conf"
  chmod 0660 "$dir/limits.conf"
  say "Limits saved. Recreate the instance with: sudo ttuhelper restart $name"
}

show_path() {
  local name="$1" dir
  [[ -n "$name" ]] || fail "Usage: ttuhelper path <name>"
  dir="$(bot_dir "$name")"
  [[ -d "$dir" ]] || fail "Instance '$name' not found."
  printf '%s\n' "$dir"
}

edit_config() {
  local name="$1" dir editor
  [[ -n "$name" ]] || fail "Usage: ttuhelper edit <name>"
  dir="$(bot_dir "$name")"
  [[ -f "$dir/config.ini" ]] || fail "Instance '$name' not found."
  editor="${EDITOR:-nano}"
  command_exists "$editor" || fail "Editor '$editor' not found. Set EDITOR to an installed editor."
  "$editor" "$dir/config.ini"
  chown 10001:10001 "$dir/config.ini"
}

start_all() {
  local d count=0
  shopt -s nullglob
  for d in "$BOTS_ROOT"/*; do
    [[ -d "$d" && -f "$d/config.ini" ]] || continue
    run_bot "$(basename "$d")" 0
    count=$((count+1))
  done
  say "Processed $count instance(s)."
}

stop_all() {
  local names name count=0
  names="$(docker ps -a --filter "label=$LABEL_KEY=$LABEL_VALUE" --format '{{.Names}}')"
  while IFS= read -r name; do
    [[ -n "$name" ]] || continue
    docker rm -f "$name" >/dev/null || true
    count=$((count+1))
  done <<< "$names"
  say "Stopped $count helper-managed container(s)."
}

update_running() {
  local names name count=0
  names="$(docker ps --filter "label=$LABEL_KEY=$LABEL_VALUE" --format '{{.Names}}')"
  pull_image
  while IFS= read -r name; do
    [[ -n "$name" ]] || continue
    say "Recreating $name with $IMAGE_NAME ..."
    run_bot "$name" 1
    count=$((count+1))
  done <<< "$names"
  say "Updated $count running instance(s). Persistent data/config was preserved."
}

migrate_ttmediabot() {
  local source="" dry_run=0 arg tmp names_file answer count=0 name
  while [[ $# -gt 0 ]]; do
    arg="$1"
    case "$arg" in
      --dry-run) dry_run=1 ;;
      -h|--help)
        cat <<'MIGHELP'
Usage: sudo ttuhelper migrate-ttmediabot [legacy-root] [--dry-run]

Imports only the legacy TTMediaBot Docker Helper layout where each bot folder
contains config.json with config_version=1. This is not a generic importer for
other old bot projects.
MIGHELP
        return 0
        ;;
      --*) fail "Unknown migrate option: $arg" ;;
      *)
        [[ -z "$source" ]] || fail "Only one legacy root path may be supplied."
        source="$arg"
        ;;
    esac
    shift
  done

  if [[ -z "$source" ]]; then
    read -rp "Legacy TTMediaBot root (default: /opt/ttmediabot-docker-helper): " source
    source="${source:-/opt/ttmediabot-docker-helper}"
  fi
  [[ -d "$source" ]] || fail "Legacy TTMediaBot root not found: $source"
  [[ -f "$MIGRATOR_PATH" ]] || fail "Migration tool not installed: $MIGRATOR_PATH. Re-run TTUHelper install.sh."

  say "This importer supports only TTMediaBot Docker Helper config.json v1 folders."
  say "It does not claim compatibility with other legacy bot projects."
  say "Original TTMediaBot folders are left unchanged as a backup."
  say "Pulling current bot image before migration: $IMAGE_NAME"
  pull_image

  tmp="$(mktemp -d)"
  docker run --rm --entrypoint cat "$IMAGE_NAME" /app/config_default.ini > "$tmp/config_default.ini"
  [[ -s "$tmp/config_default.ini" ]] || fail "Could not read /app/config_default.ini from $IMAGE_NAME"
  names_file="$tmp/imported-names.txt"

  local -a migrate_args=(
    "$MIGRATOR_PATH"
    --source "$source"
    --dest-root "$BOTS_ROOT"
    --template "$tmp/config_default.ini"
    --mode prompt
    --names-file "$names_file"
  )
  if [[ "$dry_run" == "1" ]]; then migrate_args+=(--dry-run); fi
  python3 "${migrate_args[@]}"

  if [[ "$dry_run" == "1" ]]; then
    say "Dry run complete. No bot data or containers were changed."
    return 0
  fi

  [[ -s "$names_file" ]] || fail "Migration completed without an imported-name list."
  while IFS= read -r name; do
    [[ -n "$name" ]] || continue
    chown -R 10001:10001 "$(bot_dir "$name")"
    chmod 2770 "$(bot_dir "$name")"
    count=$((count+1))
  done < "$names_file"

  say "Imported $count instance(s) into $BOTS_ROOT."
  read -rp "Start/restart all imported bots now using $IMAGE_NAME? [Y/n]: " answer
  case "${answer,,}" in
    n|no)
      say "Migration data is ready. Start later with: sudo ttuhelper start-all"
      ;;
    *)
      while IFS= read -r name; do
        [[ -n "$name" ]] || continue
        say "Replacing any old container named '$name' and starting SNTalkBot ..."
        run_bot "$name" 1
      done < "$names_file"
      say "All imported bots were started/restarted with $IMAGE_NAME."
      ;;
  esac
  say "Keep the old TTMediaBot root until you have verified every migrated bot."
  rm -rf "$tmp"
}

doctor() {
  say "SNTalkBot Docker Helper (TTUHelper)"
  say "Image: $IMAGE_NAME"
  say "Bots root: $BOTS_ROOT"
  say "Python: $(python3 --version 2>&1 || true)"
  say "Docker: $(docker --version 2>&1 || true)"
  if docker info >/dev/null 2>&1; then say "Docker daemon: OK"; else say "Docker daemon: NOT AVAILABLE"; fi
  if docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then say "Image local: YES"; else say "Image local: NO (run: sudo ttuhelper pull)"; fi
  if [[ -f "$MIGRATOR_PATH" ]]; then say "TTMediaBot migrator: YES"; else say "TTMediaBot migrator: NO (re-run install.sh)"; fi
}

usage() {
  cat <<EOF2
SNTalkBot Docker Helper (TTUHelper)
Image: $IMAGE_NAME
Data root: $BOTS_ROOT

คำสั่ง:
  ttuhelper new                 สร้างบอต instance ใหม่และเลือกโหมด Full / Player / Server Manager
  ttuhelper run <name>          เริ่มบอตจาก config/data เดิม; ถ้ามี container ที่หยุดอยู่จะสร้างใหม่
  ttuhelper stop <name>         หยุดและลบ container แต่เก็บ config/data ของบอตไว้
  ttuhelper restart <name>      รีสตาร์ตบอตหนึ่งตัวโดยสร้าง container ใหม่จาก image ที่กำหนด
  ttuhelper delete <name>        ลบ instance หลังยืนยันชื่อ; สำรอง config/data แบบ root-only ก่อนลบ (เว็บใช้ --yes หลังยืนยัน)
  ttuhelper logs <name>         ดูบันทึกการทำงานแบบสด; กด Ctrl+C เพื่อออกจากหน้าดู log
  ttuhelper ls                  ดูรายชื่อ instance ทั้งหมดพร้อมสถานะ running/stopped
  ttuhelper ps                  ดู container ที่ TTUHelper จัดการ พร้อมสถานะและ image ที่ใช้อยู่
  ttuhelper start-all           เริ่มทุก instance ที่มี config.ini
  ttuhelper stop-all            หยุด container ทุกตัวที่ TTUHelper จัดการ โดยไม่ลบข้อมูลถาวร
  ttuhelper pull                ดาวน์โหลด Docker image/tag ที่ตั้งไว้ใน /etc/default/ttuhelper
  ttuhelper update              pull image ใหม่ แล้วสร้างใหม่เฉพาะ instance ที่กำลังรัน โดยเก็บข้อมูลเดิม
  ttuhelper migrate-ttmediabot [path]  ย้ายเฉพาะ TTMediaBot Docker Helper config.json v1 ไป SNTalkBot ใหม่ (alias: import-ttmediabot)
  ttuhelper cks <name> [file]   แทนที่ cookies.txt ของ Player/Full instance; ระบุไฟล์ได้หรือวางผ่าน stdin
  ttuhelper cks-all [file]      ใส่ cookies ให้ Player/Full ทุกตัวและข้าม Server Manager; ระบุไฟล์ได้หรือวางผ่าน stdin
  ttuhelper cks-check <name>    ตรวจ cookies ของ Player/Full โดยไม่แสดงค่า secret
  ttuhelper limit <name>        ตั้งข้อจำกัด CPU/RAM ของ instance แล้วใช้หลัง restart
  ttuhelper edit <name>         เปิด config.ini ของ instance ด้วย editor; ค่าเริ่มต้นคือ nano
  ttuhelper path <name>         แสดงตำแหน่งโฟลเดอร์ config/data ของ instance
  ttuhelper doctor              ตรวจ Docker daemon, image, data root และค่าหลักของ helper
  ttuhelper version             แสดงเวอร์ชัน TTUHelper
  ttuhelper help                แสดงคำอธิบายคำสั่งนี้

ไฟล์ตั้งค่ากลาง:
  /etc/default/ttuhelper

ค่าที่เปลี่ยนได้:
  TTU_IMAGE_REPO               Default: $IMAGE_REPO
  TTU_TAG                      Default: $IMAGE_TAG
  TTU_BOTS_ROOT                Default: $BOTS_ROOT
  TTU_HELPER_CONFIG            Default: $CONFIG_FILE
  TTU_API_PORT_MIN             Default: $API_PORT_MIN
  TTU_API_PORT_MAX             Default: $API_PORT_MAX
EOF2
}

main() {
  local cmd="${1:-help}"
  shift || true
  if [[ "$cmd" == "help" || "$cmd" == "-h" || "$cmd" == "--help" || -z "$cmd" || "$cmd" == "version" || "$cmd" == "-v" || "$cmd" == "--version" ]]; then
    :
  elif [[ "$cmd" == "cks" || "$cmd" == "cks-all" || "$cmd" == "cks-check" ]]; then
    # Cookie file maintenance is deliberately independent from the Docker daemon.
    # This lets operators install/check a session before the Player container starts.
    need_root "$cmd ${*:-}"
    ensure_layout
  else
    need_root "$cmd ${*:-}"
    ensure_layout
    ensure_docker_running
    ensure_python
  fi
  case "$cmd" in
    new) create_bot ;;
    run) run_bot "${1:-}" 0 ;;
    stop) stop_bot "${1:-}" ;;
    restart) restart_bot "${1:-}" ;;
    delete) delete_bot "${1:-}" "${2:-}" ;;
    logs) logs_bot "${1:-}" ;;
    ls) list_bots ;;
    ps) list_containers ;;
    start-all) start_all ;;
    stop-all) stop_all ;;
    pull) pull_image ;;
    update) update_running ;;
    migrate-ttmediabot|import-ttmediabot) migrate_ttmediabot "$@" ;;
    cks) update_cookies "${1:-}" "${2:-}" ;;
    cks-all) update_all_cookies "${1:-}" ;;
    cks-check) check_cookies "${1:-}" ;;
    limit) set_limits "${1:-}" ;;
    edit) edit_config "${1:-}" ;;
    path) show_path "${1:-}" ;;
    doctor) doctor ;;
    version|-v|--version) echo "$HELPER_VERSION" ;;
    help|-h|--help|'') usage ;;
    *) usage; fail "Unknown command: $cmd" ;;
  esac
}

main "$@"
