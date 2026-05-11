import json
from pathlib import Path
import statistics

root = Path('docs/tmp/h800_pathc/runs')
rows = []
for p in sorted(root.glob('*/best_metrics.json')):
    name = p.parent.name
    try:
        m = json.load(open(p, encoding='utf-8'))
    except Exception:
        continue
    if 'teacher_ct' in name:
        role = 'teacher_ct'
    elif 'xray_supervised' in name:
        role = 'supervised'
    elif 'xray_cross_modal_kd' in name:
        role = 'kd'
    else:
        role = 'unknown'
    seed = int(name.rsplit('_s', 1)[-1]) if '_s' in name else None
    rows.append({'name': name, 'role': role, 'seed': seed, **m})

print(f'completed_runs={len(rows)}')
for r in rows:
    print(f"{r['name']} role={r['role']} seed={r['seed']} BA={r.get('balanced_accuracy')} F1={r.get('macro_f1')} AUC={r.get('roc_auc')}")

by = {(r['role'], r['seed']): r for r in rows}
deltas = []
for seed in sorted({r['seed'] for r in rows if r['seed'] is not None}):
    kd = by.get(('kd', seed))
    sup = by.get(('supervised', seed))
    if kd and sup:
        d = float(kd.get('balanced_accuracy', 0)) - float(sup.get('balanced_accuracy', 0))
        deltas.append(d)
        print(f'paired_delta seed={seed} kd_minus_supervised_BA={d:.6f}')
if deltas:
    print(f'delta_n={len(deltas)} mean={statistics.mean(deltas):.6f} median={statistics.median(deltas):.6f} wins={sum(d>0 for d in deltas)} ties={sum(d==0 for d in deltas)} losses={sum(d<0 for d in deltas)}')
else:
    print('paired_delta: not available yet')
