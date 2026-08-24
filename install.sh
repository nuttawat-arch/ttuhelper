#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"

[[ "$EUID" -eq 0 ]] || { echo "Run this installer with sudo: sudo ./install.sh" >&2; exit 1; }
[[ -r /etc/os-release ]] || { echo "Cannot detect Linux distribution." >&2; exit 1; }
. /etc/os-release
[[ "${ID:-}" == "ubuntu" || "${ID:-}" == "debian" ]] || { echo "Automatic installer supports Ubuntu/Debian only." >&2; exit 1; }

IMAGE_REPO="${TTU_IMAGE_REPO:-nuttawat0295/sntalkbot}"
IMAGE_TAG="${TTU_TAG:-latest}"
LEGACY_BOTS_ROOT="/opt/ttutilities-bots"
DEFAULT_BOTS_ROOT="/opt/sntalkbot-bots"
if [[ -n "${TTU_BOTS_ROOT:-}" ]]; then
  BOTS_ROOT="$TTU_BOTS_ROOT"
elif [[ -d "$LEGACY_BOTS_ROOT" && ! -e "$DEFAULT_BOTS_ROOT" ]]; then
  BOTS_ROOT="$LEGACY_BOTS_ROOT"
else
  BOTS_ROOT="$DEFAULT_BOTS_ROOT"
fi

say(){ printf '%s\n' "$*"; }
has(){ command -v "$1" >/dev/null 2>&1; }

say "TTUHelper installer preflight"
missing=()
has curl || missing+=(curl)
has gpg || missing+=(gnupg)
has python3 || missing+=(python3)
has nano || missing+=(nano)
has flock || missing+=(util-linux)
[[ -s /etc/ssl/certs/ca-certificates.crt ]] || missing+=(ca-certificates)

if ((${#missing[@]})); then
  say "Missing packages: ${missing[*]}"
  if ! apt-get update; then
    echo >&2
    echo "APT update failed." >&2
    echo "If APT says a repository changed Origin/Label/Suite, review the repository and run:" >&2
    echo "  sudo apt-get update --allow-releaseinfo-change" >&2
    echo "Then run this installer again." >&2
    exit 1
  fi
  apt-get install -y "${missing[@]}"
else
  say "[OK] curl/gpg/python3/nano/flock/CA certificates are already installed; skipping APT dependency install."
fi

if ! has docker; then
  say "Docker is not installed; installing Docker Engine from Docker's official repository..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/${ID}/gpg" | gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  arch="$(dpkg --print-architecture)"
  codename="${VERSION_CODENAME:-}"
  [[ -n "$codename" ]] || { echo "VERSION_CODENAME is missing in /etc/os-release" >&2; exit 1; }
  echo "deb [arch=$arch signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} $codename stable" > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
  say "[OK] Docker command already exists; skipping Docker installation."
fi

if has systemctl; then
  if ! systemctl is-active --quiet docker; then
    say "Starting Docker daemon..."
    systemctl enable --now docker
  else
    say "[OK] Docker daemon is already running."
  fi
fi
docker info >/dev/null 2>&1 || { echo "Docker daemon is unavailable." >&2; exit 1; }

if [[ -e /usr/local/bin/tthelper ]]; then
  say "Old command /usr/local/bin/tthelper detected; leaving it untouched."
fi
install -m 0755 ttuhelper.sh /usr/local/bin/ttuhelper
install -d -m 0755 /usr/local/lib/ttuhelper
install -m 0755 tools/migrate_ttmediabot.py /usr/local/lib/ttuhelper/migrate_ttmediabot.py
mkdir -p "$BOTS_ROOT"
chown root:10001 "$BOTS_ROOT" 2>/dev/null || true
chmod 2770 "$BOTS_ROOT"

if [[ ! -e /etc/default/ttuhelper ]]; then
  cat > /etc/default/ttuhelper <<CONF
TTU_IMAGE_REPO="$IMAGE_REPO"
TTU_TAG="$IMAGE_TAG"
TTU_BOTS_ROOT="$BOTS_ROOT"
TTU_API_PORT_MIN="20000"
TTU_API_PORT_MAX="27999"
CONF
  chmod 0644 /etc/default/ttuhelper
  say "Created /etc/default/ttuhelper"
else
  say "Keeping existing /etc/default/ttuhelper settings and adding only missing 1.5 defaults."
  grep -q '^TTU_API_PORT_MIN=' /etc/default/ttuhelper || printf '%s\n' 'TTU_API_PORT_MIN="20000"' >> /etc/default/ttuhelper
  grep -q '^TTU_API_PORT_MAX=' /etc/default/ttuhelper || printf '%s\n' 'TTU_API_PORT_MAX="27999"' >> /etc/default/ttuhelper
  # shellcheck disable=SC1091
  . /etc/default/ttuhelper
  IMAGE_REPO="${TTU_IMAGE_REPO:-$IMAGE_REPO}"
  IMAGE_TAG="${TTU_TAG:-$IMAGE_TAG}"
  BOTS_ROOT="${TTU_BOTS_ROOT:-$BOTS_ROOT}"
fi

say "Checking bot image ${IMAGE_REPO}:${IMAGE_TAG} ..."
if docker image inspect "${IMAGE_REPO}:${IMAGE_TAG}" >/dev/null 2>&1; then
  say "[OK] Local image exists. Pulling latest manifest/layers to check for updates..."
fi
docker pull "${IMAGE_REPO}:${IMAGE_TAG}"

say "Installation complete."
say "Create the first instance with: sudo ttuhelper new"
say "Then start it with: sudo ttuhelper run <name>"
say "Delete an instance safely with: sudo ttuhelper delete <name>"
say "Check the helper with: sudo ttuhelper doctor"
say "Migrate legacy TTMediaBot config v1 with: sudo ttuhelper migrate-ttmediabot"
