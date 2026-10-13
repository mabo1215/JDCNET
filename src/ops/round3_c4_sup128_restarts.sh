#!/usr/bin/env bash
# Round-3 Experiment A: batch-matched supervised restarts on the 510-patient splits.
# 16 supervised runs per (fold, seed) cell at batch size 128 with training seeds
# cell_seed + 1000*r (r = 0..15). Uses the original code read-only and writes
# only under $WORK. GPUs restricted to $GPUS (default "0 1").
set -euo pipefail

CODE=${CODE:-/data/JDCNET_git/src}
WORK=${WORK:-/data1/jdcnet_round3}
TEMPLATE_DIR=${TEMPLATE_DIR:-/data/JDCNET_git/src/configs/bimcv_full_paired_cv_20260516}
GPUS=${GPUS:-"0 1"}
CONCURRENCY=${CONCURRENCY:-4}
RESTARTS=${RESTARTS:-16}
BATCH=${BATCH:-128}
PYTHON_BIN=${PYTHON_BIN:-python3}
TAG=sup128_restarts
CFG_DIR=$WORK/configs/$TAG
RUN_ROOT=$WORK/runs/$TAG
LOG_DIR=$WORK/logs/$TAG
mkdir -p "$CFG_DIR" "$RUN_ROOT" "$LOG_DIR"
STATUS=$LOG_DIR/status.tsv; touch "$STATUS"
log(){ printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"; }

export TEMPLATE_DIR CFG_DIR RUN_ROOT RESTARTS BATCH
"$PYTHON_BIN" - <<'PY'
import json, os
from pathlib import Path
tdir, cdir, rroot = Path(os.environ['TEMPLATE_DIR']), Path(os.environ['CFG_DIR']), Path(os.environ['RUN_ROOT'])
restarts, batch = int(os.environ['RESTARTS']), int(os.environ['BATCH'])
names = []
for fold in range(5):
    for seed in (42, 43, 44):
        tpl = json.loads((tdir / f'mid_f{fold:02d}_s{seed}_supervised.json').read_text())
        for r in range(restarts):
            name = f'sup128_f{fold:02d}_s{seed}_r{r:02d}'
            cfg = json.loads(json.dumps(tpl))
            cfg['experiment_name'] = name
            cfg['output_dir'] = str(rroot / name)
            cfg['seed'] = seed + 1000 * r
            cfg['data']['batch_size'] = batch
            (cdir / f'{name}.json').write_text(json.dumps(cfg, indent=2))
            test = json.loads(json.dumps(cfg)); test['data']['val_split'] = 'test'
            (cdir / f'{name}.test.json').write_text(json.dumps(test, indent=2))
            names.append((r, name))
# r = 0 first so the batch-matched baseline finishes early
names = [n for _, n in sorted(names)]
(cdir.parent / 'sup128_names.txt').write_text('\n'.join(names) + '\n')
print('configs', len(names))
PY
mapfile -t names < "$CFG_DIR/../sup128_names.txt"
log "CONFIGS ${#names[@]} gpus=[$GPUS] concurrency=$CONCURRENCY batch=$BATCH"

for gpu in $GPUS; do
  q=$LOG_DIR/gpu${gpu}_queue.txt; : > "$q"
done
i=0; mapfile -t G < <(printf '%s\n' $GPUS)
for n in "${names[@]}"; do echo "$n" >> "$LOG_DIR/gpu${G[$((i % ${#G[@]}))]}_queue.txt"; i=$((i+1)); done

cat > "$LOG_DIR/run_one.sh" <<EOF
#!/usr/bin/env bash
set -u
name="\$1"; gpu="\$2"
cfg=$CFG_DIR/\$name.json; tcfg=$CFG_DIR/\$name.test.json; rd=$RUN_ROOT/\$name; lf=$LOG_DIR/\$name.log
log(){ printf '%s\t%s\n' "\$(date -Is)" "\$*" >> $STATUS; }
cd $CODE
if [ -s "\$rd/best.pt" ]; then log "SKIP_DONE gpu=\$gpu \$name"; else
  log "START gpu=\$gpu \$name"
  CUDA_VISIBLE_DEVICES=\$gpu $PYTHON_BIN -u -m jdcnet_exp.train --config "\$cfg" > "\$lf" 2>&1 && log "DONE gpu=\$gpu \$name" || { log "FAIL gpu=\$gpu \$name"; exit 1; }
fi
if [ ! -s "\$rd/test_eval/metrics.json" ]; then
  CUDA_VISIBLE_DEVICES=\$gpu $PYTHON_BIN -m jdcnet_exp.evaluate --config "\$tcfg" --checkpoint "\$rd/best.pt" --output-dir "\$rd/test_eval" >> "\$lf" 2>&1 && log "DONE_TEST gpu=\$gpu \$name" || log "FAIL_TEST gpu=\$gpu \$name"
fi
EOF
chmod +x "$LOG_DIR/run_one.sh"

if [ "${DRY:-0}" = "1" ]; then log "DRY_RUN configs and runner written; not launched"; exit 0; fi

for gpu in $GPUS; do
  screen -S "r3sup_g$gpu" -X quit >/dev/null 2>&1 || true
  screen -dmS "r3sup_g$gpu" bash -c "cat $LOG_DIR/gpu${gpu}_queue.txt | xargs -I{} -P $CONCURRENCY $LOG_DIR/run_one.sh {} $gpu; printf '%s\tGPU_QUEUE_DONE gpu=$gpu\n' \"\$(date -Is)\" >> $STATUS"
  log "LAUNCHED gpu=$gpu runs=$(wc -l < $LOG_DIR/gpu${gpu}_queue.txt)"
done
screen -ls | grep r3sup || true
