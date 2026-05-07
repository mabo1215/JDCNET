#!/bin/bash
set -e
cd /root/autodl-tmp/JDCNET/src
echo "[$(date)] ===MONITORING_DATA_SYNC==="
# Wait for data (max 2 hours = 120 iterations at 60s intervals)
for i in {1..120}; do
  if [ -d /root/autodl-tmp/data/bimcv/bimcv_paired ] && [ -d /root/autodl-tmp/data/bimcv/bimcv_ct_slices ]; then
    PC=$(find /root/autodl-tmp/data/bimcv/bimcv_paired -type f 2>/dev/null | wc -l)
    CT=$(find /root/autodl-tmp/data/bimcv/bimcv_ct_slices -type f 2>/dev/null | wc -l)
    DS=$(du -sh /root/autodl-tmp/data/bimcv/bimcv_paired 2>/dev/null | cut -f1)
    echo "[$(date)] bimcv_paired: $DS ($PC files), bimcv_ct_slices: ($CT files)"
    if [ "$PC" -gt 100 ] && [ "$CT" -gt 200 ]; then
      echo "[$(date)] ===DATA_SYNC_COMPLETE==="
      mkdir -p /root/autodl-tmp/logs /root/autodl-tmp/runs/bimcv_headline
      echo "[$(date)] Launching training..."
      nohup /root/miniconda3/bin/python3 -m jdcnet_exp.train --config /root/autodl-tmp/JDCNET/src/configs/bimcv_xray_supervised_s42.json > /root/autodl-tmp/logs/bimcv_xray_supervised_s42_train.log 2>&1 &
      TRAIN_PID=$!
      echo "[$(date)] TRAINING_LAUNCHED: PID=$TRAIN_PID"
      sleep 5
      ps -o pid,etime,pcpu,cmd -p $TRAIN_PID && echo "Training process verified running"
      exit 0
    fi
  else
    echo "[$(date)] Waiting for sync to begin..."
  fi
  sleep 60
done
echo "[$(date)] ERROR: Timeout waiting for data sync after 120 minutes"
exit 1
