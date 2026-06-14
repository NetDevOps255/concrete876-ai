#!/usr/bin/env bash
# Lab B — DCGM telemetry (discovery / diag / live monitor).
set -euo pipefail
cd "$(dirname "$0")"
source ../lib/common.sh

need_gpu
log "GPU: $(gpu_name)"

# Install DCGM if absent
if ! require_cmd dcgmi; then
  log "Installing DCGM (datacenter-gpu-manager)..."
  export DEBIAN_FRONTEND=noninteractive
  KEYRING="cuda-keyring_1.1-1_all.deb"
  wget -q "https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/${KEYRING}"
  dpkg -i "$KEYRING" >/dev/null
  apt-get update -qq
  apt-get install -y -qq datacenter-gpu-manager >/dev/null
  rm -f "$KEYRING"
fi

# Start the host engine if not already running
pgrep -x nv-hostengine >/dev/null || { log "starting nv-hostengine"; nv-hostengine; sleep 2; }

log "== Discovery (inventory) =="
dcgmi discovery -l

log "== Quick diagnostic (r1, ~30s) =="
dcgmi diag -r 1 || warn "diag r1 returned non-zero — read the per-test output above"

log "== Live monitor 10s :: temp(150) power(155) util(203) sm_active(1002) occupancy(1003) =="
timeout 10 dcgmi dmon -e 150,155,203,1002,1003 -d 1000 || true

ok "Lab B core done."
cat <<'EOF'

Optional — metrics endpoint + dashboard (needs docker on the instance):
  docker run -d --gpus all --cap-add SYS_ADMIN -p 9400:9400 \
    --name dcgm-exporter nvcr.io/nvidia/k8s/dcgm-exporter:3.3.9-3.6.1-ubuntu22.04
  curl -s localhost:9400/metrics | grep DCGM_FI_PROF_PIPE_TENSOR_ACTIVE

  # view from your laptop without exposing the port:
  #   ssh -p <port> -L 9400:localhost:9400 root@<host>

Then destroy the box:  ./vast.sh kill <id>
EOF
