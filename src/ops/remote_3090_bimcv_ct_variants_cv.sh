#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/data/JDCNET_git/src}
PYTHON_BIN=${PYTHON_BIN:-python3}
TAG=${TAG:-bimcv_ct_variants_cv_20260516}
CV_DIR=${CV_DIR:-/data1/midrc/bimcv_only_cv_20260514}
PREFIX=${PREFIX:-bimcv_only}
RUN_ROOT=${RUN_ROOT:-/data1/midrc/runs/${TAG}}
CONFIG_DIR=${CONFIG_DIR:-$ROOT/configs/${TAG}}
LOG_DIR=${LOG_DIR:-/data1/logs/${TAG}}
MANIFEST_DIR=${MANIFEST_DIR:-/data1/midrc/${TAG}/manifests}
DRR_SRC=${DRR_SRC:-/data/bimcv/drr_cache}
DRR_SHM=${DRR_SHM:-/dev/shm/bimcv_drr}
TEACHERS=${TEACHERS:-"mid 3slice proj drr"}
FOLDS=${FOLDS:-"0 1 2 3 4"}
SEEDS=${SEEDS:-"42 43 44"}
GPUS=${GPUS:-"0 1 2 3"}
CONCURRENCY=${CONCURRENCY:-4}
BATCH_SIZE=${BATCH_SIZE:-512}
NUM_WORKERS=${NUM_WORKERS:-8}
EPOCHS=${EPOCHS:-50}
INPUT_SIZE=${INPUT_SIZE:-224}
AMP=${AMP:-true}
CHANNELS_LAST=${CHANNELS_LAST:-true}
TORCH_COMPILE=${TORCH_COMPILE:-false}
ALPHA=${ALPHA:-0.6}
TEMP=${TEMP:-4.0}
THRESHOLD=${THRESHOLD:-0.50}

mkdir -p "$RUN_ROOT" "$CONFIG_DIR" "$LOG_DIR" "$MANIFEST_DIR" "$DRR_SHM"
STATUS="$LOG_DIR/status.tsv"; touch "$STATUS"
log(){ printf '%s\t%s\n' "$(date -Is)" "$*" | tee -a "$STATUS"; }
done_run(){ [ -s "$1/best.pt" ]; }
done_test(){ [ -s "$1/test_eval/metrics.json" ]; }

log "C1_START tag=$TAG batch=$BATCH_SIZE workers=$NUM_WORKERS concurrency=$CONCURRENCY gpus=[$GPUS]"
cp "$DRR_SRC"/bimcv_S*.png "$DRR_SHM"/ 2>/dev/null || true
cd "$ROOT"
"$PYTHON_BIN" ops/extract_ct_teacher_variants.py --cv-dir "$CV_DIR" --prefix "$PREFIX" --drr-dir "$DRR_SHM" --summary "$LOG_DIR/extract_summary.json"

export ROOT TAG CV_DIR PREFIX RUN_ROOT CONFIG_DIR LOG_DIR MANIFEST_DIR DRR_SHM TEACHERS FOLDS SEEDS BATCH_SIZE NUM_WORKERS EPOCHS INPUT_SIZE AMP CHANNELS_LAST TORCH_COMPILE ALPHA TEMP THRESHOLD
"$PYTHON_BIN" - <<'PY'
import json, os, re
from pathlib import Path
import pandas as pd
cv_dir=Path(os.environ['CV_DIR']); prefix=os.environ['PREFIX']
run_root=Path(os.environ['RUN_ROOT']); cfg_dir=Path(os.environ['CONFIG_DIR']); man_dir=Path(os.environ['MANIFEST_DIR']); log_dir=Path(os.environ['LOG_DIR'])
teachers=os.environ['TEACHERS'].split(); folds=[int(x) for x in os.environ['FOLDS'].split()]; seeds=[int(x) for x in os.environ['SEEDS'].split()]
batch=int(os.environ['BATCH_SIZE']); workers=int(os.environ['NUM_WORKERS']); epochs=int(os.environ['EPOCHS']); input_size=int(os.environ['INPUT_SIZE'])
amp=os.environ['AMP'].lower()=='true'; channels_last=os.environ['CHANNELS_LAST'].lower()=='true'; torch_compile=os.environ['TORCH_COMPILE'].lower()=='true'
alpha=float(os.environ['ALPHA']); temp=float(os.environ['TEMP']); thr=float(os.environ['THRESHOLD']); drr=Path(os.environ['DRR_SHM'])
variant_dirs={'mid':Path('/dev/shm/bimcv_ct_mid'),'3slice':Path('/dev/shm/bimcv_ct_3slice'),'proj':Path('/dev/shm/bimcv_ct_proj'),'drr':drr}
for p in [cfg_dir, man_dir]: p.mkdir(parents=True, exist_ok=True)

def patient_from_path(s):
    m=re.search(r'S\d+', str(s)); return m.group(0) if m else None

def variant_path(t,pid): return str(variant_dirs[t] / f'bimcv_{pid}.png')
common=None
for t in teachers:
    avail={patient_from_path(x.name) for x in variant_dirs[t].glob('bimcv_S*.png')}; avail.discard(None)
    common=avail if common is None else common & avail
common=set(common or [])
base_model={'name':'student','num_classes':2,'input_size':input_size,'use_dpe':False,'use_mhra':False,'use_dfpn':False,'paired_input':False,'backbone':'resnet18'}

def data_cfg(batch_size, paired=False):
    d={'train_split':'train','val_split':'val','train_modalities':['xray'],'val_modalities':['xray'],'batch_size':batch_size,'num_workers':workers,'use_weighted_sampler':True,'pin_memory':True,'persistent_workers':workers>0,'prefetch_factor':4 if workers>0 else 2}
    if paired: d['paired_image_column']='teacher_image_path'
    return d

def opt_cfg(lr=3e-4):
    return {'epochs':epochs,'learning_rate':lr,'weight_decay':1e-4,'grad_accum_steps':1,'amp':amp,'channels_last':channels_last,'torch_compile':torch_compile,'validation_interval':1}

def plain(ckpt): return {'enabled':True,'temperature':temp,'alpha':alpha,'teacher_checkpoint':ckpt,'confidence_gate_enabled':False,'projected_attention_weight':0.0}
def gated(ckpt): return {'enabled':True,'temperature':temp,'alpha':alpha,'teacher_checkpoint':ckpt,'confidence_gate_enabled':True,'confidence_gate_threshold':thr,'confidence_gate_floor':0.0,'confidence_gate_power':1.0,'confidence_gate_requires_correct':True,'confidence_gate_positive_threshold':-1.0,'confidence_gate_negative_threshold':-1.0,'confidence_gate_min_margin':0.0,'confidence_gate_max_entropy':-1.0,'projected_attention_weight':0.0}

def write_cfg(name, manifest, dist=None):
    cfg={'experiment_name':name,'manifest_path':str(manifest),'output_dir':str(run_root/name),'seed':int(re.search(r'_s(\d+)', name).group(1)),'model':base_model,'data':data_cfg(batch, bool(dist and dist.get('enabled'))),'optimization':opt_cfg(),'distillation':dist or {'enabled':False}}
    (cfg_dir/f'{name}.json').write_text(json.dumps(cfg,indent=2))

names=[]
for t in teachers:
  for fold in folds:
    src=cv_dir/f'fold_{fold:02d}'/f'{prefix}_fold{fold:02d}_paired_manifest.csv'
    df=pd.read_csv(src)
    keep=[]; vpaths=[]
    for _,row in df.iterrows():
        pid=str(row['patient_id']).replace('bimcv_','')
        ok=pid in common
        keep.append(ok); vpaths.append(variant_path(t,pid) if ok else '')
    dfs=df[keep].copy().reset_index(drop=True); vpaths=[p for p,k in zip(vpaths,keep) if k]
    dfs['teacher_image_path']=vpaths
    student_csv=man_dir/f'{t}_fold{fold:02d}_student_manifest.csv'; dfs.to_csv(student_csv,index=False)
    dft=dfs.copy(); dft['teacher_image_path']=dfs['image_path']; dft['image_path']=vpaths
    teacher_csv=man_dir/f'{t}_fold{fold:02d}_teacher_manifest.csv'; dft.to_csv(teacher_csv,index=False)
    print(f'{t} fold{fold}: rows={len(dfs)} pos={(dfs.label==1).sum()} neg={(dfs.label==0).sum()}')
    for seed in seeds:
        stem=f'{t}_f{fold:02d}_s{seed}'
        teacher_name=f'{stem}_teacher'; sup_name=f'{stem}_supervised'; plain_name=f'{stem}_plain_kd'; gated_name=f'{stem}_gated_kd_thr050'
        ckpt=str(run_root/teacher_name/'best.pt')
        write_cfg(teacher_name, teacher_csv); names.append((0,teacher_name))
        write_cfg(sup_name, student_csv); names.append((1,sup_name))
        write_cfg(plain_name, student_csv, plain(ckpt)); names.append((2,plain_name))
        write_cfg(gated_name, student_csv, gated(ckpt)); names.append((3,gated_name))
names=[n for _,n in sorted(names)]
(log_dir/'cell_names.txt').write_text('\n'.join(names)+'\n')
print('configs',len(names),'common_patients',len(common))
PY

log "CONFIGS_GENERATED $(wc -l < "$LOG_DIR/cell_names.txt")"

write_queue(){
  local gpu="$1"; shift; local script="$LOG_DIR/gpu${gpu}_queue.sh"; local qfile="$LOG_DIR/gpu${gpu}_names.txt"; printf '%s\n' "$@" > "$qfile"
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
mapfile -t gpus < <(printf '%s\n' $GPUS)
mapfile -t names < "$LOG_DIR/cell_names.txt"
for gi in "${!gpus[@]}"; do
  gpu="${gpus[$gi]}"; assigned=()
  for idx in "${!names[@]}"; do [ $((idx % ${#gpus[@]})) -eq "$gi" ] && assigned+=("${names[$idx]}"); done
  write_queue "$gpu" "${assigned[@]}"
  screen -S "c1_ctv_g${gpu}" -X quit >/dev/null 2>&1 || true
  screen -dmS "c1_ctv_g${gpu}" bash "$LOG_DIR/gpu${gpu}_queue.sh"
  log "LAUNCHED gpu=$gpu runs=${#assigned[@]}"
done
log "C1_ALL_LAUNCHED total=${#names[@]}"
screen -ls | grep c1_ctv || true
