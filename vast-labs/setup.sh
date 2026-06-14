#!/usr/bin/env bash
# vast-labs bootstrap. Run once after `git clone` on a fresh Vast.ai box.
set -euo pipefail
cd "$(dirname "$0")"
source lib/common.sh

need_gpu
log "GPU:  $(gpu_name)   (x$(gpu_count))"

log "Installing base tooling..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git curl wget vim htop build-essential ca-certificates >/dev/null

ok "Base ready. Detected CUDA arch: $(detect_arch)"
echo
log "Next:  cd lab-a-cuda && ./run.sh"
log "       (lab-b-dcgm | lab-c-mig | lab-d-nccl)"
