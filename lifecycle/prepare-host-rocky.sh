#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
ADD_CURRENT_USER_TO_DOCKER_GROUP="false"

usage() {
  cat <<'EOF'
Prepare a Rocky Linux host with Docker Engine and the Docker Compose plugin.

Usage:
  ./lifecycle/prepare-host-rocky.sh [options]

Options:
  --add-current-user-to-docker-group
      Add the sudo-invoking user to the docker group after installation.
      Docker group membership is effectively root-equivalent on the host; use
      this only on trusted single-operator systems.
  -h, --help   Show this help
  --version    Show manager version
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --add-current-user-to-docker-group) ADD_CURRENT_USER_TO_DOCKER_GROUP="true"; shift;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done

SUDO=""; [[ $(id -u) -ne 0 ]] && SUDO=sudo
[[ -r /etc/os-release ]] && . /etc/os-release && log "Detected OS: ${PRETTY_NAME:-unknown}"

# External package repositories can occasionally time out while downloading
# metadata or GPG keys. Retry package-manager operations before failing.
retry_cmd 3 15 $SUDO dnf -y install dnf-plugins-core curl ca-certificates tar gzip openssl python3 git findutils diffutils
if ! dnf repolist --enabled | grep -q '^docker-ce-stable'; then
  retry_cmd 3 15 $SUDO dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
fi
retry_cmd 3 20 $SUDO dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
$SUDO systemctl enable --now docker
if [[ "$ADD_CURRENT_USER_TO_DOCKER_GROUP" == true && -n "${SUDO_USER:-}" && "$SUDO_USER" != root ]]; then
  $SUDO usermod -aG docker "$SUDO_USER" || true
  warn "User $SUDO_USER was added to docker group. Docker group membership is root-equivalent; re-login or run: newgrp docker"
elif [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != root ]]; then
  warn "User $SUDO_USER was not added to docker group. This is safer by default; use sudo for Docker commands or rerun with --add-current-user-to-docker-group if you accept root-equivalent Docker group access."
fi
docker --version || $SUDO docker --version
docker compose version || $SUDO docker compose version
