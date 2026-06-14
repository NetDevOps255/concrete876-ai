# Lab B — DCGM Telemetry

**Rent:** 1x any GPU · **Image:** `nvidia/cuda:12.4.1-runtime-ubuntu22.04` · **~$0.50**

```bash
./run.sh
```

Installs DCGM, runs `discovery` (inventory), `diag -r 1` (health), and a 10s live
`dmon`. Field IDs used: 150 temp, 155 power, 203 util, 1002 sm-active, 1003 occupancy.
On a datacenter card the `DCGM_FI_PROF_*` fields populate (unlike the Pascal P1000).
Optional Prometheus/Grafana endpoint printed at the end (needs docker).
