param([string]$EnvPath = 'C:\source\.env')
$lines = Get-Content -LiteralPath $EnvPath
$pw = $lines[8].Trim()
$hk = 'ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0'
$cmd = 'ROOT=/data1/midrc/raw_559cases_combined; M=/data/secure/midrc/MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.manifest.json; zip_done=$(find $ROOT -type f -name "*.zip" | wc -l); total_obj=$(grep -c "object_id" $M 2>/dev/null || echo unknown); size=$(du -sh $ROOT 2>/dev/null | cut -f1); disk=$(df -h /data1 | tail -1); echo ZIPS_DONE=$zip_done; echo MANIFEST_OBJECTS=$total_obj; echo SIZE=$size; echo "$disk"; tail -3 /data1/logs/midrc/midrc_559_progress.tsv 2>/dev/null'
$result = & plink -ssh -batch -hostkey $hk -l mabo1215 -pw $pw 10.147.20.176 $cmd 2>&1
$result | ForEach-Object { $_ -replace [regex]::Escape($pw), '***' }
