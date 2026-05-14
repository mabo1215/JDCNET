param(
    [string]$EnvPath = 'C:\source\.env',
    [string]$OutDir = 'docs\tmp\h800_pathc',
    [int]$Port = 12437,
    [string]$HostName = 'connect.westc.seetacloud.com',
    [string]$UserName = 'root',
    [string]$HostKey = 'ssh-ed25519 255 SHA256:liZ36vNCsNcNdXeWs4f+g5ZIhPM/ZihP834vxs8Ulqc'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $repo
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $OutDir 'runs') | Out-Null

$lines = Get-Content -LiteralPath $EnvPath
$password = $env:H800_PASSWORD
if ([string]::IsNullOrWhiteSpace($password)) {
    $password = $lines[4].Trim()
}
$plink = (Get-Command plink).Source
$pscp = (Get-Command pscp).Source

function Invoke-H800([string]$Command) {
    & $plink -ssh -batch -hostkey $HostKey -P $Port -l $UserName -pw $password $HostName $Command 2>&1 |
        ForEach-Object { $_ -replace [regex]::Escape($password), '***' }
}

function Copy-H800File([string]$RemotePath, [string]$LocalPath) {
    & $pscp -batch -q -hostkey $HostKey -P $Port -l $UserName -pw $password "${HostName}:$RemotePath" $LocalPath 2>&1 |
        ForEach-Object { $_ -replace [regex]::Escape($password), '***' }
}

$status = Invoke-H800 @'
cd /root/autodl-tmp/JDCNET/src || exit 1
printf "__SCREEN__\n"; screen -ls 2>/dev/null | grep pathc_h800 || true
printf "__GPU__\n"; nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader,nounits || true
printf "__PROCS__\n"; pgrep -af 'jdcnet_exp.train.*bimcv_pathc_h800|run_pathc_h800' || true
printf "__COMPLETED__\n"; find -L /root/autodl-tmp/runs/bimcv_pathc_h800 -maxdepth 2 -name best_metrics.json -printf '%h\n' 2>/dev/null | sed 's#/root/autodl-tmp/runs/bimcv_pathc_h800/##' | sort || true
printf "__STATUS_TAIL__\n"; tail -n 50 /root/autodl-tmp/logs/bimcv_pathc_h800/status.tsv 2>/dev/null || true
'@
$status | Set-Content -Encoding UTF8 -Path (Join-Path $OutDir 'remote_status.txt')

Copy-H800File '/root/autodl-tmp/logs/bimcv_pathc_h800/status.tsv' (Join-Path $OutDir 'status.tsv') | Out-Null
Copy-H800File '/root/autodl-tmp/data/bimcv/bimcv_pathc_split_summary.json' (Join-Path $OutDir 'bimcv_pathc_split_summary.json') | Out-Null
try { Copy-H800File '/root/autodl-tmp/logs/bimcv_pathc_h800/best_metrics_summary.csv' (Join-Path $OutDir 'best_metrics_summary.csv') | Out-Null } catch {}

$remoteList = Invoke-H800 "find -L /root/autodl-tmp/runs/bimcv_pathc_h800 -maxdepth 2 -name best_metrics.json -printf '%h %p\n' 2>/dev/null || true"
foreach ($line in $remoteList) {
    if ($line -match '^(.+) (/root/.+/best_metrics\.json)$') {
        $runName = Split-Path -Leaf $Matches[1]
        $localRun = Join-Path (Join-Path $OutDir 'runs') $runName
        New-Item -ItemType Directory -Force -Path $localRun | Out-Null
        Copy-H800File $Matches[2] (Join-Path $localRun 'best_metrics.json') | Out-Null
    }
}

$analysis = @'
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
'@
$analysisPath = Join-Path $OutDir 'analyze_partial.py'
$analysis | Set-Content -Encoding UTF8 -Path $analysisPath
python $analysisPath | Tee-Object -FilePath (Join-Path $OutDir 'analysis.txt')

Write-Host "Pulled H800 Path C results into $OutDir"

