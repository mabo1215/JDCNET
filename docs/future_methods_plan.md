# Future Methods Plan - 针对拒稿原因的实验改进计划

本文档依据 `docs/revision_suggestions.tex` 重写，目标是把拒稿意见转化为可执行的实验与论文修改。拒稿核心不是 JDCNet 思路本身，而是三类证据不足：

- F1: 只在一个 510 例 cohort 上评估，缺少跨数据域泛化验证，结果可能受单一数据集偏置影响。
- F2: 只报告相对提升，例如 balanced accuracy 增加约 0.035，缺少 baseline 与 JDCNet 的绝对指标，难以判断临床可用性。
- F3: confidence gate 直接使用未校准 teacher 的 softmax 置信度，存在 teacher 过度自信并把错误分布强制传给 student 的风险。

修订目标是：用外部验证回应 F1，用绝对指标回应 F2，用 teacher calibration + overconfidence ablation 回应 F3。远端 4x RTX 3090 只用于需要重跑或推理的部分；绝对指标汇总优先本地/远端 CPU 完成。

---

## 0. 远端 3090 可用性前置检查

远端 GPU 信息：

- Host: `mabo1215@10.147.20.176`
- Code root: `/data/JDCNET/src`
- Data root: `/data1`
- Repo helper: `src/tmp_sync/ssh3090.sh`
- 推荐入口: WSL 中执行 `bash src/tmp_sync/ssh3090.sh '<remote command>'`

当前发现的阻塞：

```bash
ssh mabo1215@10.147.20.176
# ssh: connect to host 10.147.20.176 port 22: No route to host
```

本机复查结果同样显示不可达：Windows ping 超时，WSL `nc -vz -w 3 10.147.20.176 22` 返回 `No route to host`。这不是密码、密钥或用户名错误，而是网络层没有到该主机的可用路由，常见原因包括 ZeroTier/VPN 未连接、远端主机离线、远端未加入同一 overlay 网络、IP 变更、防火墙或 sshd 未启动。

在启动任何 3090 实验前，必须先完成以下检查：

```bash
# WSL 本地检查
ip route
ping -c 2 -W 2 10.147.20.176
nc -vz -w 3 10.147.20.176 22

# Windows 本地检查
ping 10.147.20.176
tracert -d 10.147.20.176
```

需要远端机器管理员确认：

```bash
ip addr | grep 10.147.20.176
systemctl status ssh || service ssh status
ss -tlnp | grep ':22'
nvidia-smi
```

只有当 `ssh mabo1215@10.147.20.176` 或 `bash src/tmp_sync/ssh3090.sh 'hostname; nvidia-smi'` 成功后，下面的 GPU 计划才可执行。若 3090 暂时不可达，先完成 A1、论文表格、脚本准备和外部数据 manifest 准备；所有训练任务排队等待网络恢复。

---

## A1. 绝对指标补全 - 回应 F2

### 目的

F2 是报告方式问题。论文不能只写 `Delta BA = +0.035`，必须同时写 baseline 和 JDCNet 的绝对 BA、ROC-AUC、macro-F1、sensitivity、specificity，并给出 patient-level bootstrap 95% CI。

### 实施

1. 从现有 run artifact 的 `best_metrics.json` 汇总：
   - supervised X-ray baseline
   - CT teacher, 包括 mid / 3-slice teacher
   - 已通过 gate 的 JDCNet 配置，例如 3-slice soft-KL 和 mid hard
2. 生成主文表格：每行包括 model、BA、AUC、macro-F1、sensitivity、specificity、95% CI。
3. 摘要和实验结果中必须成对报告：
   - `supervised baseline BA = ...`
   - `JDCNet BA = ...`
   - `Delta BA = ...`

### 远端/本地执行

A1 不需要 GPU，可在网络恢复前先完成。如果 artifact 只在 3090 上，则网络恢复后执行：

```bash
bash src/tmp_sync/ssh3090.sh 'cd /data/JDCNET/src && python3 -m jdcnet_exp.summarize_runs \
  --runs runs/bimcv_pseudolabel_cv runs/bimcv_pseudolabel_soft runs/bimcv_pseudolabel_lam15 \
  --metrics balanced_accuracy roc_auc macro_f1 sensitivity specificity \
  --bootstrap 10000 \
  --out /data1/reports/absolute_metrics_table.json'
```

### 论文写法

在摘要和 main results 中明确写绝对值。相对提升只能作为补充，不再单独出现。

---

## A2. Calibrate-Then-Gate - 回应 F3 的核心方法

### 目的

审稿人担心 gate 依赖未校准 teacher 的 softmax confidence。如果 teacher 过度自信，student 会学习到高置信度但错误的 pseudo-target。改进方式是先校准 teacher，再用校准后的置信度做 gate。

### 方法

1. 每个 fold 内保留 calibration split，或使用 out-of-fold teacher prediction。
2. 对 teacher logits 拟合 temperature scaling：

   ```text
   p_cal = softmax(logits / T_cal)
   ```

3. 将原始 gate：

   ```text
   max(softmax(logits)) > tau
   ```

   改为：

   ```text
   max(softmax(logits / T_cal)) > tau
   ```

4. 报告校准前后：
   - ECE / MCE
   - reliability diagram
   - gate coverage
   - retained pseudo-label error rate
   - student absolute metrics and Delta BA

### 远端 3090 执行

网络恢复后新增并运行脚本：

```bash
# 1. 拟合每个 fold / teacher 的 temperature
bash src/tmp_sync/ssh3090.sh 'cd /data/JDCNET/src && python3 -m jdcnet_exp.calibration_report \
  --teachers mid 3slice \
  --fit-temperature \
  --out /data1/reports/teacher_tcal.json'

# 2. 重跑已通过 gate 的 JDCNet 配置，使用 calibrated confidence
bash src/ops/remote_3090_calibrated_gate.sh
bash src/ops/remote_3090_calibrated_gate_summarize.sh
```

预计计算量：约 60 个 fold/seed run，4x3090 约 1.5 小时。

### 需要修改的代码接口

- `jdcnet_exp.calibration_report`: 增加 fit temperature 与 per-fold 输出。
- `train_pseudolabel.py` / distillation 相关模块：增加 `teacher_temperature` 或 `teacher_temperature_file`。
- confidence mask 统一通过校准后的 probability 计算。

---

## A3. Overconfidence Stress Ablation - 回应 F3 的证据实验

### 目的

不仅声明校准有用，还要复现审稿人担心的失败模式：当 teacher 被人为 sharpen 后，错误 pseudo-label 更容易通过 gate，student 性能应下降或不稳定；校准后应缓解该问题。

### 设计

对同一 teacher/student 配置比较三种 teacher confidence：

| Regime | Temperature | 目的 |
|---|---:|---|
| Sharpened teacher | `T = 0.5` | 模拟过度自信 teacher |
| Raw teacher | `T = 1.0` | 当前论文设置 |
| Calibrated teacher | `T = T_cal` | 新方法 |

每组报告：

- teacher ECE
- gate coverage
- admitted pseudo-label error rate
- student BA/AUC/F1
- Delta BA and CI

### 远端 3090 执行

复用 A2 的 calibrated gate 脚本，只改变 temperature regime：

```bash
bash src/ops/remote_3090_overconfidence_ablation.sh
bash src/ops/remote_3090_overconfidence_ablation_summarize.sh
```

预计计算量：约 60 个 fold/seed run，4x3090 约 1.5 小时。

---

## A4. External X-ray-Only Validation - 回应 F1 的最低可行外部验证

### 目的

F1 的最低可行修复是：冻结 BIMCV 上训练好的 X-ray student，不重新训练，直接在独立外部 X-ray cohort 上推理。这样可以证明 deployed X-ray model 在 domain shift 下的绝对表现。

### 外部数据

优先顺序：

1. MIDRC X-ray manifest，使用 repo 现有 `prepare_midrc_dataset.py`。
2. 另一个公开 COVID CXR 数据集，使用现有 `download_noncovid_datasets.py` / `prepare_covid_dataset.py` 相关脚手架。
3. 若存在同患者 CT-X-ray 外部数据，则升级为 B1。

### 实施

1. 构建外部 patient-level manifest。
2. 对 supervised X-ray baseline 和已通过 gate 的 JDCNet student 做 frozen inference。
3. 报告每个外部 cohort 上的 BA、ROC-AUC、macro-F1、sensitivity、specificity 和 bootstrap CI。
4. 主文新增 External Validation 小节。

### 远端 3090 执行

```bash
bash src/tmp_sync/ssh3090.sh 'cd /data/JDCNET/src && python3 -m jdcnet_exp.prepare_midrc_dataset \
  --out /data1/external/midrc'

bash src/ops/remote_3090_external_eval.sh
bash src/ops/remote_3090_external_eval_summarize.sh
```

预计计算量：只做推理，单 GPU 通常小于 30 分钟。

---

## B1. External Paired-Cohort Gate - 回应 F1 的最强版本

### 目的

如果能拿到外部 same-patient paired CT-X-ray cohort，则可完整复现 JDCNet transfer claim：CT teacher -> confidence gate -> X-ray student -> matched baseline comparison。这是对 F1 最有力的反驳。

### 候选来源

- BIMCV-COVID19 negative paired release:
  - `download_bimcv_neg_paired.py`
  - `prepare_bimcv_neg_dataset.py`
- MIDRC 中同时存在 CT 和 CXR 的 subject:
  - `prepare_midrc_teacher_variants.py`
  - `prepare_mixed_bimcv_midrc_cv.py`

### 执行

复刻主实验 16-cell grid，5-fold patient-level CV，seeds 42-44。若外部 paired cohort 可用，则 B1 应成为 F1 的 headline rebuttal。

预计计算量：约 240 个 fold/seed run，4x3090 约 6 小时。

当前状态：数据可行性待确认。若无法组装真正的 same-patient paired cohort，则使用 A4 + B2 回应 F1。

---

## B2. Cross-Source Transfer Matrix - 量化 F1 的泛化落差

### 目的

将跨域泛化从“没有证明”改为“明确量化”。构建 train/test source matrix，报告 same-source 与 cross-source 的绝对性能和下降幅度。

### 设计

| Train | Test | Model |
|---|---|---|
| BIMCV | BIMCV | supervised baseline / JDCNet |
| BIMCV | external | supervised baseline / JDCNet |
| external | external | supervised baseline, if labels enough |
| external | BIMCV | optional |

### 远端 3090 执行

```bash
bash src/ops/remote_3090_cross_source_matrix.sh
bash src/ops/remote_3090_cross_source_matrix_summarize.sh
```

预计计算量：约 30 个 run，4x3090 约 1.5 小时。

---

## B3. Calibrated-Quantile Gate Sweep - F3 稳健性补充

### 目的

证明 calibrated gate 不是某个固定阈值 `tau` 的偶然结果。将固定阈值换成校准置信度分位数 gate，例如保留 top 50%, 60%, 70%, 80% 的 pseudo-label。

### 设计

```text
q in {0.5, 0.6, 0.7, 0.8}
mask = calibrated_confidence >= quantile(calibrated_confidence, 1 - q)
```

报告 Delta BA 是否保持正向、CI 是否稳定、coverage 与 error rate 是否平滑变化。

预计计算量：约 90 个 fold/seed run，4x3090 约 2.5 小时。

---

## 推荐执行顺序

| 顺序 | 任务 | 回应 | 是否依赖 3090 | 备注 |
|---:|---|---|---|---|
| 1 | A1 绝对指标汇总 | F2 | 否 | 立即可做 |
| 2 | 修复 3090 网络 | infra | 是 | 当前 `No route to host` 阻塞 GPU |
| 3 | A2 Calibrate-then-gate | F3 | 是 | 主要方法改进 |
| 4 | A3 Overconfidence ablation | F3 | 是 | 直接回应 reviewer 风险 |
| 5 | A4 外部 X-ray-only 推理 | F1 | 是 | 最低可行外部验证 |
| 6 | B2 Cross-source matrix | F1 | 是 | 量化泛化落差 |
| 7 | B3 Quantile gate sweep | F3 | 是 | 稳健性 |
| 8 | B1 外部 paired gate | F1 | 是 | 数据可得时做 |

最低可投稿组合：A1 + A2 + A3 + A4。更强版本：再加入 B2；最强版本：B1 成功。

---

## 论文整合计划

1. Abstract:
   - 增加 baseline 和 JDCNet 的绝对 BA/AUC。
   - 增加外部 cohort 的绝对指标。
   - 不再只写相对提升。
2. Methods:
   - 新增 `Calibration Safeguard` 小节。
   - 写清 temperature scaling、calibration split、calibrated confidence gate。
3. Experiments:
   - 新增 absolute metrics table。
   - 新增 external validation section。
   - 新增 calibration / overconfidence ablation table。
4. Limitations:
   - 若无外部 paired cohort，明确说明 full CT-Xray transfer replication 仍受 paired data 可得性限制。
5. Cover letter:
   - 按 F1/F2/F3 逐条回应。

---

## Stop Conditions

- Best case: B1 外部 paired gate 通过，论文可主张 transfer mechanism 跨 cohort 复现。
- Expected case: A4 + B2 完成，论文可主张 deployed X-ray student 在外部域上经过绝对指标验证，且泛化落差已量化。
- Floor: 若外部 paired data 不可得，至少完成 A1-A4；F1 以 X-ray-only external validation 和 limitations 中的 paired-data 约束回应。

最后更新：2026-06-16。
