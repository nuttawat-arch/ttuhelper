#!/usr/bin/env bash
set -euo pipefail
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

echo "Installing Docker/helper dependencies..."
apt-get update
apt-get install -y ca-certificates curl gnupg python3 nano

if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/${ID}/gpg" | gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  arch="$(dpkg --print-architecture)"
  codename="${VERSION_CODENAME:-}"
  [[ -n "$codename" ]] || { echo "VERSION_CODENAME is missing in /etc/os-release" >&2; exit 1; }
  echo "deb [arch=$arch signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} $codename stable" > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

systemctl enable --now docker

if [[ -e /usr/local/bin/tthelper ]]; then
  echo "Old command /usr/local/bin/tthelper detected; leaving it untouched."
fi
install -m 0755 ttuhelper.sh /usr/local/bin/ttuhelper
mkdir -p "$BOTS_ROOT"
chmod 0755 "$BOTS_ROOT"

if [[ ! -e /etc/default/ttuhelper ]]; then
  cat > /etc/default/ttuhelper <<CONF
TTU_IMAGE_REPO="$IMAGE_REPO"
TTU_TAG="$IMAGE_TAG"
TTU_BOTS_ROOT="$BOTS_ROOT"
CONF
  chmod 0644 /etc/default/ttuhelper
  echo "Created /etc/default/ttuhelper"
else
  echo "Keeping existing /etc/default/ttuhelper unchanged."
  # shellcheck disable=SC1091
  . /etc/default/ttuhelper
  IMAGE_REPO="${TTU_IMAGE_REPO:-$IMAGE_REPO}"
  IMAGE_TAG="${TTU_TAG:-$IMAGE_TAG}"
  BOTS_ROOT="${TTU_BOTS_ROOT:-$BOTS_ROOT}"
fi

echo "Pulling bot image ${IMAGE_REPO}:${IMAGE_TAG} ..."
docker pull "${IMAGE_REPO}:${IMAGE_TAG}"

echo
echo "Installation complete."
echo "Create the first instance with: sudo ttuhelper new"
echo "Then start it with: sudo ttuhelper run <name>"
echo "Check the helper with: sudo ttuhelper doctor"
