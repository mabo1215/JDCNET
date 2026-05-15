#!/usr/bin/env bash
set -euo pipefail
ROOT=${ROOT:-/data/JDCNET_git/src}
PYTHON_BIN=${PYTHON_BIN:-python3}
TAG=${TAG:-bimcv_biomedclip_cv_20260516}
CV_DIR=${CV_DIR:-/data1/midrc/bimcv_only_cv_20260514}
PREFIX=${PREFIX:-bimcv_only}
RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/${TAG}}
CONFIG_DIR=${CONFIG_DIR:-$ROOT/configs/${TAG}}
LOG_DIR=${LOG_DIR:-/data1/logs/${TAG}}
FOLDS=${FOLDS:-"0 1 2 3 4"}
SEEDS=${SEEDS:-"42 43 44"}
GPUS=${GPUS:-"0 1 2 3"}
CONCURRENCY=${CONCURRENCY:-1}
BATCH_SIZE=${BATCH_SIZE:-64}
NUM_WORKERS=${NUM_WORKERS:-8}
EPOCHS=${EPOCHS:-50}
LR=${LR:-1e-5}
INPUT_SIZE=${INPUT_SIZE:-224}
AMP=${AMP:-true}
CHANNELS_LAST=${CHANNELS_LAST:-true}
TORCH_COMPILE=${TORCH_COMPILE:-false}
mkdir -p "$RUN_ROOT" "$CONFIG_DIR" "$LOG_DIR"
STATUS="$LOG_DIR/status.tsv"; touch "$STATUS"
log(){ printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"; }
done_run(){ [ -s "$1/best.pt" ]; }
done_test(){ [ -s "$1/test_eval/metrics.json" ]; }
log "C2_START tag=$TAG batch=$BATCH_SIZE workers=$NUM_WORKERS concurrency=$CONCURRENCY gpus=[$GPUS]"
cd "$ROOT"
$PYTHON_BIN - <<'PY'
import open_clip
m,_,_=open_clip.create_model_and_transforms('hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224')
print('BiomedCLIP visual ready:', type(m.visual).__name__)
PY
export RUN_ROOT CONFIG_DIR LOG_DIR CV_DIR PREFIX FOLDS SEEDS BATCH_SIZE NUM_WORKERS EPOCHS LR INPUT_SIZE AMP CHANNELS_LAST TORCH_COMPILE
"$PYTHON_BIN" - <<'PY'
import json, os
from pathlib import Path
cv=Path(os.environ['CV_DIR']); prefix=os.environ['PREFIX']; run=Path(os.environ['RUN_ROOT']); cfg_dir=Path(os.environ['CONFIG_DIR']); log=Path(os.environ['LOG_DIR'])
folds=[int(x) for x in os.environ['FOLDS'].split()]; seeds=[int(x) for x in os.environ['SEEDS'].split()]
batch=int(os.environ['BATCH_SIZE']); workers=int(os.environ['NUM_WORKERS']); epochs=int(os.environ['EPOCHS']); lr=float(os.environ['LR']); size=int(os.environ['INPUT_SIZE'])
amp=os.environ['AMP'].lower()=='true'; channels=os.environ['CHANNELS_LAST'].lower()=='true'; compile_=os.environ['TORCH_COMPILE'].lower()=='true'
cfg_dir.mkdir(parents=True, exist_ok=True)
names=[]
for fold in folds:
  manifest=str(cv/f'fold_{fold:02d}'/f'{prefix}_fold{fold:02d}_paired_manifest.csv')
  for seed in seeds:
    name=f'biomedclip_ft_f{fold:02d}_s{seed}'
    cfg={'experiment_name':name,'manifest_path':manifest,'output_dir':str(run/name),'seed':seed,
      'model':{'name':'student','num_classes':2,'input_size':size,'use_dpe':False,'use_mhra':False,'use_dfpn':False,'paired_input':False,'backbone':'biomedclip','freeze_backbone':False},
      'data':{'train_split':'train','val_split':'val','train_modalities':['xray'],'val_modalities':['xray'],'batch_size':batch,'num_workers':workers,'use_weighted_sampler':True,'pin_memory':True,'persistent_workers':workers>0,'prefetch_factor':4 if workers>0 else 2},
      'optimization':{'epochs':epochs,'learning_rate':lr,'weight_decay':1e-4,'grad_accum_steps':1,'amp':amp,'channels_last':channels,'torch_compile':compile_,'validation_interval':1},
      'distillation':{'enabled':False}}
    (cfg_dir/f'{name}.json').write_text(json.dumps(cfg,indent=2)); names.append(name)
(log/'cell_names.txt').write_text('\n'.join(names)+'\n')
print('configs',len(names))
PY
write_queue(){
  local gpu="$1"; shift; local qfile="$LOG_DIR/gpu${gpu}_names.txt"; local script="$LOG_DIR/gpu${gpu}_queue.sh"; printf '%s\n' "$@" > "$qfile"
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
  if done_run "\$run_dir"; then log "SKIP_DONE gpu=\$gpu \$name"; else log "START gpu=\$gpu \$name"; CUDA_VISIBLE_DEVICES=\$gpu "\$PYTHON_BIN" -u -m jdcnet_exp.train --config "\$cfg" > "\$log_f" 2>&1; rc=\$?; [ \$rc -eq 0 ] && log "DONE gpu=\$gpu \$name" || { log "FAIL rc=\$rc gpu=\$gpu \$name"; return \$rc; }; fi
  "\$PYTHON_BIN" - "\$cfg" "\$test_cfg" <<'PY'
import json,sys
p=json.load(open(sys.argv[1])); p['data']=dict(p['data']); p['data']['val_split']='test'; json.dump(p,open(sys.argv[2],'w'),indent=2)
PY
  if done_test "\$run_dir"; then log "SKIP_TEST gpu=\$gpu \$name"; else CUDA_VISIBLE_DEVICES=\$gpu "\$PYTHON_BIN" -m jdcnet_exp.evaluate --config "\$test_cfg" --checkpoint "\$run_dir/best.pt" --output-dir "\$run_dir/test_eval" >> "\$log_f" 2>&1 && log "DONE_TEST gpu=\$gpu \$name" || log "FAIL_TEST gpu=\$gpu \$name"; fi
}
export -f run_one log done_run done_test
export STATUS LOG_DIR CONFIG_DIR RUN_ROOT PYTHON_BIN gpu
cat '$qfile' | xargs -I{} -P '$CONCURRENCY' bash -c 'run_one "\$@"' _ {}
log "GPU_QUEUE_DONE gpu=\$gpu"
EOF
  chmod +x "$script"
}
mapfile -t gpus < <(printf '%s\n' $GPUS); mapfile -t names < "$LOG_DIR/cell_names.txt"
for gi in "${!gpus[@]}"; do gpu="${gpus[$gi]}"; assigned=(); for idx in "${!names[@]}"; do [ $((idx % ${#gpus[@]})) -eq "$gi" ] && assigned+=("${names[$idx]}"); done; [ ${#assigned[@]} -eq 0 ] && continue; write_queue "$gpu" "${assigned[@]}"; screen -S "c2_bclip_g${gpu}" -X quit >/dev/null 2>&1 || true; screen -dmS "c2_bclip_g${gpu}" bash "$LOG_DIR/gpu${gpu}_queue.sh"; log "LAUNCHED gpu=$gpu runs=${#assigned[@]}"; done
log "C2_ALL_LAUNCHED total=${#names[@]}"
screen -ls | grep c2_bclip || true
