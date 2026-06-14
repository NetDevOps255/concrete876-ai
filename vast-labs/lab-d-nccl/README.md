# Lab D — NCCL & Multi-GPU

**Rent:** 2x+ GPU (prefer SXM/NVLink) · **Image:** `nvidia/cuda:12.4.1-devel-ubuntu22.04` · **~$2–4**

```bash
./run.sh          # topo -m, build nccl-tests, all-reduce benchmark
./run.sh --all    # also all-gather, reduce-scatter, broadcast
```

`busbw` (bus bandwidth) is the number that matters — it should climb toward the
NVLink ceiling at large message sizes. On a `SYS`-only box it plateaus low, which
is the whole point: **fabric topology drives training throughput** (your NCP-AIN bridge).
