param(
    [string]$EnvPath = 'C:\source\.env',
    [string]$OutDir = 'src\results\bimcv_pathc_3090',
    [string]$HostName = '10.147.20.176',
    [string]$UserName = 'mabo1215',
    [string]$HostKey = 'ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $repo
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $OutDir 'runs') | Out-Null

$lines = Get-Content -LiteralPath $EnvPath
$password = $lines[8].Trim()
$plink = (Get-Command plink).Source
$pscp = (Get-Command pscp).Source

function Invoke-3090([string]$Command) {
    & $plink -ssh -batch -hostkey $HostKey -l $UserName -pw $password $HostName $Command 2>&1 |
        ForEach-Object { $_ -replace [regex]::Escape($password), '***' }
}

function Copy-3090File([string]$RemotePath, [string]$LocalPath) {
    & $pscp -batch -q -hostkey $HostKey -l $UserName -pw $password "${HostName}:$RemotePath" $LocalPath 2>&1 |
        ForEach-Object { $_ -replace [regex]::Escape($password), '***' }
}

$status = Invoke-3090 @'
cd /data/JDCNET/src || exit 1
printf "__TIME__\n"; date -Is
printf "__SCREEN__\n"; screen -ls 2>/dev/null | grep -E 'bimcv_pathc_gpu23|midrc_559' || true
printf "__GPU__\n"; nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader,nounits 2>/dev/null || true
printf "__PROCS__\n"; pgrep -af 'jdcnet_exp.train.*bimcv_pathc|bimcv_pathc_gpu23_scheduler|gen3-client.*midrc' || true
printf "__COMPLETED__\n"; find /data/JDCNET/src/runs/bimcv_pathc -maxdepth 2 -name best_metrics.json -printf '%h\n' 2>/dev/null | sed 's#/data/JDCNET/src/runs/bimcv_pathc/##' | sort || true
printf "__STATUS_TAIL__\n"; tail -n 80 /data/logs/bimcv_pathc/train_status.tsv 2>/dev/null || true
printf "__MIDRC__\n"; find /data/midrc/raw_559cases_combined -type f 2>/dev/null | wc -l; du -sh /data/midrc/raw_559cases_combined 2>/dev/null || true
'@
$status | Set-Content -Encoding UTF8 -Path (Join-Path $OutDir 'remote_status.txt')

$remoteList = Invoke-3090 "find /data/JDCNET/src/runs/bimcv_pathc -maxdepth 2 -name best_metrics.json -printf '%h %p\n' 2>/dev/null || true"
foreach ($line in $remoteList) {
    if ($line -match '^(.+) (/data/.+/best_metrics\.json)$') {
        $runName = Split-Path -Leaf $Matches[1]
        $localRun = Join-Path (Join-Path $OutDir 'runs') $runName
        New-Item -ItemType Directory -Force -Path $localRun | Out-Null
        Copy-3090File $Matches[2] (Join-Path $localRun 'best_metrics.json') | Out-Null
    }
}

$analysis = @'
import json
from pathlib import Path
import csv
import statistics

import os
root = Path(os.environ.get('PATHC_OUTDIR', 'src/results/bimcv_pathc_3090')) / 'runs'
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
    print(
        f"{r['name']} role={r['role']} seed={r['seed']} "
        f"BA={r.get('balanced_accuracy')} F1={r.get('macro_f1')} "
        f"AUC={r.get('roc_auc')} epoch={r.get('epoch')}"
    )

for role in ['teacher_ct', 'supervised', 'kd']:
    vals = [r.get('balanced_accuracy') for r in rows if r['role'] == role and r.get('balanced_accuracy') is not None]
    if vals:
        sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
        print(f'MEAN {role} n={len(vals)} BA={sum(vals)/len(vals):.6f} SD={sd:.6f}')

print('paired_delta kd-supervised:')
by = {(r['role'], r['seed']): r for r in rows}
for seed in sorted({r['seed'] for r in rows if r['seed'] is not None}):
    if ('kd', seed) in by and ('supervised', seed) in by:
        delta = by[('kd', seed)]['balanced_accuracy'] - by[('supervised', seed)]['balanced_accuracy']
        print(f'seed={seed} delta_BA={delta:.6f}')

out = Path(os.environ.get('PATHC_OUTDIR', 'src/results/bimcv_pathc_3090')) / 'summary.csv'
fields = ['name', 'role', 'seed', 'balanced_accuracy', 'macro_f1', 'roc_auc', 'pr_auc', 'epoch']
with out.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in fields})
'@
$analysisPath = Join-Path $OutDir 'analyze_partial.py'
$analysis | Set-Content -Encoding UTF8 -Path $analysisPath
$env:PATHC_OUTDIR = $OutDir
python $analysisPath | Set-Content -Encoding UTF8 -Path (Join-Path $OutDir 'analysis.txt')
Remove-Item Env:PATHC_OUTDIR -ErrorAction SilentlyContinue
Get-Content (Join-Path $OutDir 'analysis.txt')
Write-Host "Pulled 3090 Path C results into $OutDir"
