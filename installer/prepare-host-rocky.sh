#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
SUDO=""; [[ $(id -u) -ne 0 ]] && SUDO=sudo
[[ -r /etc/os-release ]] && . /etc/os-release && log "Detected OS: ${PRETTY_NAME:-unknown}"
$SUDO dnf -y install dnf-plugins-core curl ca-certificates tar gzip openssl python3 git findutils diffutils
if ! dnf repolist --enabled | grep -q '^docker-ce-stable'; then
  $SUDO dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
fi
$SUDO dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
$SUDO systemctl enable --now docker
if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != root ]]; then
  $SUDO usermod -aG docker "$SUDO_USER" || true
  warn "User $SUDO_USER was added to docker group. Re-login or run: newgrp docker"
fi
docker --version || $SUDO docker --version
docker compose version || $SUDO docker compose version
