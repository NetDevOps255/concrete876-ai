# Lab C — MIG Partitioning

**Rent:** 1x **WHOLE** A100/H100 (verified host) · **Image:** `nvidia/cuda:12.4.1-runtime-ubuntu22.04` · **~$1–2**

```bash
./run.sh            # enable MIG, carve 3x 1g.5gb slices (profile 19)
./run.sh 14 2       # or: 2x 2g.10gb slices
./cleanup.sh        # tear down MIG when done
```

⚠️ **MIG is the picky lab.** Some Vast hosts block `nvidia-smi -mig 1`. If `run.sh`
fails at enable, destroy the box and pick a different `verified=true` whole-A100 offer.
Test in the first 2 minutes so you don't waste rental time.

Profile IDs (A100): 0=`7g.40gb` 9=`3g.20gb` 14=`2g.10gb` 19=`1g.5gb`.
Confirm with `nvidia-smi mig -lgip`.
