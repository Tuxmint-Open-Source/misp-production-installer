#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

usage() {
  cat <<'EOF'
Reset a failed or unwanted MISP Docker installation created by this installer.

Usage:
  ./installer/reset-installation.sh [options]

What this script removes:
  - MISP Docker Compose containers for the deployment
  - Docker Compose networks created for the deployment
  - Docker Compose named volumes created for the deployment
  - The local install directory, including generated .env, certificates, logs,
    files, configs, backups, and upstream checkout

What this script does NOT remove:
  - Docker Engine / Docker Compose packages
  - unrelated Docker containers, images, volumes, or networks
  - files outside --install-dir

Options:
  --install-dir PATH      Deployment directory to remove (default: /opt/misp-docker)
  --project-name NAME     Compose project name to clean. Defaults to the install
                          directory basename, matching Docker Compose behavior.
  --keep-install-dir      Stop/remove Docker resources but keep files on disk
  --yes                   Enable destructive mode. You will still be prompted.
  --force                 Skip the interactive confirmation prompt. Use only for
                          automation after testing the dry-run output.
  -h, --help              Show this help
  --version               Show installer version

Examples:
  # Show what would be removed without changing anything:
  ./installer/reset-installation.sh --install-dir /opt/misp-docker

  # Remove MISP resources and the install directory:
  ./installer/reset-installation.sh --install-dir /opt/misp-docker --yes

  # If you used a custom Compose project name:
  ./installer/reset-installation.sh --install-dir /srv/misp --project-name mymisp --yes
EOF
}

INSTALL_DIR="/opt/misp-docker"
PROJECT_NAME=""
KEEP_INSTALL_DIR="false"
YES="false"
FORCE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --project-name) PROJECT_NAME="$2"; shift 2;;
    --keep-install-dir) KEEP_INSTALL_DIR="true"; shift;;
    --yes) YES="true"; shift;;
    --force) FORCE="true"; shift;;
    -h|--help) usage; exit 0;;
    --version) print_version; exit 0;;
    *) fatal "Unknown argument: $1";;
  esac
done

INSTALL_DIR="$(python3 - "$INSTALL_DIR" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
)"
if [[ -z "$PROJECT_NAME" ]]; then
  PROJECT_NAME="$(basename "$INSTALL_DIR")"
fi

case "$INSTALL_DIR" in
  /|/opt|/srv|/home|/var|/usr|/tmp) fatal "Refusing unsafe --install-dir: $INSTALL_DIR";;
esac
[[ "$INSTALL_DIR" == */* ]] || fatal "Refusing unsafe --install-dir: $INSTALL_DIR"

run_or_print() {
  if [[ "$YES" == true ]]; then
    "$@"
  else
    printf '[DRY-RUN]'
    printf ' %q' "$@"
    printf '\n'
  fi
}

compose_files_present=false
if [[ -f "$INSTALL_DIR/docker-compose.yml" || -f "$INSTALL_DIR/compose.yml" ]]; then
  compose_files_present=true
fi

warn "This reset removes MISP containers, networks, named volumes, and generated files for: $INSTALL_DIR"
warn "Docker Engine itself is not removed. Unrelated Docker resources are not targeted."
[[ "$YES" == true ]] || warn "Dry-run only. Re-run with --yes to actually remove resources."

if [[ "$YES" == true && "$FORCE" != true ]]; then
  [[ -t 0 ]] || fatal "Interactive confirmation requires a terminal. Use --force only for automation after reviewing dry-run output."
  printf '\n%s\n' "Are you sure you want to delete everything for this MISP installation?"
  printf 'Install directory: %s\n' "$INSTALL_DIR"
  printf 'Compose project:   %s\n' "$PROJECT_NAME"
  printf 'Type DELETE to continue: '
  read -r confirmation
  [[ "$confirmation" == "DELETE" ]] || fatal "Reset aborted by user."
fi

if [[ "$compose_files_present" == true && -f "$INSTALL_DIR/.env" ]]; then
  # Preferred path: let Docker Compose remove the exact project described by the
  # install directory. --volumes is intentional; a reset should remove DB/data
  # volumes so a new install starts from scratch.
  log "Compose files found. Cleaning project via docker compose down --volumes --remove-orphans."
  if [[ "$YES" == true ]]; then
    compose_cmd "$INSTALL_DIR" down --volumes --remove-orphans
  else
    printf '[DRY-RUN] docker compose --env-file %q -f %q' "$INSTALL_DIR/.env" "$INSTALL_DIR/docker-compose.yml"
    [[ -f "$INSTALL_DIR/docker-compose.override.yml" ]] && printf ' -f %q' "$INSTALL_DIR/docker-compose.override.yml"
    printf ' down --volumes --remove-orphans\n'
  fi
else
  # Fallback for half-created installs where compose files or .env are missing.
  # Docker Compose labels all resources with com.docker.compose.project, so this
  # stays scoped to the intended project name.
  warn "Compose files or .env are missing; falling back to Docker label cleanup for project: $PROJECT_NAME"
  if command -v docker >/dev/null 2>&1; then
    mapfile -t containers < <(docker ps -aq --filter "label=com.docker.compose.project=$PROJECT_NAME")
    mapfile -t volumes < <(docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT_NAME")
    mapfile -t networks < <(docker network ls -q --filter "label=com.docker.compose.project=$PROJECT_NAME")
    if (( ${#containers[@]} )); then run_or_print docker rm -f "${containers[@]}"; else log "No matching containers found."; fi
    if (( ${#volumes[@]} )); then run_or_print docker volume rm -f "${volumes[@]}"; else log "No matching volumes found."; fi
    if (( ${#networks[@]} )); then run_or_print docker network rm "${networks[@]}"; else log "No matching networks found."; fi
  else
    warn "docker command not found; skipping Docker resource cleanup."
  fi
fi

if [[ "$KEEP_INSTALL_DIR" == true ]]; then
  log "Keeping install directory because --keep-install-dir was set: $INSTALL_DIR"
elif [[ -e "$INSTALL_DIR" ]]; then
  log "Removing install directory: $INSTALL_DIR"
  if [[ "$YES" == true ]]; then
    if rm -rf "$INSTALL_DIR" 2>/dev/null; then
      :
    else
      sudo rm -rf "$INSTALL_DIR"
    fi
  else
    printf '[DRY-RUN] rm -rf %q\n' "$INSTALL_DIR"
  fi
else
  log "Install directory does not exist: $INSTALL_DIR"
fi

if [[ "$YES" == true ]]; then
  log "Reset completed for $INSTALL_DIR"
else
  log "Dry-run completed. Nothing was removed."
fi
