param(
    [string]$EnvPath = 'C:\source\.env',
    [int]$IntervalSeconds = 300,
    [switch]$Once,
    [string]$LogDir = 'docs\tmp\host_monitor'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $repo
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$logFile = Join-Path $LogDir 'monitor.log'
$stateFile = Join-Path $LogDir 'latest_status.txt'
$lines = Get-Content -LiteralPath $EnvPath
$h800Password = $env:H800_PASSWORD
if ([string]::IsNullOrWhiteSpace($h800Password)) {
  $h800Password = $lines[4].Trim()
}
$r3090Password = $env:R3090_PASSWORD
if ([string]::IsNullOrWhiteSpace($r3090Password)) {
  $r3090Password = $lines[8].Trim()
}
$plink = (Get-Command plink).Source
$pscp = (Get-Command pscp).Source

$h800Host = 'connect.westc.seetacloud.com'
$h800Port = 12437
$h800User = 'root'
$h800HostKey = 'ssh-ed25519 255 SHA256:liZ36vNCsNcNdXeWs4f+g5ZIhPM/ZihP834vxs8Ulqc'

$r3090Host = '10.147.20.176'
$r3090User = 'mabo1215'
$r3090HostKey = 'ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0'

function Write-Log([string]$Message) {
    $line = "$(Get-Date -Format o) $Message"
    $line | Tee-Object -FilePath $logFile -Append | Out-Null
}

function Mask-Secrets($Items, [string[]]$Secrets) {
    $Items | ForEach-Object {
        $s = [string]$_
        foreach ($secret in $Secrets) {
            if ($secret) { $s = $s -replace [regex]::Escape($secret), '***' }
        }
        $s
    }
}

function Invoke-H800([string]$Command) {
    $out = & $plink -ssh -batch -hostkey $h800HostKey -P $h800Port -l $h800User -pw $h800Password $h800Host $Command 2>&1
    Mask-Secrets $out @($h800Password)
}

function Invoke-3090([string]$Command) {
    $out = & $plink -ssh -batch -hostkey $r3090HostKey -l $r3090User -pw $r3090Password $r3090Host $Command 2>&1
    Mask-Secrets $out @($r3090Password)
}

function Copy-H800File([string]$RemotePath, [string]$LocalPath) {
    $out = & $pscp -batch -q -hostkey $h800HostKey -P $h800Port -l $h800User -pw $h800Password "${h800Host}:$RemotePath" $LocalPath 2>&1
    Mask-Secrets $out @($h800Password)
}

function Copy-TextToRemoteH800([string]$Text, [string]$RemotePath) {
    $tmp = Join-Path $env:TEMP ("h800_" + [guid]::NewGuid().ToString("N") + ".sh")
    [System.IO.File]::WriteAllText($tmp, ($Text -replace "`r`n", "`n"), [System.Text.Encoding]::ASCII)
    $out = & $pscp -batch -q -hostkey $h800HostKey -P $h800Port -l $h800User -pw $h800Password $tmp "${h800Host}:$RemotePath" 2>&1
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    Mask-Secrets $out @($h800Password)
}

function Copy-TextToRemote3090([string]$Text, [string]$RemotePath) {
    $tmp = Join-Path $env:TEMP ("r3090_" + [guid]::NewGuid().ToString("N") + ".sh")
    [System.IO.File]::WriteAllText($tmp, ($Text -replace "`r`n", "`n"), [System.Text.Encoding]::ASCII)
    $out = & $pscp -batch -q -hostkey $r3090HostKey -l $r3090User -pw $r3090Password $tmp "${r3090Host}:$RemotePath" 2>&1
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    Mask-Secrets $out @($r3090Password)
}

$h800Health = @'
#!/usr/bin/env bash
set -u
RUN_ROOT=/root/autodl-tmp/runs/bimcv_pathc_h800
LOG_ROOT=/root/autodl-tmp/logs/bimcv_pathc_h800
TASKS=(
  bimcv_pathc_h800_resnet18_teacher_ct_s42
  bimcv_pathc_h800_resnet18_xray_supervised_s42
  bimcv_pathc_h800_resnet18_teacher_ct_s43
  bimcv_pathc_h800_resnet18_xray_supervised_s43
  bimcv_pathc_h800_resnet18_teacher_ct_s44
  bimcv_pathc_h800_resnet18_xray_supervised_s44
  bimcv_pathc_h800_resnet18_teacher_ct_s45
  bimcv_pathc_h800_resnet18_xray_supervised_s45
  bimcv_pathc_h800_resnet18_xray_cross_modal_kd_s42
  bimcv_pathc_h800_resnet18_xray_cross_modal_kd_s43
  bimcv_pathc_h800_resnet18_xray_cross_modal_kd_s44
  bimcv_pathc_h800_resnet18_xray_cross_modal_kd_s45
)
done_task(){ local d="$RUN_ROOT/$1"; [ -s "$d/history.csv" ] && [ -s "$d/best_metrics.json" ] && [ -s "$d/best.pt" ]; }
epoch_of(){ local f="$LOG_ROOT/$1.log"; [ -f "$f" ] && grep -aoE 'epoch=[0-9]+' "$f" | tail -1 | cut -d= -f2 || echo 0; }
done_count=0
weighted=0
active=""
for t in "${TASKS[@]}"; do
  if done_task "$t"; then
    done_count=$((done_count+1))
    weighted=$((weighted+50))
  elif pgrep -af "jdcnet_exp.train.*$t" >/dev/null; then
    e=$(epoch_of "$t"); [ -z "$e" ] && e=0
    [ "$e" -gt 49 ] && e=49
    weighted=$((weighted+e))
    active="$active $t@$e/50"
  fi
done
percent=$(awk "BEGIN { printf \"%.1f\", 100*$weighted/(50*${#TASKS[@]}) }")
runner=$(pgrep -af 'run_pathc_h800|jdcnet_exp.train.*bimcv_pathc_h800' | grep -v grep || true)
if [ "$done_count" -lt "${#TASKS[@]}" ] && [ -z "$runner" ]; then
  screen -S pathc_h800 -X quit >/dev/null 2>&1 || true
  screen -dmS pathc_h800 bash /root/autodl-tmp/logs/bimcv_pathc_h800/run_pathc_h800.sh
  echo "ACTION restarted_h800_pathc_runner"
fi
if ! pgrep -af 'shutdown_after_pathc.sh' >/dev/null; then
  screen -dmS pathc_shutdown_watchdog bash /root/autodl-tmp/logs/bimcv_pathc_h800/shutdown_after_pathc.sh
  echo "ACTION restarted_h800_shutdown_watchdog"
fi
echo "HOST H800"
echo "DONE $done_count/${#TASKS[@]}"
echo "PERCENT $percent"
echo "ACTIVE$active"
df -h /root /root/autodl-tmp | awk '{print "DF "$0}'
'@

$r3090Health = @'
#!/usr/bin/env bash
set -u
ROOT=/data/JDCNET/src
RUN_ROOT=$ROOT/runs/bimcv_pathc
LOG_ROOT=/data/logs/bimcv_pathc
LOCK_DIR=$LOG_ROOT/locks
TASKS=(
  bimcv_resnet18_pathc_teacher_ct_s42
  bimcv_resnet18_pathc_xray_supervised_s42
  bimcv_resnet18_pathc_teacher_ct_s43
  bimcv_resnet18_pathc_xray_supervised_s43
  bimcv_resnet18_pathc_teacher_ct_s44
  bimcv_resnet18_pathc_xray_supervised_s44
  bimcv_resnet18_pathc_teacher_ct_s45
  bimcv_resnet18_pathc_xray_supervised_s45
  bimcv_resnet18_pathc_xray_cross_modal_kd_s42
  bimcv_resnet18_pathc_xray_cross_modal_kd_s43
  bimcv_resnet18_pathc_xray_cross_modal_kd_s44
  bimcv_resnet18_pathc_xray_cross_modal_kd_s45
)
done_task(){ local d="$RUN_ROOT/$1"; [ -s "$d/history.csv" ] && [ -s "$d/best_metrics.json" ] && [ -s "$d/best.pt" ]; }
epoch_of(){ local f="$LOG_ROOT/$1.log"; [ -f "$f" ] && grep -aoE 'epoch=[0-9]+' "$f" | tail -1 | cut -d= -f2 || echo 0; }
if [ -d "$LOCK_DIR" ]; then
  for pidf in "$LOCK_DIR"/*.lock/pid; do
    [ -f "$pidf" ] || continue
    pid=$(cat "$pidf" 2>/dev/null || true)
    if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
      rm -rf "$(dirname "$pidf")"
      echo "ACTION removed_stale_lock $(dirname "$pidf")"
    fi
  done
fi
done_count=0
weighted=0
active=""
for t in "${TASKS[@]}"; do
  if done_task "$t"; then
    done_count=$((done_count+1))
    weighted=$((weighted+50))
  elif pgrep -af "jdcnet_exp.train.*$t" >/dev/null; then
    e=$(epoch_of "$t"); [ -z "$e" ] && e=0
    [ "$e" -gt 49 ] && e=49
    weighted=$((weighted+e))
    active="$active $t@$e/50"
  fi
done
percent=$(awk "BEGIN { printf \"%.1f\", 100*$weighted/(50*${#TASKS[@]}) }")
runner=$(pgrep -af 'bimcv_pathc_gpu23_scheduler|jdcnet_exp.train.*bimcv_pathc' | grep -v grep || true)
if [ "$done_count" -lt "${#TASKS[@]}" ] && [ -z "$runner" ]; then
  cd "$ROOT" || exit 1
  screen -dmS bimcv_pathc_gpu23 bash ops/bimcv_pathc_gpu23_scheduler.sh
  echo "ACTION restarted_3090_pathc_scheduler"
fi
echo "HOST 3090"
echo "DONE $done_count/${#TASKS[@]}"
echo "PERCENT $percent"
echo "ACTIVE$active"
df -h /data | awk '{print "DF "$0}'
'@

function Install-RemoteHelpers {
    Copy-TextToRemoteH800 $h800Health '/tmp/monitor_h800_pathc.sh' | Out-Null
    Invoke-H800 'chmod +x /tmp/monitor_h800_pathc.sh' | Out-Null
    Copy-TextToRemote3090 $r3090Health '/tmp/monitor_3090_pathc.sh' | Out-Null
    Invoke-3090 'chmod +x /tmp/monitor_3090_pathc.sh' | Out-Null
}

function Run-Cycle {
    Write-Log 'cycle_start'
    Install-RemoteHelpers

    $h800 = Invoke-H800 '/tmp/monitor_h800_pathc.sh'
    $r3090 = Invoke-3090 '/tmp/monitor_3090_pathc.sh'
    @('=== H800 ===') + $h800 + @('=== 3090 ===') + $r3090 |
        Set-Content -Encoding UTF8 -Path $stateFile
    Write-Log ('h800_status ' + (($h800 | Where-Object { $_ -match '^(DONE|PERCENT|ACTIVE|ACTION)' }) -join ' | '))
    Write-Log ('r3090_status ' + (($r3090 | Where-Object { $_ -match '^(DONE|PERCENT|ACTIVE|ACTION)' }) -join ' | '))

    try {
        powershell -ExecutionPolicy Bypass -File src\ops\pull_h800_pathc_results.ps1 | Out-Null
        Write-Log 'pulled_h800_pathc_results'
    } catch {
        Write-Log ('pull_h800_failed ' + $_.Exception.Message)
    }

    try {
        powershell -ExecutionPolicy Bypass -File src\ops\pull_3090_pathc_results.ps1 | Out-Null
        Write-Log 'pulled_3090_pathc_results'
    } catch {
        Write-Log ('pull_3090_failed ' + $_.Exception.Message)
    }

    $h800Analysis = 'docs\tmp\h800_pathc\analysis.txt'
    if (Test-Path $h800Analysis) {
        $first = (Get-Content $h800Analysis -TotalCount 1)
        if ($first -match 'completed_runs=12') {
            New-Item -ItemType Directory -Force -Path 'docs\tmp\h800_pathc' | Out-Null
            try {
                Copy-H800File '/root/autodl-tmp/logs/bimcv_pathc_h800/pathc_h800_final_results.tgz' 'docs\tmp\h800_pathc\pathc_h800_final_results.tgz' | Out-Null
                Write-Log 'pulled_h800_final_archive'
            } catch {
                Write-Log ('pull_h800_archive_pending ' + $_.Exception.Message)
            }
            Invoke-H800 'touch /root/autodl-tmp/logs/bimcv_pathc_h800/local_pull_done' | Out-Null
            Write-Log 'marked_h800_local_pull_done'
        }
    }
    Write-Log 'cycle_end'
}

Write-Log "monitor_start interval_seconds=$IntervalSeconds once=$Once"
do {
    try {
        Run-Cycle
    } catch {
        Write-Log ('cycle_failed ' + $_.Exception.Message)
    }
    if ($Once) { break }
    Start-Sleep -Seconds $IntervalSeconds
} while ($true)
