# TCSVT 审稿修改计划 (2026-05-15)

> **审稿结论**: Reject in the current form, but encourage substantially revised resubmission.
> **审稿原文**: `docs/revision_suggestions.tex`
>
> 审稿覆盖 12 项 Major + 12 项 minor，共 12 项 Required Revision Checklist (R1-R12)。
> 本计划记录：(A) 本次会话已完成的立即修改；(B) 需后续会话完成的重构；(C) 需新实验的项目。

---

## A. 本次会话已完成的修改 (Path A: 立即可改文本)

| ID | Action | 文件 | 状态 |
|---|---|---|---|
| R2/M3 | Abstract 缩短到 ~195 词，删 DPE/MHRA/DFPN/DRR/Path-C 等术语，使用审稿建议版本 | `paper/main.tex` | ✓ 完成 |
| R4/M12 | Conclusion 首段改为 sharper 版本（审稿建议原话） | `paper/main.tex` | ✓ 完成 |
| R4 | Contributions §2 已扩展为完整实验范围 + confound 穷尽框架 | `paper/main.tex` | ✓ 完成 (上一会话) |
| M6 | 在 Primary Same-Case Evidence 节末尾添加 Statistical caveat（重采样相关性 + 多重比较） | `paper/main.tex` | ✓ 完成 |
| m2 | 标题改为 "When Does CT-to-X-ray Distillation Help? An Evidence-Bounded Visual-Systems Audit under Paired-Cohort Constraints" | `paper/main.tex` | ✓ 完成 |
| m3 | "Full JDCNet" 在 Notation 节已明确标记为 "the legacy name for the module-augmented test variant" | `paper/main.tex` | ✓ 已存在 |
| m6 | artefact → artifact 全文统一（IEEE 美式拼写） | both | ✓ 完成 |
| m7 | "Gui Lin" → "Guilin" affiliation typo | `paper/main.tex` | ✓ 完成 |
| Limitations | DRR + 校准扫描 + 同源 5-fold 闭环已写入 Limitations Method/Evaluation 段 | `paper/main.tex` | ✓ 完成 (上一会话) |

---

## B. 需后续会话完成的重构 (Path B: 大改但无新实验)

### B1. 页数压缩到 12-14 页 (R1, M1) — 最 critical 工作

**当前**: ~31 页 (主稿约 14 页 + appendix ~17 页)
**目标**: 主稿 12-14 页，appendix 移至 supplementary material

**操作步骤**:
1. 将 appendix.tex 拆为两个文件：
   - `paper/main.tex` 保留：Reproducibility Statement、Limitations、Conclusion 必需的最小 ref
   - `paper/supplementary.tex` (新建): 现 appendix 的全部内容
2. 删除主稿冗余（这些子节其内容可合入 main 段落）：
   - Discussion Preview (line 160-178) - 与 Introduction、Contributions 重复
   - Hypothesis Status Table (Tab 2) - 可压缩为正文 1 段
   - 多个并存的 evaluation regime 表格 - 合并为 1 个
3. 主稿表格目标：≤ 6 个表格 (现 ~12 个)
4. 主稿图目标：≤ 5 个图 (现 ~6 个)

**预计工时**: 4-6 小时 (大量精细编辑)

### B2. TCSVT systems framing 强化 (R3, M2, M11)

**问题**: 现写法过偏 medical AI evaluation；TCSVT 期待 visual systems / efficient deployment 角度

**操作步骤**:
1. Introduction 增加 1 段：明确将 problem 定义为 **"training-only privileged modality learning for efficient visual deployment"**
2. Introduction Motivation 段：突出 X-ray-only inference 的 latency / model size / deployment constraint 价值
3. 将现 "Deployment-Time Efficiency" 子节（line 453）从 Reproducibility 旁边移到 Experiments 主线靠前位置
4. Related Work 增补 TCSVT 相关引用：
   - efficient visual recognition (MobileNet, ShuffleNet 系)
   - cross-modal visual learning beyond medical (Action recognition, video understanding)
   - multimodal compression / distillation for video
5. Conclusion 强调：cost-benefit trade-off (modules 增 6× 参数无 BA 增益)

**预计工时**: 3-4 小时

### B3. 统计处理改进 (R7, M6)

**问题**: 重采样不独立；某些 p-value 看起来比实际更精确

**操作步骤**:
1. 在 Methods 节添加 "Statistical Protocol" 子节：
   - 主端点 pre-specified: plain KD vs supervised
   - 所有其他比较为 post-hoc，不做 family-wise correction
   - bootstrap 使用 patient-level resampling (现已部分实现)
2. 将所有 post-hoc Wilcoxon 表格添加 "Exploratory" 标记
3. 同时报告 effect size (Cliff's δ 或 Cohen's d) + win/loss counts

**预计工时**: 2 小时

### B4. Baseline 简化和强化 (R8, M8)

**操作步骤**:
1. 删除主稿中 generic KD baselines (CRD, DKD, DIST, MH) 详细数字 - 保留为 "all collapse, see supplementary"
2. 主稿 baseline 表只保留：student-only, late fusion, same-modality KD, plain logit KD, attention transfer, module-augmented variant
3. 添加一行：BiomedCLIP fine-tuned (currently only frozen-feature, see C2 below for new run)

**预计工时**: 1 小时 (前提是 C2 实验已完成)

### B5. 表格/图可读性 (R11)

1. 表格大字段缩写化，使用 macro 减小行高
2. 图字号 ≥ 8pt
3. 主表使用 booktabs 三横线规范

**预计工时**: 1-2 小时

### B6. 引用格式审查 (R12, m8)

1. 全部 arXiv 条目检查是否已发表（很多 2022-2024 paper 现在有期刊/会议版本）
2. 添加 DOI
3. 增补 TCSVT 相关引用

**预计工时**: 1 小时 (脚本辅助)

---

## C. 需新实验的项目 (Path C: 实验+写作)

### C1. Multi-slice/volume CT teacher (R8, M9) — **优先级: HIGH**

**审稿原话** (M9): "If CT is claimed to be a richer teacher modality, the teacher should exploit CT more meaningfully... Add or emphasize multi-slice/volume teacher experiments."

**实验设计**:
- 在 BIMCV-only balanced 5-fold CV 同样设置上，对比 4 种 CT teacher 表征:
  1. mid-slice (现有 baseline)
  2. 3-slice central stack (上中下三切片，concatenate channels 或 voxel-wise mean)
  3. multi-slice projection (axial 平均投影 / lung mask 加权投影)
  4. DRR (现有 pilot)
- 每种 ×4 rows × 5 folds × 3 seeds = 60 runs/teacher × 4 teachers = 240 runs
- 同 calibration scan 框架，可在 3090 上 ~2-3 小时完成

**资源需求**: 3090 4 卡 ~3 小时；需准备 multi-slice CT cache (~30 GB on /data1)

**写作产出**:
- 新增 1 个 appendix 表 (4 teacher × method comparison)
- 主稿 1 段讨论：CT 表征丰富度 vs KD 收益的关系
- **预期结果**: 极大可能仍 FAIL，但能直接回应 M9 的"CT under-specified"质疑

**风险**: 即使 multi-slice 也很可能在 BIMCV 160 样本规模下卡在同样的统计功效瓶颈

### C2. BiomedCLIP fine-tuning baseline (R8, M8) — **优先级: HIGH**

**审稿原话**: "Consider foundation-model baselines with fine-tuning, not only frozen linear probing."

**实验设计**:
- BiomedCLIP visual encoder + 二分类 head, fine-tune 全部参数
- 在 BIMCV-only balanced 5-fold CV 上跑 3 seeds × 5 folds = 15 runs
- 与现有 ResNet18 supervised + plain logit KD + gated KD 对比

**资源需求**: 3090 1 卡 ~1 小时 (BiomedCLIP ViT-B 较大)

**写作产出**:
- 主稿 baseline 表新增 1 行
- 强化"foundation model 不是银弹"的论点 (assuming it doesn't dominate)
- **预期结果**: BiomedCLIP fine-tuned 可能略优于 ResNet18 supervised 但不会 dominate KD 结果

### C3. Edge-device latency measurement (R10, M11) — **优先级: MEDIUM**

**审稿原话**: "If possible, include an edge-device or embedded-platform measurement, which would strengthen the TCSVT systems fit."

**实验设计**:
- 在 Jetson Nano / Raspberry Pi 4 / 类似 ARM 平台上实测 student inference latency
- 报告：CPU latency (Cortex-A76 等), memory footprint, throughput (images/sec)

**资源需求**: 需要物理设备 OR 通过 ONNX export + emulator 间接测量

**写作产出**:
- Deployment Efficiency 表新增 edge-device 列
- 强化 TCSVT systems contribution

**当前不可行性**: 需要硬件，本地无；可考虑 AWS Graviton 实例或省略

### C4. 外部独立配对队列验证 (M5, M10) — **优先级: LOW (不可行)**

**审稿原话**: "If possible, add an external same-patient paired validation cohort with adequate negative support."

**判断**: 公开数据集中没有现成的同患者 CT-X-ray 配对队列符合此要求；需要新数据采集，超出本投稿范围。**只在 Limitations 中明确说明**。

---

## 修改优先级建议

```
critical (resubmit 前必做):
  - B1 (页数压缩) — 不做无法投稿
  - B2 (TCSVT framing) — 不做几乎确定 desk reject
  - A 部分已完成 ✓

high (强化 resubmit 成功率):
  - C1 (multi-slice CT teacher) — 直接回应 M9
  - C2 (BiomedCLIP fine-tune) — 直接回应 R8/M8
  - B3 (统计处理) — 回应 M6/R7

medium:
  - B4 (baseline 简化)
  - B5 (表格图)
  - B6 (引用格式)

low / 不可行:
  - C3 (edge device) — 硬件依赖
  - C4 (外部队列) — 数据获取问题
```

## 时间估算

- A 部分: 已完成
- B1+B2+B3 (重构主线): 10-12 小时纯写作
- C1+C2 (新实验): 4-5 小时实验 + 2 小时写作
- B4+B5+B6 (打磨): 4 小时

**总计**: 约 20-25 小时分散到 3-4 次后续会话

## 文件位置

| 资源 | 路径 |
|---|---|
| 审稿原文 | `docs/revision_suggestions.tex` |
| 本计划 | `docs/tmp/report517.md` |
| 当前论文主稿 | `paper/main.tex` |
| 当前论文 appendix | `paper/appendix.tex` |
| Path B 决策记录 | `docs/tmp/drr_cv_decision_report.md` |
| 项目 memory | `~/.claude/projects/-mnt-c-source-JDCNET/memory/project_jdcnet.md` |

## 决策记录

- **不接受 reviewer 关于"重新做架构"的暗示** (M4 中 "If authors want to keep JDCNet... must provide a revised architecture"): 已通过 evidence-bounded framing + DRR 实验 30 cells 闭环证明在当前数据规模下任何架构都无法验证。继续追求架构改进将重蹈覆辙。
- **保留 negative-result audit 作为核心贡献**: 这是审稿人也认可的强项 ("unusually honest and reproducible, and its negative-result framing is scientifically useful")。
- **TCSVT scope 的 fit 是真问题**: 需要强化 visual-systems framing (B2) 才能 survive desk review。
