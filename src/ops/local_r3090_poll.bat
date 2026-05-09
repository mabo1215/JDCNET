@echo off
rem Wrapper for hourly R3090 polling. Invoked by Windows Task Scheduler.
rem The wsl.exe command runs the bash poller; output goes to a small log
rem inside the snapshot dir (poll.log) so this stdout can stay quiet.
wsl.exe bash /mnt/c/source/JDCNET/ops/local_r3090_poll.sh
exit /b %ERRORLEVEL%
