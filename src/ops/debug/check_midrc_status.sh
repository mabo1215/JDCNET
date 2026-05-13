#!/bin/bash
# Check MIDRC download and GAPKD sweep status

echo "=== Host and directories ==="
hostname
pwd

echo "=== Data directories ==="
ls -ld /data* 2>/dev/null || echo "No /data*"

echo "=== GAPKD sweep config count ==="
ls /data/JDCNET/src/configs/bimcv_gapkd_sweep/*.json 2>/dev/null | wc -l

echo "=== GAPKD run directories ==="
ls -d /data/JDCNET/src/runs/bimcv_gapkd_sweep/*/ 2>/dev/null | wc -l

echo "=== GAPKD completed runs ==="
ls /data/JDCNET/src/runs/bimcv_gapkd_sweep/*/best_metrics.json 2>/dev/null | wc -l

echo "=== Screen sessions ==="
screen -ls 2>&1

echo "=== Gen3 client process ==="
ps aux | grep gen3-client | grep -v grep

echo "=== MIDRC download path ==="
find /data* /home -maxdepth 3 -name "*midrc*" -type d 2>/dev/null | head -5

echo "=== Check /home for gen3 downloads ==="
ls -lh /home/*/gen3* /home/mabo1215/.gen3* 2>/dev/null | head -10

echo "=== Recent process history (last 20 lines from syslog) ==="
tail -20 /var/log/syslog 2>/dev/null || echo "No syslog"
