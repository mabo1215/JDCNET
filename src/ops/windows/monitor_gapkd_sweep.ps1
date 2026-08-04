# Continuous monitoring script - Check every minute until first of 7 configs creates run directory.
# Authentication is SSH public-key based through the WSL ssh-agent or ~/.ssh/config.

param(
    [string]$SshTarget = $env:JDCNET_R3090_SSH_TARGET,
    [int]$SshPort = 0
)

if ([string]::IsNullOrWhiteSpace($SshTarget)) {
    throw 'Set JDCNET_R3090_SSH_TARGET or pass -SshTarget with an SSH host or ~/.ssh/config alias.'
}

$ssh_options = @(
    '-o', 'BatchMode=yes',
    '-o', 'ConnectTimeout=5',
    '-o', 'StrictHostKeyChecking=accept-new',
    '-o', 'LogLevel=ERROR'
)
if ($SshPort -gt 0) {
    $ssh_options += @('-p', [string]$SshPort)
}
$checkCount = 0

Write-Host "$(Get-Date -Format 'HH:mm:ss') [MONITOR] Start monitoring 7 configs...`n" -ForegroundColor Cyan

while ($true) {
    $checkCount++
    $timestamp = Get-Date -Format 'HH:mm:ss'
    
    # Remote bash command to check for run directories
    $bash_cmd = 'for cfg in bimcv_sweep_thr065_proj0000_s44 bimcv_sweep_thr065_proj0020_s42 bimcv_sweep_thr065_proj0020_s43 bimcv_sweep_thr065_proj0020_s44 bimcv_sweep_thr065_proj0050_s42 bimcv_sweep_thr065_proj0050_s43 bimcv_sweep_thr065_proj0050_s44; do if [ -d /data/JDCNET/src/runs/bimcv_gapkd_sweep/$cfg ]; then echo $cfg: FOUND; else echo $cfg: waiting; fi; done'
    
    # Encode and execute
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash_cmd))
    $remote_command = "printf '%s' '$b64' | base64 -d | bash"
    $wsl_args = @('ssh') + $ssh_options + @($SshTarget, $remote_command)
    $result = & wsl.exe @wsl_args 2>&1
    
    # Check for FOUND
    if ($result -match 'FOUND') {
        Write-Host "`n$timestamp [OK] First config creating run directory!" -ForegroundColor Green
        Write-Host "`nResult:`n$result`n" -ForegroundColor Green
        break
    } else {
        Write-Host "$timestamp [Check #$checkCount] Waiting for first directory... (7 configs total)" -ForegroundColor Yellow
        Write-Host ($result | Select-Object -Last 3) -ForegroundColor Gray
        Write-Host ""
    }
    
    # Wait 60 seconds before next check
    Write-Host "Sleep 60 seconds..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 60
}

Write-Host "`n[END] Monitoring complete - $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
