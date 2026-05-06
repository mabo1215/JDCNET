# JDCNET Download Progress - May 5/6 2026

## H800 (root@connect.westc.seetacloud.com:12437)

### Negative Cohort (BIMCV-COVID19-cIter_1_2-Negative)
```
total_paired_subjects: 398
downloaded_subjects: 297
progress_percent: 74.6%
data_size_gb: 41
can_start_training_now: true
readiness_reason: "Negative cohort at 297/398 (74.6%). Sufficient for training workflow."
```

### Training Readiness
- ✅ **Negative:** 297/398 subjects (READY - exceeds 20 minimum)
- ❌ **Positive:** Not applicable (H800 only requires negative for validation)
- **Status:** Training can begin immediately on H800 using negative cohort

---

## R3090 (mabo1215@10.147.20.176)

### Positive Cohort (BIMCV-COVID19)
```
total_paired_subjects: 113
downloaded_subjects: 18
progress_percent: 15.9%
data_size_gb: 2.1
can_start_training_now: false
readiness_reason: "Positive cohort at 18/113 (15.9%). Need >=20 subjects for training. ETA 1-2 hours."
```

### Negative Cohort (BIMCV-COVID19-cIter_1_2-Negative)
```
total_paired_subjects: 398
downloaded_subjects: 368
progress_percent: 92.5%
data_size_gb: 52
can_start_training_now: true
readiness_reason: "Negative cohort at 368/398 (92.5%). Sufficient for training workflow."
```

### Training Readiness
- ❌ **Positive:** 18/113 subjects (NOT READY - need 20 minimum) - ETA **+1-2 hours**
- ✅ **Negative:** 368/398 subjects (READY - exceeds 20 minimum)
- **Status:** Cannot start training yet. Waiting for positive to reach 20 subjects.
- **Process:** Background download active (python3 -m jdcnet_exp.download_bimcv_paired)
- **Next milestone:** 20/113 positive → triggers training readiness

---

## Combined System Status

### Data Readiness Checklist
- [x] H800 negative: 297/398 (74.6%) ✅
- [ ] R3090 positive: 18/113 (15.9%) ⏳ Need +2 more subjects
- [x] R3090 negative: 368/398 (92.5%) ✅

### Training Approval Criteria
```
training_can_begin = (
    h800_negative >= 20 AND           # ✅ 297 >= 20
    r3090_positive >= 20 AND          # ⏳ 18 >= 20 (FALSE)
    r3090_negative >= 20              # ✅ 368 >= 20
)
```

**Current:** ❌ BLOCKED (waiting for R3090 positive to reach 20)

### Next Steps
1. Monitor R3090 positive download (currently 18/113)
2. When positive reaches 20, execute training pipeline
3. Parallel workflow: Both H800 and R3090 begin with available data
4. Complete positive download (remaining 93 subjects) during training

### Timeline Estimate
- **Time to 20 positive subjects:** ~1-2 hours (need 2 more from current 18)
- **Time to 100 positive subjects:** ~6-8 hours  
- **Time to full completion (113):** ~10-12 hours

---

## Implementation Notes

### Code Versions
- Positive downloader: B2Drop WebDAV implementation (replaces Kaggle API)
- Negative downloader: B2Drop WebDAV (working as expected)
- Both use token-based authentication with manifest-driven extraction

### Infrastructure
- H800: Stable, high download rate (completed negative)
- R3090: Recovering from network issues, positive download restarted
- B2Drop source: Verified accessible with 113 positive + 398 negative pairs total

### Monitoring Commands
```bash
# H800 - Check status
plink -P 12437 root@connect.westc.seetacloud.com 'ls -d /root/autodl-tmp/bimcv_neg_paired/sub-S* | wc -l'

# R3090 - Check positive progress
plink mabo1215@10.147.20.176 'ls -d /data/bimcv_paired/sub-S* 2>/dev/null | wc -l'

# R3090 - Check negative progress  
plink mabo1215@10.147.20.176 'ls -d /data/bimcv_neg_paired/sub-S* 2>/dev/null | wc -l'

# R3090 - Monitor download log
plink mabo1215@10.147.20.176 'tail -20 /data/logs/bimcv_pos_download.log'
```

---

Generated: 2026-05-05/06 22:41 UTC

---

## Current Issues Before Reboot (Recorded May 6, 2026)

1. R3090 network/connectivity is unstable.
- Multiple `plink` commands to `10.147.20.176` intermittently failed with timeout/abort.
- Last successful check showed positive downloader syntax is OK (`SYNTAX_OK`).

2. H800 SSH connectivity is intermittent.
- Some `plink`/`ssh` commands to `connect.westc.seetacloud.com:12437` returned timeout or non-zero exit.

3. PowerShell quoting can break complex remote commands.
- Nested quotes, pipes, and Python one-liners are error-prone in PowerShell + plink.
- Prefer simple single-purpose commands, or execute via WSL bash path.

4. R3090 positive download readiness threshold was still not met at last confirmed snapshot.
- Last confirmed value in this doc: `18/113`.
- Training gate requires positive `>=20`.

## Post-Reboot Quick Check Checklist

Run these in order and update numbers in this file.

1. Verify R3090 connectivity.
```powershell
plink -ssh -batch -hostkey "ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0" -l mabo1215 -pw "mabo1215" 10.147.20.176 "echo R3090_OK; hostname; whoami"
```

2. Verify H800 connectivity.
```powershell
plink -ssh -batch -hostkey "ssh-ed25519 255 SHA256:liZ36vNCsNcNdXeWs4f+g5ZIhPM/ZihP834vxs8Ulqc" -P 12437 -l root -pw "k5qShTLQWF5a" connect.westc.seetacloud.com "echo H800_OK; hostname; whoami"
```

3. Re-check R3090 positive/negative subject counts.
```powershell
plink -ssh -batch -hostkey "ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0" -l mabo1215 -pw "mabo1215" 10.147.20.176 "echo POS; ls -d /data/bimcv_paired/sub-S* 2>/dev/null | wc -l; echo NEG; ls -d /data/bimcv_neg_paired/sub-S* 2>/dev/null | wc -l"
```

4. Confirm R3090 positive downloader process state.
```powershell
plink -ssh -batch -hostkey "ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0" -l mabo1215 -pw "mabo1215" 10.147.20.176 "pgrep -af download_bimcv_paired || echo POS_DOWNLOADER_NOT_RUNNING"
```

5. If process is not running, restart it.
```powershell
plink -ssh -batch -hostkey "ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0" -l mabo1215 -pw "mabo1215" 10.147.20.176 "nohup python3 -m jdcnet_exp.download_bimcv_paired --output-dir /data/bimcv_paired > /data/logs/bimcv_pos_download.log 2>&1 &"
```

6. Confirm training gate.
- Ready condition:
    - H800 negative `>=20`
    - R3090 negative `>=20`
    - R3090 positive `>=20`
- If all true, start training immediately.

Updated: 2026-05-06

---

## WSL 稳定命令模板（非交互式，sshpass 消除密码弹窗）

> `sshpass` 已在本机 WSL 确认可用（`/usr/bin/sshpass`）。
> `pgrep -f` 模式匹配已在 WSL 确认可用。
> 所有命令从 PowerShell 终端执行，outer 双引号给 PowerShell，inner 单引号给 bash。

### 规则：外层单引号，内层双引号
- PowerShell 对单引号内容**完全不解析**（`2>/dev/null`、`|`、`$` 均安全）
- bash 收到完整命令，传给 sshpass → ssh
- 远端命令用双引号包裹（bash 层已消耗单引号）

### 连通性测试
```powershell
# R3090
wsl bash -c 'sshpass -p mabo1215 ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new mabo1215@10.147.20.176 "echo R3090_OK; hostname"'

# H800
wsl bash -c 'sshpass -p k5qShTLQWF5a ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -p 12437 root@connect.westc.seetacloud.com "echo H800_OK; hostname"'
```

### 进度快照
```powershell
# R3090 — 正/负样本数 + 进程状态
wsl bash -c 'sshpass -p mabo1215 ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new mabo1215@10.147.20.176 "echo POS_COUNT:; ls /data/bimcv_paired/ 2>/dev/null | grep -c sub-S; echo NEG_COUNT:; ls /data/bimcv_neg_paired/ 2>/dev/null | grep -c sub-S; pgrep -af download_bimcv_paired || echo PROCESS_DEAD"'

# H800 — 负样本数 + 进程状态
wsl bash -c 'sshpass -p k5qShTLQWF5a ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -p 12437 root@connect.westc.seetacloud.com "echo NEG_COUNT:; ls /root/autodl-tmp/bimcv_neg_paired/ 2>/dev/null | grep -c sub-S; pgrep -af download_bimcv || echo PROCESS_DEAD"'
```

### 重启正样本下载（R3090 进程死亡时）
```powershell
wsl bash -c 'sshpass -p mabo1215 ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new mabo1215@10.147.20.176 "pkill -9 -f download_bimcv_paired; sleep 1; cd /data/JDCNET/src && nohup python3 -m jdcnet_exp.download_bimcv_paired --output-dir /data/bimcv_paired > /data/logs/bimcv_pos_download.log 2>&1 & sleep 2; pgrep -af download_bimcv_paired && echo STARTED || echo FAILED"'
```

### 查看下载日志
```powershell
wsl bash -c 'sshpass -p mabo1215 ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new mabo1215@10.147.20.176 "tail -30 /data/logs/bimcv_pos_download.log 2>/dev/null || echo NO_LOG"'
```

### 为什么用 sshpass 而不是 plink
| 方案 | 问题 |
|---|---|
| `plink` + PowerShell 双引号 | `2>/dev/null`、`\|`、`$()` 被 PowerShell 解析破坏 |
| `wsl ssh` 无 sshpass | 等待密码输入，无法脚本化 |
| `wsl sshpass ssh`（外层单引号）| ✅ 非交互式，PowerShell 完全透传，稳定 |

---

## Latest Verified Status (May 6, 2026)

### H800 (connect.westc.seetacloud.com:12437)
```text
total_paired_subjects: 398
downloaded_subjects: 297
progress_percent: 74.6%
can_start_training_now: true
readiness_reason: "H800 negative cohort remains at 297/398; exceeds training threshold."
```

### R3090 (10.147.20.176)
```text
positive_total_paired_subjects: 113
positive_downloaded_subjects: 113
positive_progress_percent: 100.0%

negative_total_paired_subjects: 398
negative_downloaded_subjects: 368
negative_progress_percent: 92.5%

can_start_training_now: true
readiness_reason: "R3090 positive reached full 113/113 and negative is 368/398."
```

### 3090 Training Main Flow (Persistent)

- Training was started with `nohup` so local shutdown will not stop remote execution.
- Verified process: `python3 -m jdcnet_exp.train --config configs/bimcv_neg_teacher_xray_main.json`
- Verified PID observed: `1084449` (elapsed > 10 min at check time).
- Log file: `/data/logs/train_main_flow.log`
- Active config on remote: `/data/JDCNET/src/configs/bimcv_neg_teacher_xray_main.json`

Persistent launcher used:

```powershell
plink -ssh -batch -hostkey "ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0" -l mabo1215 -pw "mabo1215" 10.147.20.176 'cd /data/JDCNET/src; export PYTHONPATH=/data/JDCNET/src; nohup python3 -m jdcnet_exp.train --config configs/bimcv_neg_teacher_xray_main.json > /data/logs/train_main_flow.log 2>&1 < /dev/null &'
```

Optional `screen` wrapper (double safety):

```powershell
plink -ssh -batch -hostkey "ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0" -l mabo1215 -pw "mabo1215" 10.147.20.176 'screen -dmS jdcnet_main bash -lc "cd /data/JDCNET/src; export PYTHONPATH=/data/JDCNET/src; nohup python3 -m jdcnet_exp.train --config configs/bimcv_neg_teacher_xray_main.json > /data/logs/train_main_flow.log 2>&1 < /dev/null"'
```

Quick checks for next boot:

```powershell
# Process
plink -ssh -batch -hostkey "ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0" -l mabo1215 -pw "mabo1215" 10.147.20.176 'pgrep -af -- "jdcnet_exp.train" || echo TRAIN_DOWN'

# Log tail
plink -ssh -batch -hostkey "ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0" -l mabo1215 -pw "mabo1215" 10.147.20.176 'tail -40 /data/logs/train_main_flow.log'
```
