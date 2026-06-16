# Revision Roadmap - TCSVT 拒稿后的修订路线图

本文档根据 `docs/revision_suggestions.tex` 重写。拒稿意见可以归纳为三点：单 cohort、只报相对提升、teacher gate 未校准。修订路线图只围绕这三点展开，避免引入无关的新故事。

---

## 1. 拒稿原因分解

| ID | 拒稿原因 | 必须补的证据 |
|---|---|---|
| F1 | 评估只限于 510 例单一 cohort，无法证明 cross-domain generalization，存在 dataset-specific bias | 外部 cohort 验证、跨源 train/test matrix；若可行，外部 same-patient CT-Xray paired replication |
| F2 | 只报告相对提升，例如 `Delta BA = +0.035`，没有绝对 baseline 指标 | 主文和摘要补充 baseline/JDCNet 的 BA、AUC、F1、sensitivity、specificity 和 CI |
| F3 | confidence gate 来自未校准 teacher，可能因 overconfidence 让 student 学错 target distribution | teacher temperature scaling、calibrated confidence gate、overconfidence ablation、ECE/reliability 图 |

优先级：F1 最大，F3 次之，F2 最容易修复但必须立即补齐。

---

## 2. P0: 投稿前必须完成

| ID | 对应问题 | 行动 | 输出 |
|---|---|---|---|
| A1 | F2 | 汇总现有 artifact 的绝对指标 | absolute metrics table，摘要中的绝对 BA/AUC |
| A2 | F3 | teacher temperature scaling + calibrated confidence gate | calibrated gate 结果、ECE/MCE、reliability diagram |
| A3 | F3 | overconfidence stress ablation，比较 `T=0.5`, `T=1`, `T=T_cal` | 证明未校准过度自信会伤害 gate，校准可缓解 |
| A4 | F1 | frozen X-ray student 在外部 X-ray cohort 上推理 | external BA/AUC/F1/sens/spec + bootstrap CI |

P0 完成后，论文至少能明确回应全部三条拒稿原因。

---

## 3. P1: 强烈建议完成

| ID | 对应问题 | 行动 | 价值 |
|---|---|---|---|
| B1 | F1 | 外部 same-patient paired CT-Xray cohort 上重跑完整 JDCNet gate | 最强 F1 反驳；若通过，可主张 transfer mechanism 跨 cohort 复现 |
| B2 | F1 | cross-source transfer matrix | 把泛化问题量化成 same-source vs cross-source gap |
| B3 | F3 | calibrated-quantile gate sweep | 证明 gate 对阈值选择稳定，不是单点偶然 |

若 B1 因数据不可得无法完成，A4 + B2 是 F1 的现实替代方案。

---

## 4. 远端 3090 使用路线

### 4.1 机器与路径

- Host: `mabo1215@10.147.20.176`
- GPU: 4x RTX 3090
- Remote code root: `/data/JDCNET/src`
- Remote data root: `/data1`
- Local helper: `src/tmp_sync/ssh3090.sh`
- 推荐运行环境：WSL-first

### 4.2 当前连接阻塞

用户当前执行：

```bash
ssh mabo1215@10.147.20.176
# ssh: connect to host 10.147.20.176 port 22: No route to host
```

本机复查也显示：

- Windows `ping 10.147.20.176`: 100% timeout
- WSL `nc -vz -w 3 10.147.20.176 22`: `No route to host`

结论：这是网络路由/overlay 网络问题，不是 SSH 密码、密钥或用户名问题。远端实验目前被阻塞。

### 4.3 恢复连接前的检查清单

本地 WSL：

```bash
ip route
ping -c 2 -W 2 10.147.20.176
nc -vz -w 3 10.147.20.176 22
```

Windows：

```powershell
ping 10.147.20.176
tracert -d 10.147.20.176
```

远端管理员需要确认：

```bash
ip addr | grep 10.147.20.176
systemctl status ssh || service ssh status
ss -tlnp | grep ':22'
nvidia-smi
```

只有当以下命令成功后，才启动训练：

```bash
bash src/tmp_sync/ssh3090.sh 'hostname; nvidia-smi'
```

### 4.4 标准运行模式

所有复杂远端命令写成 `.sh` 脚本，不在 PowerShell 中拼复杂引号。每个 sweep 使用以下模式：

1. 在 `src/configs/<sweep>/` 生成配置。
2. 将任务 round-robin 分到 GPU 0-3。
3. 用 detached `screen` 启动每个 GPU queue。
4. 每个 run 写出 `best_metrics.json`、`best.pt`、日志。
5. summarize 脚本汇总 Delta BA、absolute metrics、CI、PASS/FAIL。

典型生命周期：

```bash
bash src/ops/<new_sweep>.sh
bash src/tmp_sync/ssh3090.sh 'screen -ls'
bash src/ops/<new_sweep>_summarize.sh
```

---

## 5. GPU 任务预算

| Task | Runs | 预计时间 | 备注 |
|---|---:|---:|---|
| A1 absolute metrics | 0 GPU | 立即 | 汇总现有 JSON |
| A2 calibrated gate | 约 60 | 约 1.5 h | 两个已通过配置，5-fold x 3 seeds |
| A3 overconfidence ablation | 约 60 | 约 1.5 h | `T=0.5`, `T=1`, `T=T_cal` |
| A4 external X-ray inference | inference only | < 0.5 h | frozen checkpoints |
| B1 external paired gate | 约 240 | 约 6 h | 依赖 paired data |
| B2 cross-source matrix | 约 30 | 约 1.5 h | 依赖 external manifest |
| B3 calibrated quantile sweep | 约 90 | 约 2.5 h | 依赖 A2 |

---

## 6. 具体执行顺序

### Step 1: 先做不依赖 GPU 的 F2 修复

- 汇总已有 `best_metrics.json`。
- 生成 absolute metrics table。
- 修改摘要和 main results，使所有相对提升都有绝对 baseline/JDCNet 数值支撑。

### Step 2: 恢复远端 3090 连接

- 修复 `No route to host`。
- 确认 `ssh`、`screen`、`nvidia-smi` 可用。
- 确认 `/data/JDCNET/src` 与本地 repo 同步。

### Step 3: 完成 F3 方法修复

- 实现 teacher temperature scaling。
- gate 改为 calibrated confidence。
- 重跑 A2。
- 做 A3 overconfidence ablation。
- 若时间允许，做 B3 quantile gate sweep。

### Step 4: 完成 F1 外部验证

- 先做 A4 frozen external X-ray inference。
- 再做 B2 cross-source matrix。
- 若 same-patient paired CT-Xray 外部数据可得，做 B1。

### Step 5: 论文整合

- Abstract: 加 absolute BA/AUC + external result。
- Methods: 加 `Calibration Safeguard`。
- Experiments: 加 absolute table、external validation、calibration ablation。
- Limitations: 如无 B1，说明 paired external replication 受数据可得性限制。
- Cover letter: 按 F1/F2/F3 逐条回应。

---

## 7. Manuscript Checklist

- [ ] Abstract 中同时报告 baseline 和 JDCNet 绝对 BA/AUC。
- [ ] Main text 中加入 absolute metrics table。
- [ ] Methodology 中加入 temperature scaling 和 calibrated gate。
- [ ] Experiments 中加入 ECE/reliability diagram。
- [ ] Experiments 中加入 overconfidence ablation。
- [ ] Experiments 中加入 external validation。
- [ ] 若可行，加入 paired external replication。
- [ ] 更新 `docs/cover_letter.txt`。
- [ ] 更新 `docs/progress.md`。
- [ ] 运行 `paper/build.bat` 并确认页数限制。

---

## 8. Stop Conditions

- Best case: B1 通过，说明 JDCNet transfer claim 在外部 paired cohort 上复现。
- Expected case: A1-A4 + B2 完成，说明论文已经补齐绝对指标、校准机制和外部域验证。
- Minimum case: A1-A4 完成，至少可以有针对性回应三条拒稿原因。
- Blocked case: 若 3090 长期不可达，则先完成 A1、数据 manifest、代码脚本和论文结构改写；训练结果等待网络恢复。

最后更新：2026-06-16。
