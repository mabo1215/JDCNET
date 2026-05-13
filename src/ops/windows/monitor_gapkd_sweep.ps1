# Continuous monitoring script - Check every minute until first of 7 configs creates run directory

$ssh_pass = 'mabo1215'
$ssh_host = 'mabo1215@10.147.20.176'
$checkCount = 0

Write-Host "$(Get-Date -Format 'HH:mm:ss') [MONITOR] Start monitoring 7 configs...`n" -ForegroundColor Cyan

while ($true) {
    $checkCount++
    $timestamp = Get-Date -Format 'HH:mm:ss'
    
    # Remote bash command to check for run directories
    $bash_cmd = 'for cfg in bimcv_sweep_thr065_proj0000_s44 bimcv_sweep_thr065_proj0020_s42 bimcv_sweep_thr065_proj0020_s43 bimcv_sweep_thr065_proj0020_s44 bimcv_sweep_thr065_proj0050_s42 bimcv_sweep_thr065_proj0050_s43 bimcv_sweep_thr065_proj0050_s44; do if [ -d /data/JDCNET/src/runs/bimcv_gapkd_sweep/$cfg ]; then echo $cfg: FOUND; else echo $cfg: waiting; fi; done'
    
    # Encode and execute
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash_cmd))
    $result = wsl sshpass -p $ssh_pass ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR $ssh_host "printf '%s' '$b64' | base64 -d | bash" 2>&1
    
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
