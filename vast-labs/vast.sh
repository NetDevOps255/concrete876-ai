#!/usr/bin/env bash
# vast.sh — local control for vast-labs. Run on YOUR machine, NOT the rented box.
# Prereq:  pip install --upgrade vastai && vastai set api-key <KEY>
set -euo pipefail

DEFAULT_IMAGE="nvidia/cuda:12.4.1-devel-ubuntu22.04"

cmd="${1:-help}"; shift || true
case "$cmd" in
  search)
    # ./vast.sh search 'num_gpus=1 gpu_name=RTX_4090'
    vastai search offers "reliability>0.98 rentable=true ${*}" -o 'dph+' | head -n 20
    ;;
  up)
    # ./vast.sh up <OFFER_ID> [image] [disk_gb]
    OFFER="${1:?offer id required}"
    vastai create instance "$OFFER" \
      --image "${2:-$DEFAULT_IMAGE}" --disk "${3:-40}" --ssh --direct
    ;;
  ls)    vastai show instances ;;
  ssh)   vastai ssh-url "${1:?instance id required}" ;;
  kill)
    vastai destroy instance "${1:?instance id required}"
    echo "--- remaining instances (should be empty) ---"
    vastai show instances
    ;;
  *)
    cat <<EOF
vast.sh — local control for vast-labs

  ./vast.sh search 'num_gpus=1 gpu_name=RTX_4090'   find cheapest reliable offers
  ./vast.sh up <OFFER_ID> [image] [disk_gb]         rent (default image: devel CUDA)
  ./vast.sh ls                                      list your instances
  ./vast.sh ssh <INSTANCE_ID>                       print the ssh command
  ./vast.sh kill <INSTANCE_ID>                      destroy + confirm gone

Examples:
  ./vast.sh search 'num_gpus=1 gpu_name=A100_SXM4 verified=true'
  ./vast.sh up 1234567 nvidia/cuda:12.4.1-runtime-ubuntu22.04 30
EOF
    ;;
esac
