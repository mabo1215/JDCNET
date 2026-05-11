param(
    [string]$EnvPath = 'C:\source\.env',
    [string]$RemoteRepo = '/root/autodl-tmp/JDCNET',
    [string]$OutDir = 'src\results\h800_gapkd_cpu_smoke',
    [int]$WaitSeconds = 20
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $repo
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$lines = Get-Content -LiteralPath $EnvPath
$password = $lines[4].Trim()
$plink = (Get-Command plink).Source
$pscp = (Get-Command pscp).Source

$hostName = 'connect.westc.seetacloud.com'
$port = 12437
$userName = 'root'
$hostKey = 'ssh-ed25519 255 SHA256:liZ36vNCsNcNdXeWs4f+g5ZIhPM/ZihP834vxs8Ulqc'

function Mask-Secrets($Items) {
    $Items | ForEach-Object {
        $s = [string]$_
        if ($password) { $s = $s -replace [regex]::Escape($password), '***' }
        $s
    }
}

function Invoke-H800([string]$Command) {
    $out = & $plink -ssh -batch -hostkey $hostKey -P $port -l $userName -pw $password $hostName $Command 2>&1
    Mask-Secrets $out
}

function Copy-H800File([string]$RemotePath, [string]$LocalPath) {
    $out = & $pscp -batch -q -hostkey $hostKey -P $port -l $userName -pw $password "${hostName}:$RemotePath" $LocalPath 2>&1
    Mask-Secrets $out
}

$archive = Join-Path $env:TEMP ("jdcnet_gapkd_src_" + [guid]::NewGuid().ToString("N") + ".tgz")
try {
    & tar -czf $archive `
        --exclude='__pycache__' `
        --exclude='*.pyc' `
        -C src jdcnet_exp ops/h800_gapkd_cpu_smoke.sh

    Invoke-H800 "mkdir -p '$RemoteRepo/src' /root/autodl-tmp/logs/gapkd_cpu_smoke /root/autodl-tmp/results/gapkd_cpu_smoke" | Out-Null
    & $pscp -batch -q -hostkey $hostKey -P $port -l $userName -pw $password $archive "${hostName}:/tmp/jdcnet_gapkd_src.tgz" 2>&1 | Mask-Secrets | Out-Null
    Invoke-H800 "tar -xzf /tmp/jdcnet_gapkd_src.tgz -C '$RemoteRepo/src' && chmod +x '$RemoteRepo/src/ops/h800_gapkd_cpu_smoke.sh'" | Out-Null
    Invoke-H800 "screen -S gapkd_cpu_smoke -X quit >/dev/null 2>&1 || true; screen -dmS gapkd_cpu_smoke bash '$RemoteRepo/src/ops/h800_gapkd_cpu_smoke.sh' '$RemoteRepo'" | Out-Null

    if ($WaitSeconds -gt 0) {
        Start-Sleep -Seconds $WaitSeconds
    }

    $status = Invoke-H800 @"
printf '__SCREEN__\n'; screen -ls 2>/dev/null | grep gapkd_cpu_smoke || true
printf '__LOG_TAIL__\n'; tail -n 80 /root/autodl-tmp/logs/gapkd_cpu_smoke/smoke.log 2>/dev/null || true
printf '__RESULT__\n'; cat /root/autodl-tmp/results/gapkd_cpu_smoke/smoke_gapkd.json 2>/dev/null || true
"@
    $status | Set-Content -Encoding UTF8 -Path (Join-Path $OutDir 'remote_status.txt')

    try {
        Copy-H800File '/root/autodl-tmp/logs/gapkd_cpu_smoke/smoke.log' (Join-Path $OutDir 'smoke.log') | Out-Null
    } catch {}
    try {
        Copy-H800File '/root/autodl-tmp/results/gapkd_cpu_smoke/smoke_gapkd.json' (Join-Path $OutDir 'smoke_gapkd.json') | Out-Null
    } catch {}

    Write-Host "H800 GAP-KD CPU smoke launched. Local status: $OutDir\remote_status.txt"
} finally {
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
}
