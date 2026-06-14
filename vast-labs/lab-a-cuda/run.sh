#!/usr/bin/env bash
# Lab A — CUDA kernels + Nsight profiling.   Usage: ./run.sh [--fma]
set -euo pipefail
cd "$(dirname "$0")"
source ../lib/common.sh

need_gpu
require_cmd nvcc || { err "nvcc missing — rent a '-devel' CUDA image"; exit 1; }

ARCH=$(detect_arch)
log "Compiling for $ARCH on $(gpu_name)"

nvcc -O2 -arch="$ARCH" vadd.cu -o vadd
ok "built vadd"
./vadd

# Nsight Systems — timeline (kernel vs memcpy vs API time)
if require_cmd nsys; then
  log "Nsight Systems profile (vadd is memory-bound)..."
  nsys profile --stats=true -o vadd_report ./vadd || warn "nsys returned non-zero (non-fatal)"
else
  warn "nsys not found; skipping timeline. (ships with CUDA toolkit)"
fi

# Nsight Compute — kernel deep-dive (occupancy, mem vs compute throughput)
NCU_BIN="$(command -v ncu 2>/dev/null || ls /opt/nvidia/nsight-compute/*/ncu 2>/dev/null | head -n1 || true)"
if [[ -n "$NCU_BIN" ]]; then
  log "Nsight Compute (basic set)..."
  "$NCU_BIN" --set basic ./vadd || warn "ncu may need relaxed perf-counter access (--target-processes all)"
else
  warn "ncu not found; install with: apt-get install -y nsight-compute"
fi

# Optional compute-bound contrast
if [[ "${1:-}" == "--fma" ]]; then
  log "Building + profiling compute-bound fma.cu for contrast..."
  nvcc -O2 -arch="$ARCH" fma.cu -o fma && ./fma
  [[ -n "$NCU_BIN" ]] && "$NCU_BIN" --set basic ./fma || true
  log "Compare: vadd = high DRAM throughput / low SM%; fma = high SM% / low DRAM."
fi

ok "Lab A done. Tear the box down:  ./vast.sh kill <id>  (from your machine)"
