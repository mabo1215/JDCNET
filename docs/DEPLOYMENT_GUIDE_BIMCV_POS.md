# BIMCV Positive Downloader Fix - Deployment Guide

## Problem Statement
The `download_bimcv_paired.py` script on R3090 is using an obsolete Kaggle API approach that references non-existent datasets (`rafiko1/bimcv-covid19-a-0` through `-j-0`). This causes immediate 404 failures.

**Evidence:**
```
requests.exceptions.HTTPError: 404 Client Error: Not Found for url: 
https://www.kaggle.com/api/v1/datasets/list/rafiko1/bimcv-covid19-a-0...
```

## Solution
Replace with B2Drop WebDAV-based implementation that mirrors the successful negative cohort downloader.

**File:** `/data/JDCNET/src/jdcnet_exp/download_bimcv_paired.py`

**Key Changes:**
- Switch from Kaggle API to B2Drop public share access
- Token: `BIMCV-COVID19` (positive cohort, 113 paired subjects)
- Auth: Basic auth with token as username, empty password
- Archives: Enumerate via WebDAV PROPFIND, download via HTTP GET
- Manifest matching: Try both `.tgz.tar-tvf.txt` and `.tar.gz.tar-tvf.txt` patterns

## Deployment Steps

### Option A: Use Batch Script (Windows)
```batch
cd C:\source\JDCNET
deploy_bimcv_pos_fix.bat
```

This script will:
1. Test connectivity
2. Kill old process
3. Copy new code
4. Verify deployment
5. Start downloader

### Option B: Manual Steps (If batch fails)

#### 1. Verify 3090 is reachable
```
plink -ssh -batch -hostkey "ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0" ^
  -l mabo1215 -pw "mabo1215" 10.147.20.176 "hostname"
```

#### 2. Stop old process
```
plink -ssh -batch -hostkey "ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0" ^
  -l mabo1215 -pw "mabo1215" 10.147.20.176 ^
  "pkill -9 -f download_bimcv_paired; sleep 1; echo Killed"
```

#### 3. Copy new file via SCP
```
pscp -ssh -batch -hostkey "ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0" ^
  -l mabo1215 -pw "mabo1215" ^
  C:\source\JDCNET\src\jdcnet_exp\download_bimcv_paired.py ^
  mabo1215@10.147.20.176:/data/JDCNET/src/jdcnet_exp/
```

#### 4. Start downloader
```
plink -ssh -batch -hostkey "ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0" ^
  -l mabo1215 -pw "mabo1215" 10.147.20.176 ^
  "nohup python3 /data/JDCNET/src/jdcnet_exp/download_bimcv_paired.py > /data/logs/bimcv_pos_download.log 2>&1 &; sleep 2; pgrep -f download_bimcv_paired && echo ===STARTED==="
```

## Monitoring

### Check process status
```
plink ... 10.147.20.176 "pgrep -af download_bimcv_paired | head -1"
```

### Check download progress
```
plink ... 10.147.20.176 "ls -d /data/bimcv_paired/sub-S* 2>/dev/null | wc -l"
```

### View log tail
```
plink ... 10.147.20.176 "tail -50 /data/logs/bimcv_pos_download.log"
```

### Expected log output
```
Enumerating 35 BIMCV parts to find paired subjects ...
Downloading paired subjects from BIMCV ...
Downloaded: /data/bimcv_paired/sub-S00001/...
...
Done. NNN subjects in /data/bimcv_paired
Report written to /data/bimcv_paired/download_report_pos.json
```

## Expected Outcomes

**Before fix:**
- Positive: 0/113 subjects
- Log shows: Kaggle 404 errors
- Process: Exits with error

**After fix:**
- Positive: Gradually increases toward 113
- Log shows: WebDAV PROPFIND, archive enumeration, extraction
- Process: Runs to completion, writes report

## Training Readiness

Both cohorts must reach >=20 subjects before training can start:

**Current status (May 6):**
- H800 Negative: 297/398 = 74.6% ✅ (can train now)
- R3090 Negative: 368/398 = 92.5% ✅
- R3090 Positive: 0/113 = 0% ❌ (BLOCKED on deployment)

**After deployment:**
- R3090 Positive should reach 20 subjects within 1-2 hours
- Both cohorts will then be >= 20 and training can begin

## Troubleshooting

**Symptom:** "404 Not Found" errors in log
- **Cause:** Old Kaggle-based code still running
- **Fix:** Re-run deployment script, verify file was copied

**Symptom:** "ModuleNotFoundError" (missing requests, tarfile, etc.)
- **Cause:** Python environment missing dependencies
- **Fix:** Python 3.8+ with requests library should be available

**Symptom:** "Connection refused" or "Connection timed out"
- **Cause:** 3090 network unreachable
- **Action:** Wait and retry; may be temporary connectivity issue

**Symptom:** Process exits immediately
- **Cause:** Directory `/data/bimcv_paired` missing or permissions issue
- **Fix:** Check directory exists with `ls -la /data/bimcv_paired`

## File Contents Reference

The replacement file contains these main functions:

- `_webdav_auth(token)` - Generate Basic auth header
- `_webdav_list(token, path)` - PROPFIND to list B2Drop contents
- `_http_download(token, filename, dest)` - Download file via GET
- `_parse_tvf_manifest(text)` - Parse tar -tvf output for subject/CT/CXR pairs
- `_paired_from_subjects(subjects)` - Filter to only same-patient pairs
- `_manifest_name_candidates(archive_name)` - Handle both `.tgz` and `.tar.gz` naming
- `_fetch_manifest_text(token, archive_name)` - Retrieve manifest with retry/backoff
- `_extract_paired_from_archive(archive_path, paired_members, output_dir)` - Extract from tarball
- `run(token, archives, output_dir, dry_run, min_ct_bytes)` - Main orchestration

Report output: `/data/bimcv_paired/download_report_pos.json`
