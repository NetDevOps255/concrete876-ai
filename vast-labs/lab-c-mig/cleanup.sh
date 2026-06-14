#!/usr/bin/env bash
# Tear down MIG instances and disable MIG mode. Safe to run repeatedly.
set -uo pipefail
cd "$(dirname "$0")"
source ../lib/common.sh

log "Destroying compute instances..."; nvidia-smi mig -dci || true
log "Destroying GPU instances...";     nvidia-smi mig -dgi || true
log "Disabling MIG mode...";           nvidia-smi -mig 0   || true
ok "MIG cleaned up. (Box itself still rented — kill it with ./vast.sh)"
