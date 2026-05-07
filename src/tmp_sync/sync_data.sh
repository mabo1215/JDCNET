#!/bin/bash
set -e
mkdir -p /root/autodl-tmp/data/bimcv
mkdir -p /root/autodl-tmp/logs

echo "[$(date)] Starting data sync..." >> /root/autodl-tmp/logs/bimcv_sync.log

# Sync bimcv_paired (15GB)
echo "[$(date)] Syncing bimcv_paired..." >> /root/autodl-tmp/logs/bimcv_sync.log
scp -P 22 -r mabo1215@10.147.20.176:/data/bimcv_paired /root/autodl-tmp/data/bimcv/ 2>&1 >> /root/autodl-tmp/logs/bimcv_sync.log

# Sync bimcv_ct_slices (16M)
echo "[$(date)] Syncing bimcv_ct_slices..." >> /root/autodl-tmp/logs/bimcv_sync.log
scp -P 22 -r mabo1215@10.147.20.176:/data/bimcv_ct_slices /root/autodl-tmp/data/bimcv/ 2>&1 >> /root/autodl-tmp/logs/bimcv_sync.log

echo "[$(date)] SYNC_COMPLETE" >> /root/autodl-tmp/logs/bimcv_sync.log
ls -lh /root/autodl-tmp/data/bimcv/bimcv_paired /root/autodl-tmp/data/bimcv/bimcv_ct_slices >> /root/autodl-tmp/logs/bimcv_sync.log 2>&1
