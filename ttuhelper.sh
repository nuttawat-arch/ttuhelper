#!/usr/bin/env bash
set -Eeuo pipefail

HELPER_VERSION="1.2.0"
CONFIG_FILE="${TTU_HELPER_CONFIG:-/etc/default/ttuhelper}"
if [[ -r "$CONFIG_FILE" ]]; then
  # shellcheck disable=SC1090
  . "$CONFIG_FILE"
fi

IMAGE_REPO="${TTU_IMAGE_REPO:-nuttawat0295/sntalkbot}"
IMAGE_TAG="${TTU_TAG:-latest}"
IMAGE_NAME="${IMAGE_REPO}:${IMAGE_TAG}"
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
    fail "Bot name must start with a letter/number and contain only A-Z, a-z, 0-9, _, . or - (max 63 chars)."
}

bot_dir() { printf '%s/%s' "$BOTS_ROOT" "$1"; }

ensure_layout() {
  mkdir -p "$BOTS_ROOT"
  chmod 0755 "$BOTS_ROOT"
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
  cat > "$dir/instance.conf" <<CONF
image=$IMAGE_NAME
created=$(date -Is)
mode=$mode_name
player_enabled=$player_enabled
server_management_enabled=$server_management_enabled
CONF
  chown -R 10001:10001 "$dir"
  chmod 0750 "$dir"
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
    "$IMAGE_NAME" >/dev/null

  say "Started '$name' with image $IMAGE_NAME"
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

update_cookies() {
  local name="$1" dir tmp
  [[ -n "$name" ]] || fail "Usage: ttuhelper cks <name>"
  dir="$(bot_dir "$name")"
  [[ -d "$dir" ]] || fail "Instance '$name' not found."
  say "Paste Netscape-format cookies, then press Ctrl+D:"
  tmp="$(mktemp)"
  cat > "$tmp"
  if [[ ! -s "$tmp" ]]; then
    rm -f "$tmp"
    fail "No cookie content received."
  fi
  install -o 10001 -g 10001 -m 0640 "$tmp" "$dir/cookies.txt"
  rm -f "$tmp"
  say "Updated cookies for '$name'."
}

update_all_cookies() {
  local tmp d count=0
  say "Paste Netscape-format cookies once, then press Ctrl+D. It will be copied to every instance:"
  tmp="$(mktemp)"
  cat > "$tmp"
  [[ -s "$tmp" ]] || { rm -f "$tmp"; fail "No cookie content received."; }
  shopt -s nullglob
  for d in "$BOTS_ROOT"/*; do
    [[ -d "$d" && -f "$d/config.ini" ]] || continue
    install -o 10001 -g 10001 -m 0640 "$tmp" "$d/cookies.txt"
    count=$((count+1))
  done
  rm -f "$tmp"
  say "Updated cookies for $count instance(s)."
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
  chmod 0640 "$dir/limits.conf"
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

doctor() {
  say "SNTalkBot Docker Helper (TTUHelper)"
  say "Image: $IMAGE_NAME"
  say "Bots root: $BOTS_ROOT"
  say "Python: $(python3 --version 2>&1 || true)"
  say "Docker: $(docker --version 2>&1 || true)"
  if docker info >/dev/null 2>&1; then say "Docker daemon: OK"; else say "Docker daemon: NOT AVAILABLE"; fi
  if docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then say "Image local: YES"; else say "Image local: NO (run: sudo ttuhelper pull)"; fi
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
  ttuhelper logs <name>         ดูบันทึกการทำงานแบบสด; กด Ctrl+C เพื่อออกจากหน้าดู log
  ttuhelper ls                  ดูรายชื่อ instance ทั้งหมดพร้อมสถานะ running/stopped
  ttuhelper ps                  ดู container ที่ TTUHelper จัดการ พร้อมสถานะและ image ที่ใช้อยู่
  ttuhelper start-all           เริ่มทุก instance ที่มี config.ini
  ttuhelper stop-all            หยุด container ทุกตัวที่ TTUHelper จัดการ โดยไม่ลบข้อมูลถาวร
  ttuhelper pull                ดาวน์โหลด Docker image/tag ที่ตั้งไว้ใน /etc/default/ttuhelper
  ttuhelper update              pull image ใหม่ แล้วสร้างใหม่เฉพาะ instance ที่กำลังรัน โดยเก็บข้อมูลเดิม
  ttuhelper cks <name>          แทนที่ cookies.txt ของ instance หนึ่งตัว
  ttuhelper cks-all             ใส่ cookies ชุดเดียวให้ทุก instance
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
EOF2
}

main() {
  local cmd="${1:-help}"
  shift || true
  if [[ "$cmd" == "help" || "$cmd" == "-h" || "$cmd" == "--help" || -z "$cmd" || "$cmd" == "version" || "$cmd" == "-v" || "$cmd" == "--version" ]]; then
    :
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
    logs) logs_bot "${1:-}" ;;
    ls) list_bots ;;
    ps) list_containers ;;
    start-all) start_all ;;
    stop-all) stop_all ;;
    pull) pull_image ;;
    update) update_running ;;
    cks) update_cookies "${1:-}" ;;
    cks-all) update_all_cookies ;;
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
