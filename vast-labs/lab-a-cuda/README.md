# Lab A — CUDA Kernels + Nsight Profiling

**Rent:** 1x cheap GPU (T4/3090/4090) · **Image:** `nvidia/cuda:12.4.1-devel-ubuntu22.04` · **~$0.50**

```bash
./run.sh          # build + run vadd, then nsys + ncu profiling
./run.sh --fma    # also build the compute-bound contrast kernel
```

Arch (`sm_XX`) is auto-detected from the GPU. Takeaway: vadd is **memory-bound**
(high DRAM throughput, low SM%); fma is **compute-bound** (the reverse).
