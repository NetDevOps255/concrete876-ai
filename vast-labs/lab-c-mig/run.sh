#!/usr/bin/env bash
# Lab C — MIG partitioning.   Usage: ./run.sh [PROFILE_ID] [COUNT]
# Defaults: profile 19 (1g.5gb) x3.  Run `nvidia-smi mig -lgip` to see IDs for your card.
set -euo pipefail
cd "$(dirname "$0")"
source ../lib/common.sh

need_gpu
NAME="$(gpu_name)"
log "GPU: $NAME"
case "$NAME" in
  *A100*|*H100*|*A30*) ok "MIG-capable card detected" ;;
  *) err "MIG needs A100/H100/A30 — this is '$NAME'. Rent a WHOLE A100 (verified host)."; exit 1 ;;
esac

log "Current MIG mode:"
nvidia-smi -q | grep -i "MIG Mode" -A2 || true

log "Enabling MIG..."
if ! nvidia-smi -mig 1; then
  err "Could not enable MIG. This Vast host blocks it — destroy and pick a verified whole-A100 offer."
  exit 1
fi
# Some hosts need a reset to apply the mode change
nvidia-smi --gpu-reset >/dev/null 2>&1 || warn "gpu-reset unavailable; if mode shows 'pending', reboot the instance and re-run"

log "Available GPU Instance profiles:"
nvidia-smi mig -lgip

PROFILE="${1:-19}"      # 19 = 1g.5gb on A100
COUNT="${2:-3}"
SLICES="$(printf '%s,' $(for _ in $(seq "$COUNT"); do echo "$PROFILE"; done) | sed 's/,$//')"
log "Creating $COUNT x profile $PROFILE  ->  $SLICES"
nvidia-smi mig -cgi "$SLICES" -C

log "GPU instances:"; nvidia-smi mig -lgi
log "MIG devices (UUIDs):"; nvidia-smi -L

cat <<'EOF'

Pin a workload to a single slice (hardware-isolated):
  CUDA_VISIBLE_DEVICES=MIG-<uuid> <your_app>

See the slices in DCGM:
  apt-get install -y datacenter-gpu-manager && nv-hostengine && dcgmi discovery -l

When finished:
  ./cleanup.sh          # tears down MIG instances + disables MIG
  ./vast.sh kill <id>   # destroy the box (from your machine)
EOF
