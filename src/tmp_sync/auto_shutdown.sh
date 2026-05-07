#!/bin/bash
# Auto-shutdown script: monitors training completion and shuts down H800 container
# Usage: nohup /root/auto_shutdown.sh > /root/auto_shutdown.log 2>&1 &

set -e
TRAIN_LOGFILE="/root/autodl-tmp/logs/bimcv_xray_supervised_s42_train.log"
MONITOR_INTERVAL=30  # Check every 30 seconds
MAX_WAIT=28800       # Max 8 hours of waiting

echo "[$(date)] Auto-shutdown monitor started"
echo "[$(date)] Monitoring: $TRAIN_LOGFILE"

start_time=$(date +%s)

while true; do
  current_time=$(date +%s)
  elapsed=$((current_time - start_time))
  
  # Check if training completed
  if [ -f "$TRAIN_LOGFILE" ]; then
    if tail -5 "$TRAIN_LOGFILE" | grep -qE "Training complete|Finished|successfully completed"; then
      echo "[$(date)] Training completed detected!"
      echo "[$(date)] Waiting 60 seconds before shutdown..."
      sleep 60
      echo "[$(date)] Shutting down H800 container..."
      # Send shutdown signal
      poweroff || shutdown -h now
      exit 0
    fi
    
    # Check for errors
    if tail -20 "$TRAIN_LOGFILE" | grep -qE "Error|Exception|Traceback"; then
      echo "[$(date)] Training error detected!"
      echo "[$(date)] Container will remain online for debugging"
      exit 1
    fi
  fi
  
  # Timeout check
  if [ $elapsed -gt $MAX_WAIT ]; then
    echo "[$(date)] Timeout ($MAX_WAIT seconds) reached, shutting down..."
    poweroff || shutdown -h now
    exit 0
  fi
  
  # Log status every 5 checks (every 2.5 minutes)
  if [ $((elapsed % 150)) -lt $MONITOR_INTERVAL ]; then
    echo "[$(date)] Checking... (elapsed: $((elapsed/60))m)"
    if [ -f "$TRAIN_LOGFILE" ]; then
      tail -3 "$TRAIN_LOGFILE"
    fi
  fi
  
  sleep $MONITOR_INTERVAL
done
