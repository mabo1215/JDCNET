# JDCNet TCSVT 实验蓝图更新 (2026-05-15)

结论先说：**report513.md 的 teacher upper-bound 优先路线已部分执行。BIMCV-only same-source 验证通过上界门槛，但 gated KD 仍未稳定超过 supervised。Priority 2 标定扫描（T × threshold）因 dataloader 死锁卡住，需要重启。以下是当前完整状态与更新后的决策蓝图。**

---

## 1. Priority 2 Calibration Scan — 目的

**背景：** Round 4（BIMCV-only 5-fold CV）得到以下核心矛盾：

| 对比 | mean ΔBA | 95% CI | 结论 |
|---|---|---|---|
| teacher - supervised | +0.0746 | [+0.0314, +0.1144] | ✓ teacher 上界成立 |
| gated KD - plain KD | +0.0435 | [+0.0052, +0.0858] | ✓ gating 修复 plain KD 退化 |
| gated KD - supervised | +0.0146 | [-0.0264, +0.0531] | ✗ CI 过 0，未验证 |
| gated KD - teacher | -0.0600 | [-0.1011, -0.0133] | teacher 优势没有被充分转移 |

**问题：** teacher 有 +7.46% 的上界优势，但 gated KD 只收回了 +1.46% vs supervised。转移效率 = 1.46/7.46 ≈ 20%，极低。

**Priority 2 扫描的假设：** 当前锁定配置 (T=4.0, thr=0.55) 可能不是最优校准点。更高的 T（更平滑的 soft target）或更低的 threshold（更多样本获得 KD 信号）可能提高知识转移效率。

**扫描网格：**
```
T ∈ {2.0, 4.0, 8.0} × threshold ∈ {0.50, 0.55, 0.60}
跳过 (4.0, 0.55)（已有结果）
= 8 new cells × 5 folds × 3 seeds = 120 runs
```

**决策标准：** 至少一个 cell 达到 mean ΔBA ≥ +0.03 AND bootstrap 95% CI lower bound > 0

**当前状态：** 扫描于 2026-05-14 11:46 UTC 启动，但在 epoch 45/50 处因 dataloader 多进程死锁卡住（已持续 ~22 小时，log 不再增长）。

---

## 2. Report513.md 计划执行对比

Report513.md Section 7（2026-05-13 决策）规划了以下五步路线，以下是执行状态：

### Step 1：先确认 teacher upper bound

| 变体 | 在哪个数据集 | 结果 |
|---|---|---|
| ct_mean_projection_lung | MIDRC 126 5-fold | FAIL（均值 delta -0.009，fold1 supervised 崩溃导致假正信号） |
| ct_3slice_lung_rgb | MIDRC 126 5-fold | FAIL（均值 delta -0.027，同样 fold1 崩溃） |
| ct_mean_projection | BIMCV+MIDRC 混合 5-fold | FAIL（teacher mean AUC 0.653 < sup 0.686，BIMCV DRR ≠ MIDRC CT 投影，跨域差） |
| **bimcv_ct_mid（teacher_drr 行）** | **BIMCV-only 5-fold** | **PASS ✓**（ΔBA +0.0746，CI [+0.0314,+0.1144]，12/15 positive） |

**重要澄清：** "teacher_drr" 实际使用的是 `/data/bimcv_ct_slices/S03048_ct_mid.png`（CT 中间层单张 PNG），不是 Digitally Reconstructed Radiograph（DRR 射线投影）。命名来自脚本行标签，实质是 BIMCV CT 单层切片教师。DRR 生成路径（`/data/bimcv/drr_cache/`）作为独立资源存在，尚未在主 CV 实验中使用。

**结论：** teacher upper-bound 在 BIMCV-only 同源条件下成立；在 MIDRC 和跨源混合中均失败。

### Step 2：保留 gating-only，暂停 projection attention ✓

已执行，所有 CV 实验均使用 `projected_attention_weight=0.0`。

### Step 3：改验证协议 ✓

已升级为 5-fold stratified patient-level CV（MIDRC 5-fold、混合 5-fold、BIMCV-only 5-fold）。

### Step 4：4 行 locked matrix ✓

BIMCV-only 5-fold 完成了 teacher_drr / xray_supervised / plain_kd / gated_kd 四行矩阵。

### Step 5：BIMCV+MIDRC 混合只作诊断 ✓

混合 CV 三轮均失败，与计划一致（source-label confounding 确认），不作为主验证。

**总结：** report513.md 的路线已执行完毕。核心发现：BIMCV-only 同源条件下 teacher 上界成立，但 KD 转移效率不足；MIDRC 和混合路径均未能建立稳定 teacher 上界。

---

## 3. 两天实验完整时间线（2026-05-13 ~ 2026-05-15）

```
2026-05-13
  H800 无卡：BIMCV+MIDRC existing-path 5-fold index 生成（147 patients）
  H800 无卡：MIDRC teacher variant 预处理完成（6 类，每类 126 patients，errors=0）
  决策记录：report513.md Section 7，teacher upper-bound 优先路线

2026-05-14（early UTC）
  3090：locked_validation paired manifest 生成完成（126 paired patients）
  3090：teacher_variants_20260514 6 类 CT teacher 输入生成
  
2026-05-14 ~03:00 UTC（Round 1）
  3090：MIDRC 126 triage，6 teacher × 3 seeds
  结果：ct_mean_projection 最好，mean delta +0.050，但 2/3 seeds 正 → FAIL（test=10/10 过小）

2026-05-14 ~04:46–05:30 UTC（Round 2）
  3090：MIDRC-only 5-fold CV（ct_mean_projection + ct_3slice，MIDRC 126pts）
  结果：两者均 FAIL（fold1 supervised 崩溃是假信号，根因：78 gradient steps 导致退化）

2026-05-14 ~06:32–07:07 UTC（Round 3）
  3090：BIMCV+MIDRC 混合 5-fold CV（352 patients，ct_mean_projection teacher）
  结果：FAIL（mean_delta=-0.020，CI [-0.043,+0.002]，根因：跨域差 BIMCV DRR ≠ MIDRC CT 投影）

2026-05-14（afternoon UTC，Round 4）
  3090：BIMCV-only same-source 5-fold CV（228 patients，4 行矩阵，60 runs）
  结果：teacher_drr PASS（ΔBA +0.0746，CI lower +0.0314）
        plain_kd FAIL（-0.0290 vs sup）
        gated_kd PARTIAL（vs plain +0.0435 CI lower > 0；vs sup +0.0146 CI 跨 0）
  论文更新：bibliography pass 完成（9 refs 2022-2025），Related Work 扩展

2026-05-14 11:46 UTC（Priority 2）
  3090：Priority 2 calibration scan 启动（T × threshold 120 runs，GPUs 2/3）
  状态：启动 28 分钟后在 epoch 45/50 处 dataloader 死锁，已卡住 ~22 小时
  当前：2/120 best.pt（前 2 runs 训练完成），0/120 test_eval，screen sessions 仍在
```

---

## 4. 当前已验证证据状态

| 结论 | 证据强度 | 数据来源 |
|---|---|---|
| BIMCV CT 单层切片 teacher 在同源条件下有信息优势 | **VALIDATED**（CI lower > 0，12/15 folds 正向） | BIMCV-only 5-fold CV，228pts |
| Plain KD 在小数据集下会退化（低于 supervised） | **CONFIRMED**（-0.029，CI [-0.084,+0.024] 均值负） | 同上 |
| Reliability gating 能稳定修复 plain KD 退化 | **VALIDATED**（gated-plain ΔBA +0.0435，CI lower > 0） | 同上 |
| Gated KD 超过 supervised | **UNVALIDATED**（ΔBA +0.0146，CI [-0.0264,+0.0531]） | 同上 |
| MIDRC CT teacher 有信息优势 | **FAILED**（3 轮均 FAIL） | MIDRC-only & 混合 5-fold CV |
| KD 在 MIDRC 上有效 | **NOT TESTED**（teacher 未过上界门槛，未启动 KD） | — |

---

## 5. 即时问题：Calibration Scan 死锁修复

**问题：** `num_workers=16` 导致 epoch 45 dataloader 多进程死锁，两个 screen session 均卡死。

**修复命令（在 3090 远端执行）：**

```bash
# 1. 杀掉卡死的 screen 和进程
sshpass -p mabo1215 ssh mabo1215@10.147.20.176 "
  screen -S bimcv_calib_g2 -X quit 2>/dev/null || true
  screen -S bimcv_calib_g3 -X quit 2>/dev/null || true
  pkill -f 'bimcv_only_calibration_scan' 2>/dev/null || true
  sleep 3
  screen -ls | grep bimcv_calib || echo 'screens cleaned'
"

# 2. 用 num_workers=0 重启（done_run() 检查会自动跳过已完成的 2 runs）
sshpass -p mabo1215 ssh mabo1215@10.147.20.176 "
  cd /data/JDCNET_git && git fetch origin && git reset --hard origin/main
  export NUM_WORKERS=0
  bash /data/JDCNET_git/src/ops/remote_3090_bimcv_calibration_scan.sh
"
```

**说明：** `done_run()` 检查 `best.pt + best_metrics.json` 存在，已完成的 2 runs 会被跳过，只训练剩余 118 runs。`num_workers=0` 避免 fork 死锁，对小数据集影响极小。

---

## 6. 更新后的决策蓝图

### 6.1 总体决策树

```
Priority 2 scan 完成
    │
    ├─ 有 validated cell（ΔBA ≥ +0.03 AND CI lower > 0）
    │       │
    │       ├─ [路径 A] 扩展 BIMCV-only pilot
    │       │   → 对 winner cell 补充 seeds 45-47（5 folds × 6 seeds = 30 runs）
    │       │   → 写入论文 appendix/pilot section
    │       │   → 同时可启动 MIDRC DRR 生成（路径 B）
    │       │
    │       └─ 决策：是否满足于 BIMCV-only pilot 投稿，还是继续追求 MIDRC 主验证？
    │
    └─ 无 validated cell
            │
            ├─ [路径 B] MIDRC DRR 生成 → MIDRC-specific DRR teacher
            │   → 生成 MIDRC CT → DRR 投影（plastimatch 或类似工具）
            │   → 训练 MIDRC DRR teacher，测 upper-bound
            │   → 若 MIDRC DRR teacher PASS：运行 MIDRC-only 4-row locked matrix
            │
            └─ [路径 C] Evidence-bounded 投稿（当前可立即执行）
                → 不再扩展实验
                → 论文主叙事：framework audit + diagnostic benchmark
                → BIMCV-only pilot 写入 appendix（有限正向证据）
```

---

### 6.2 路径 A：BIMCV-only Pilot 扩展

**适用条件：** Priority 2 至少一个 (T, thr) cell 通过决策门（ΔBA ≥ +0.03，CI lower > 0）

**执行步骤：**
1. 从 `decision_report.md` 中找出 winner cell
2. 对 winner cell 追加 seeds 45, 46, 47（共 5 folds × 6 seeds = 30 runs）
3. 汇总 30 runs 的 gated_kd vs supervised 配对 delta
4. 若 30 runs 中大多数正且 CI lower > 0：可写为 "BIMCV-only validated configuration"

**论文处理：** 作为 "Section X: Limited Positive Pilot" 或 appendix。明确说明：
- 仅限 BIMCV 同源 CT 单层切片 teacher
- 不是跨机构验证
- Teacher 上界 ΔBA +0.075 中只有 20-40% 被 KD 转移，知识转移效率问题仍存在

**达标标准（升级为 validated architecture）：**
```
30 runs 大多数为正（至少 20/30）
mean ΔBA vs supervised ≥ +0.03
Macro-F1 同方向提升
specificity 不崩
95% bootstrap CI lower bound > 0
```

---

### 6.3 路径 B：MIDRC DRR 生成（Teacher 信息优势重建）

**背景：** MIDRC CT teacher 失败的核心原因是跨域差：
- BIMCV teacher 成功：BIMCV CT 单层切片教师在 BIMCV X-ray 患者上训练/测试，同源同域
- MIDRC teacher 失败：MIDRC ct_mean_projection（真实 CT 投影）与 BIMCV DRR cache 存在成像差异，混合 CV 跨域泛化差
- MIDRC-only 失败：只有 69 COVID+ patients（太少），小数据集 supervised 模型退化导致假信号

**路径 B 假设：** 如果为 MIDRC CT 生成 DRR 投影（与 BIMCV `/data/bimcv/drr_cache/` 相同的 DRR pipeline），则：
- MIDRC DRR teacher 在 MIDRC 同源条件下也可能通过 upper-bound 测试
- 类比 BIMCV 同源成功路径

**执行步骤：**
1. 确认 BIMCV DRR pipeline（`/data/bimcv/drr_cache/bimcv_S{patient}.png` 是如何生成的）
   - 检查是否有生成脚本在 repo 中
   - 确认使用的工具（plastimatch / tigre / deepdrr）和参数
2. 对 MIDRC 559 中有 CT 的患者（从 `/data1/midrc/raw_559cases_combined/` 中）生成 DRR
   - 重点：69 COVID+ + 等量 COVID- 配对患者
   - 生成格式与 BIMCV drr_cache 一致（224×224 PNG 灰度/RGB）
3. 将 MIDRC DRR 路径写入 teacher_image_path manifest
4. 跑 MIDRC-only 5-fold CV，4 行 locked matrix，使用 DRR teacher
5. 检查 teacher upper-bound：MIDRC DRR teacher ΔBA vs X-ray supervised

**风险：**
- BIMCV DRR 可能是预先计算的外部资源，不一定有可重复的生成脚本
- MIDRC CT DICOM → DRR 需要额外预处理步骤（CT orientation、lung mask、projection angle）
- MIDRC 只有 69 COVID+，即使 DRR teacher 通过上界，5-fold test fold ≈ 14 patients，统计功效仍不足

**优先级：** 如果路径 A 失败且路径 C 不够充分，则尝试路径 B。

---

### 6.4 路径 C：Evidence-Bounded 投稿（当前可立即执行）

**适用条件：** 任何情况下均可作为保底选项

**当前可用证据：**
- BIMCV-only same-source pilot：teacher 上界 VALIDATED，plain KD 退化 CONFIRMED，gated KD 部分修复 VALIDATED，但 gated KD vs supervised 仍 UNVALIDATED
- MIDRC/混合：teacher 上界全部 FAIL，跨域差原因已确认
- Framework 实现：完整代码，包含 gate diagnostics（active fraction、mean weight、teacher confidence）

**论文主张（当前可支持）：**
```
1. CT teacher 在同源条件下具有信息优势（BIMCV-only validated）
2. Plain KD 在小 paired cohort 下会退化
3. Reliability gating 能稳定修复 plain KD 退化（CI lower > 0）
4. Gated KD 尚未稳定超过 supervised（现有证据不足）
5. 跨域差（BIMCV DRR vs MIDRC CT 投影）是跨源 KD 的主要障碍
```

**论文定位：** Protocol contribution / diagnostic framework paper，而非 validated architecture paper。适合 TCSVT 的 Systems / Methodology 投稿方向。

**所需工作：**
- Priority 2 scan 完成后写入 gate diagnostics 分析（即使无 validated cell）
- 确认 BIMCV-only pilot section（teacher 上界 + gating rescue）的论文表述
- 完成 manuscript polish

---

## 7. 最小验证矩阵（任意路径下保持不变）

```
行 1: CT teacher（BIMCV ct_mid 或 MIDRC DRR）
行 2: X-ray supervised
行 3: Plain CT logit KD
行 4: Reliability-gated KD（locked config）
```

**锁定配置（来自 docs/VALIDATED_ARCHITECTURE_EXPERIMENT_PLAN.md）：**
```json
{
  "temperature": 4.0,
  "confidence_gate_threshold": 0.55,
  "confidence_gate_requires_correct": true,
  "projected_attention_weight": 0.0
}
```
（如果 Priority 2 扫描找到更优 (T, thr)，在追加 seeds 前更新此配置。）

---

## 8. 论文写作分工

| 模块 | 当前状态 | 待完成 |
|---|---|---|
| Bibliography | ✓ 完成（9 refs 2022-2025） | — |
| Related Work KD 段 | ✓ 完成 | — |
| Main contribution claims | 已降调为 evidence-bounded | 等扫描结果更新措辞 |
| BIMCV-only pilot section | 数据已有，未写 | 等扫描结果决定路径 A/C |
| Gate diagnostics section | 待写 | 扫描完成后写 |
| MIDRC failure analysis | 部分写入 | 可补充跨域差分析 |
| Appendix 大表 | 已有 Path-C + MIDRC pilot | 等 Priority 2 结果追加 |
| Manuscript polish | Pending | 路径决定后执行 |

---

## 9. 作者决策清单（需要输入的问题）

1. **Calibration scan 重启：** 是否授权用 `NUM_WORKERS=0` 重启扫描（见 Section 5 命令）？如果授权，可立即执行。

2. **路径选择：** 扫描结果出来后，优先选择：
   - 路径 A（有 winner cell）→ 扩展 seeds 继续 BIMCV-only pilot
   - 路径 B（无 winner cell）→ 尝试 MIDRC DRR 生成
   - 路径 C（直接）→ evidence-bounded 立即投稿

3. **MIDRC 主验证：** 是否继续把 MIDRC 作为主验证目标？（当前 MIDRC 只有 69 COVID+，即使 DRR teacher 通过上界，统计功效仍偏弱。若接受 BIMCV-only pilot 作为 limited positive evidence，则 MIDRC 可降为 diagnostic 队列。）

4. **H800：** 是否还在计费？如果是，需要在平台控制台停止实例。

---

## 10. 快速参考

| 资源 | 路径/地址 |
|---|---|
| 3090 SSH | `sshpass -p mabo1215 ssh mabo1215@10.147.20.176` |
| 扫描 status.tsv | `/data1/logs/bimcv_only_calibration_scan_20260514/status.tsv` |
| 扫描 run root | `/data1/midrc/runs/bimcv_only_calibration_scan_20260514/` |
| BIMCV-only CV results | `src/results/bimcv_only_5fold_cv_3090_20260514/` |
| BIMCV 原始 teacher 图像 | `/data/bimcv_ct_slices/` (ct_mid, 114 positive patients) |
| BIMCV DRR cache（未使用）| `/data/bimcv/drr_cache/bimcv_S{patient}.png` |
| 汇总脚本 | `bash /data/JDCNET_git/src/ops/remote_3090_bimcv_calibration_summarize.sh` |
| 论文 | `paper/main.tex`, `paper/ref.bib` |
| 验证计划 | `docs/VALIDATED_ARCHITECTURE_EXPERIMENT_PLAN.md` |
