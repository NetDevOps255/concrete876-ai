# vast-labs

Companion scaffold for the **NVIDIA → Vast.ai Lab Guide** (BookStack: `concrete876.com`, NVIDIA book → *Vast.ai Lab Guide* chapter).

Clone onto a rented Vast.ai box and each lab is one command. Everything is self-contained: rent → run → tear down.

## Flow

**On YOUR machine (control side)** — needs `pip install --upgrade vastai && vastai set api-key <KEY>`:

```bash
./vast.sh search 'num_gpus=1 gpu_name=RTX_4090'   # find an offer
./vast.sh up <OFFER_ID>                            # rent it
./vast.sh ssh <INSTANCE_ID>                        # print the ssh command
```

**On the rented box:**

```bash
git clone <your-fork-url> vast-labs && cd vast-labs
./setup.sh                       # one-time bootstrap (base tools, arch detect)
cd lab-a-cuda && ./run.sh        # run a lab
```

**Tear down (control side)** — do this EVERY time:

```bash
./vast.sh kill <INSTANCE_ID>     # destroys + confirms gone
```

## Labs

| Dir | Lab | Rent | ~Cost | Image |
|---|---|---|---|---|
| `lab-a-cuda` | CUDA kernels + Nsight profiling | 1x cheap (T4/3090/4090) | ~$0.50 | `nvidia/cuda:12.4.1-devel-ubuntu22.04` |
| `lab-b-dcgm` | DCGM telemetry (discovery/diag/dmon) | 1x any | ~$0.50 | `...runtime...` |
| `lab-c-mig`  | MIG partitioning | 1x **whole** A100/H100 | ~$1–2 | `...runtime...` |
| `lab-d-nccl` | NCCL + multi-GPU | 2x+ GPU | ~$2–4 | `...devel...` |

Use a **`-devel`** image when the lab needs `nvcc` (A and D). `-runtime` is fine for B and C.

## Cost discipline (FIRE rule)

- Set a phone timer every session.
- `./vast.sh kill <id>` then confirm the list is empty. A "stopped" box still bills for disk.
- Log every session in [`COST-LOG.md`](./COST-LOG.md). Whole chapter target: under $15.

## Layout

```
vast-labs/
├── README.md
├── COST-LOG.md
├── vast.sh              # local control helper (run on YOUR machine)
├── setup.sh             # one-time bootstrap (run on the rented box)
├── lib/common.sh        # shared helpers (arch detection, logging)
├── lab-a-cuda/   vadd.cu  fma.cu  run.sh  README.md
├── lab-b-dcgm/   run.sh  README.md
├── lab-c-mig/    run.sh  cleanup.sh  README.md
└── lab-d-nccl/   run.sh  README.md
```

> Fork this and point the clone URL at your own remote so you can commit results/notes per session.
