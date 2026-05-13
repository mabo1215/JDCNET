@echo off
REM Deployment script for BIMCV positive downloader fix on 3090
REM Fix: Replace broken Kaggle-based code with B2Drop WebDAV implementation
REM Usage: Run this script when 3090 network is accessible

setlocal enabledelayedexpansion

set TARGET_HOST=10.147.20.176
set TARGET_USER=mabo1215
set TARGET_PASS=mabo1215
set TARGET_HOSTKEY=ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0
set PLINK="C:\Program Files\PuTTY\plink.exe"
set SCP="C:\Program Files\PuTTY\pscp.exe"
set LOCAL_FILE=C:\source\JDCNET\src\jdcnet_exp\download_bimcv_paired.py
set REMOTE_PATH=/data/JDCNET/src/jdcnet_exp/download_bimcv_paired.py
set REMOTE_LOG=/data/logs/bimcv_pos_download.log

echo ========================================
echo BIMCV Positive Downloader Deployment
echo ========================================
echo.
echo Step 1: Test connectivity to 3090...
echo.

%PLINK% -ssh -batch -hostkey "%TARGET_HOSTKEY%" -l %TARGET_USER% -pw %TARGET_PASS% %TARGET_HOST% "echo ===CONNECTIVITY_TEST===" ^
  && echo PASS: 3090 is reachable ^
  || (echo FAIL: Cannot reach 3090 && exit /b 1)

echo.
echo Step 2: Kill old Kaggle-based process...
echo.

%PLINK% -ssh -batch -hostkey "%TARGET_HOSTKEY%" -l %TARGET_USER% -pw %TARGET_PASS% %TARGET_HOST% ^
  "pgrep -f download_bimcv_paired || true; pkill -9 -f download_bimcv_paired; sleep 1; echo ===KILLED===" ^
  || echo Warning: process kill may have failed, continuing...

echo.
echo Step 3: Deploy new B2Drop-based code...
echo.

%SCP% -ssh -batch -hostkey "%TARGET_HOSTKEY%" -l %TARGET_USER% -pw %TARGET_PASS% ^
  "%LOCAL_FILE%" "%TARGET_USER%@%TARGET_HOST%:%REMOTE_PATH%"

if errorlevel 1 (
  echo FAIL: Could not copy file to 3090
  exit /b 1
)

echo Deployed to %REMOTE_PATH%

echo.
echo Step 4: Verify deployment...
echo.

%PLINK% -ssh -batch -hostkey "%TARGET_HOSTKEY%" -l %TARGET_USER% -pw %TARGET_PASS% %TARGET_HOST% ^
  "grep -c BIMCV_POS_SHARE_TOKEN %REMOTE_PATH% && echo ===FILE_VERIFIED===" ^
  || (echo FAIL: File verification failed && exit /b 1)

echo.
echo Step 5: Start positive download process...
echo.

%PLINK% -ssh -batch -hostkey "%TARGET_HOSTKEY%" -l %TARGET_USER% -pw %TARGET_PASS% %TARGET_HOST% ^
  "nohup python3 %REMOTE_PATH% > %REMOTE_LOG% 2>&1 &; sleep 2; pgrep -f download_bimcv_paired && echo ===PROCESS_STARTED===" ^
  || (echo FAIL: Could not start process && exit /b 1)

echo.
echo ========================================
echo SUCCESS: Deployment complete!
echo ========================================
echo.
echo Monitor download with:
echo   plink ... 10.147.20.176 "tail -f /data/logs/bimcv_pos_download.log"
echo.
echo Check progress with:
echo   plink ... 10.147.20.176 "ls -d /data/bimcv_paired/sub-S* 2>/dev/null ^| wc -l"
echo.
echo Expected: Download of 113 paired subjects from B2Drop
echo.
