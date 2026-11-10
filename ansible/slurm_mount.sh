#!/usr/bin/env bash
# Mount / unmount a Slurm VM directory locally using sshfs.
# Usage: ./slurm_mount.sh {mount|unmount|status}

set -euo pipefail

# Defaults can be overridden with environment variables. When run in a
# terminal, mount prompts for the connection details and local mount point.
SLURM_USER="${SLURM_USER:-66070503445@cpe.kmutt.ac.th}"
SLURM_HOST="${SLURM_HOST:-portal.slurm.cpe.kmutt.ac.th}"
REMOTE_PATH="${REMOTE_PATH:-}"                     # empty = remote home directory
MOUNT_PATH="${MOUNT_PATH:-${HOME}/BenSlurm}"       # local directory where remote files appear
SSH_KEY="${SSH_KEY:-${HOME}/.ssh/id_rsa}"          # empty = use ssh-agent/config
# --------------------------------------------------------------------------

prompt_mount_path() {
  if [[ -t 0 ]]; then
    local value
    read -r -p "Local mount path [$MOUNT_PATH]: " value
    MOUNT_PATH="${value:-$MOUNT_PATH}"
  fi
}

prompt_connection_settings() {
  if [[ -t 0 ]]; then
    local value remote_default
    read -r -p "Slurm SSH user [$SLURM_USER]: " value
    SLURM_USER="${value:-$SLURM_USER}"
    read -r -p "Slurm host [$SLURM_HOST]: " value
    SLURM_HOST="${value:-$SLURM_HOST}"
    remote_default="${REMOTE_PATH:-remote home directory}"
    read -r -p "Remote path [$remote_default]: " value
    REMOTE_PATH="${value:-$REMOTE_PATH}"
  fi
}

is_mounted() {
  mountpoint -q "$MOUNT_PATH" 2>/dev/null
}

do_mount() {
  prompt_connection_settings
  prompt_mount_path

  if ! command -v sshfs >/dev/null 2>&1; then
    echo "sshfs not found. Install it first: sudo apt install sshfs" >&2
    exit 1
  fi

  if is_mounted; then
    echo "Already mounted at $MOUNT_PATH"
    return 0
  fi

  mkdir -p "$MOUNT_PATH"

  opts="reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,StrictHostKeyChecking=accept-new"
  if [[ -n "$SSH_KEY" ]]; then
    opts="IdentityFile=${SSH_KEY},${opts}"
  fi

  sshfs "${SLURM_USER}@${SLURM_HOST}:${REMOTE_PATH}" "$MOUNT_PATH" -o "$opts"
  echo "Mounted ${SLURM_USER}@${SLURM_HOST}:${REMOTE_PATH} -> $MOUNT_PATH"
}

do_unmount() {
  prompt_mount_path

  if ! is_mounted; then
    echo "Not mounted: $MOUNT_PATH"
    return 0
  fi

  if [[ "$(uname -s)" == "Darwin" ]]; then
    umount "$MOUNT_PATH" || { echo "Busy, forcing..."; umount -f "$MOUNT_PATH"; }
  else
    fusermount3 -u "$MOUNT_PATH" || { echo "Busy, using lazy unmount..."; fusermount -uz "$MOUNT_PATH"; }
  fi
  echo "Unmounted $MOUNT_PATH"
}

do_status() {
  prompt_mount_path

  if is_mounted; then
    echo "MOUNTED: $MOUNT_PATH"
  else
    echo "NOT MOUNTED: $MOUNT_PATH"
  fi
}

case "${1:-}" in
  mount)   do_mount ;;
  unmount) do_unmount ;;
  status)  do_status ;;
  *)
    echo "Usage: $0 {mount|unmount|status}" >&2
    exit 1
    ;;
esac