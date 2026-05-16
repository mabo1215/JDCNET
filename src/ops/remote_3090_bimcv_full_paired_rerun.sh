#!/usr/bin/env bash
set -euo pipefail
# Re-run failed Stage A configs with CONCURRENCY=2 to avoid CUDA OOM

ROOT=${ROOT:-/data/JDCNET_git/src}
PYTHON_BIN=${PYTHON_BIN:-python3}
TAG=${TAG:-bimcv_full_paired_cv_20260516}
RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/${TAG}}
CONFIG_DIR=${CONFIG_DIR:-$ROOT/configs/${TAG}}
LOG_DIR=${LOG_DIR:-/data1/logs/${TAG}}
CONCURRENCY=${CONCURRENCY:-2}

STATUS="$LOG_DIR/status.tsv"; touch "$STATUS"
log(){ printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"; }

# Build list of incomplete runs (no best.pt OR no test_eval/metrics.json)
NAMES_FILE="$LOG_DIR/cell_names.txt"
RERUN_FILE="$LOG_DIR/rerun_list.txt"
> "$RERUN_FILE"
while IFS= read -r name; do
  [ -z "$name" ] && continue
  rd="$RUN_ROOT/$name"
  if [ ! -s "$rd/best.pt" ] || [ ! -s "$rd/test_eval/metrics.json" ]; then
    echo "$name" >> "$RERUN_FILE"
  fi
done < "$NAMES_FILE"
TOTAL=$(wc -l < "$RERUN_FILE")
log "RERUN_PLAN total=$TOTAL concurrency=$CONCURRENCY"

# Round-robin across 4 GPUs
GPUS=(0 1 2 3)
for gpu in "${GPUS[@]}"; do
  > "$LOG_DIR/gpu${gpu}_rerun_names.txt"
done
mapfile -t names < "$RERUN_FILE"
i=0
for n in "${names[@]}"; do
  gpu=${GPUS[$((i % ${#GPUS[@]}))]}
  echo "$n" >> "$LOG_DIR/gpu${gpu}_rerun_names.txt"
  i=$((i+1))
done

write_queue(){
  local gpu="$1"; local script="$LOG_DIR/gpu${gpu}_rerun_queue.sh"; local qfile="$LOG_DIR/gpu${gpu}_rerun_names.txt"
  cat > "$script" <<EOF
#!/usr/bin/env bash
set -u
cd '$ROOT'
STATUS='$STATUS'; LOG_DIR='$LOG_DIR'; CONFIG_DIR='$CONFIG_DIR'; RUN_ROOT='$RUN_ROOT'; PYTHON_BIN='$PYTHON_BIN'; gpu='$gpu'
log(){ printf '%s\t%s\n' "\$(date -Is)" "\$*" | tee -a "\$STATUS"; }
done_run(){ [ -s "\$1/best.pt" ]; }
done_test(){ [ -s "\$1/test_eval/metrics.json" ]; }
run_one(){
  local name="\$1"
  local cfg="\$CONFIG_DIR/\${name}.json"
  local run_dir="\$RUN_ROOT/\$name"
  local log_f="\$LOG_DIR/\${name}.log"
  local test_cfg="\$CONFIG_DIR/\${name}.test.json"
  local ckpt; ckpt=\$(python3 - "\$cfg" <<'PY'
import json,sys
p=json.load(open(sys.argv[1])); print((p.get('distillation') or {}).get('teacher_checkpoint',''))
PY
)
  if [ -n "\$ckpt" ]; then for i in \$(seq 1 720); do [ -s "\$ckpt" ] && break; sleep 5; done; fi
  if done_run "\$run_dir"; then log "SKIP_DONE gpu=\$gpu \$name"; else log "RERUN_START gpu=\$gpu \$name"; CUDA_VISIBLE_DEVICES=\$gpu "\$PYTHON_BIN" -u -m jdcnet_exp.train --config "\$cfg" > "\$log_f" 2>&1; rc=\$?; [ \$rc -eq 0 ] && log "DONE gpu=\$gpu \$name" || { log "FAIL rc=\$rc gpu=\$gpu \$name"; return \$rc; }; fi
  "\$PYTHON_BIN" - "\$cfg" "\$test_cfg" <<'PY'
import json,sys
p=json.load(open(sys.argv[1])); p['data']=dict(p['data']); p['data']['val_split']='test'; json.dump(p,open(sys.argv[2],'w'),indent=2)
PY
  if done_test "\$run_dir"; then log "SKIP_TEST gpu=\$gpu \$name"; else CUDA_VISIBLE_DEVICES=\$gpu "\$PYTHON_BIN" -m jdcnet_exp.evaluate --config "\$test_cfg" --checkpoint "\$run_dir/best.pt" --output-dir "\$run_dir/test_eval" >> "\$log_f" 2>&1 && log "DONE_TEST gpu=\$gpu \$name" || log "FAIL_TEST gpu=\$gpu \$name"; fi
}
export -f run_one log done_run done_test
export STATUS LOG_DIR CONFIG_DIR RUN_ROOT PYTHON_BIN gpu
cat '$qfile' | xargs -I{} -P '$CONCURRENCY' bash -c 'run_one "\$@"' _ {}
log "GPU_RERUN_QUEUE_DONE gpu=\$gpu"
EOF
  chmod +x "$script"
}

for gpu in "${GPUS[@]}"; do
  write_queue "$gpu"
  cnt=$(wc -l < "$LOG_DIR/gpu${gpu}_rerun_names.txt")
  screen -S "stageA_rerun_g${gpu}" -X quit >/dev/null 2>&1 || true
  screen -dmS "stageA_rerun_g${gpu}" bash "$LOG_DIR/gpu${gpu}_rerun_queue.sh"
  log "RERUN_LAUNCHED gpu=$gpu queue_size=$cnt"
done
log "RERUN_ALL_LAUNCHED total=$TOTAL"
screen -ls | grep stageA_rerun || true
