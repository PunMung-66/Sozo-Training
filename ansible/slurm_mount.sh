#!/usr/bin/env bash
# Mount / unmount a Slurm VM directory locally using sshfs.
# Usage: ./slurm_mount.sh {mount|unmount|status}

set -euo pipefail

# ---- Edit these ----------------------------------------------------------
SLURM_USER="66070503445@cpe.kmutt.ac.th"
SLURM_HOST="portal.slurm.cpe.kmutt.ac.th"
REMOTE_PATH=""                           # empty = your home directory on the node
MOUNT_PATH="${HOME}/Documents/Senior/Project/SlurmMount"  # local mount point
SSH_KEY="${HOME}/.ssh/id_rsa"            # leave empty to use ssh-agent/config
# --------------------------------------------------------------------------

is_mounted() {
  mountpoint -q "$MOUNT_PATH" 2>/dev/null
}

do_mount() {
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