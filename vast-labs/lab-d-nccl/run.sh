#!/usr/bin/env bash
# Lab D — NCCL + multi-GPU.   Usage: ./run.sh [--all]
set -euo pipefail
cd "$(dirname "$0")"
source ../lib/common.sh

need_gpu
NGPU="$(gpu_count)"
log "GPUs detected: $NGPU  ($(gpu_name))"
[[ "$NGPU" -lt 2 ]] && warn "Only $NGPU GPU — rent a 2x+ box for meaningful collective bandwidth."

log "== Interconnect topology (NV# = NVLink, PIX/PXB = PCIe, SYS = over CPU) =="
nvidia-smi topo -m

if [[ ! -x nccl-tests/build/all_reduce_perf ]]; then
  log "Building nccl-tests..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq && apt-get install -y -qq git build-essential >/dev/null
  [[ -d nccl-tests ]] || git clone -q https://github.com/NVIDIA/nccl-tests
  make -C nccl-tests -j >/dev/null
  ok "built nccl-tests"
fi

log "== all-reduce  8B -> 512MB  (gradient-sync collective) =="
./nccl-tests/build/all_reduce_perf -b 8 -e 512M -f 2 -g "$NGPU"
log "Read the 'busbw' column — compare it to the NVLink ceiling from topo -m."

if [[ "${1:-}" == "--all" ]]; then
  for t in all_gather reduce_scatter broadcast; do
    log "== ${t} =="
    "./nccl-tests/build/${t}_perf" -b 8 -e 256M -f 2 -g "$NGPU"
  done
fi

ok "Lab D done. NCCL over NVLink here == NCCL over RoCE/InfiniBand at rack scale (NCP-AIN)."
log "Tear down:  ./vast.sh kill <id>"
