# C1 + C2 实验综合分析 (2026-05-16)

> **目的**: 分析 Codex 跑完的 C1 (4 CT teacher variants × 240 runs) 和 C2 (BiomedCLIP fine-tune × 15 runs)，给出对论文结论的影响和下一步建议。

---

## 1. C1 结果速览（Multi-slice / Volume CT Teacher Comparison）

### 1.1 4 种 teacher upper-bound（vs 同 fold-seed supervised）

| Teacher 表征 | Teacher BA | ΔBA vs sup | 95% CI | Pos / Neg | Pass? |
|---|---|---|---|---|---|
| **proj** (multi-slice projection) | **0.6760** | **+0.0449** | **[+0.008, +0.081]** | **9/5/1** | **✓ YES** |
| drr (geometric AP projection) | 0.6541 | +0.0231 | [-0.023, +0.066] | 9/0/6 | NO |
| 3slice (3-slice central stack) | 0.6503 | +0.0192 | [-0.013, +0.058] | 8/3/5 | NO |
| mid (single mid-slice, baseline) | 0.6425 | +0.0115 | [-0.024, +0.046] | 8/0/7 | NO |

**关键发现 1**: `proj` (沿 axial 平均投影) 是**唯一通过 validation gate 的 teacher upper-bound**。这是新的、强的、对审稿 M9 的直接回应。

### 1.2 4 种 KD（gated vs supervised）

| Teacher | Gated KD BA | ΔBA vs sup | 95% CI | Pass? |
|---|---|---|---|---|
| proj | 0.6163 | **−0.0148** | [-0.058, +0.027] | ✗ NO |
| drr | 0.6257 | -0.0053 | [-0.048, +0.039] | NO |
| mid | 0.6167 | -0.0144 | [-0.053, +0.023] | NO |
| 3slice | 0.5865 | **−0.0445** | [-0.092, +0.000] | NO |

**关键发现 2**: 即使 `proj` teacher 通过了 upper-bound gate（说明 CT 表征确实携带有用信息），**所有 4 种 KD 都没让 student 超过 supervised**。

### 1.3 Plain KD vs supervised（全部为负）

所有 4 种 teacher 的 plain logit KD 都 **DEGRADE** supervised baseline:
- proj: ΔBA = -0.031
- drr: ΔBA = -0.043
- mid: ΔBA = -0.022
- 3slice: ΔBA = -0.030

**关键发现 3**: Plain KD 不仅没有 transfer signal，反而损害 student，这与原 DRR pilot 一致。

### 1.4 C1 supervised baseline 上升的现象

C1 setup 下 supervised BA = **0.6311**（同 226 patients），明显高于早期 DRR pilot 的 **0.5657**（228 patients）。

可能解释：
- batch_size = 512 vs 256（虽然 160 训练样本下 effective batch 相同，但优化器动力学/AMP scale 可能不同）
- num_workers = 8 vs 1
- 同一支 patient pool 但精修排除了 2 个 patient

**这意味着**: 原 paper 报告的 DRR teacher_vs_supervised ΔBA = +0.075 是基于一个**偏弱的 supervised baseline**。在新的更强 supervised baseline 下，DRR teacher 优势缩到 +0.023（CI 跨 0）。

---

## 2. C2 结果速览（BiomedCLIP Fine-tune Baseline）

| 对比 | BiomedCLIP BA | Δ vs baseline | 95% CI | Pass? |
|---|---|---|---|---|
| vs C1 ResNet18 supervised (same 226) | 0.6333 | **+0.0022** | **[-0.048, +0.050]** | ✗ NO |
| vs 旧 DRR pilot supervised (228) | 0.6333 | +0.0675 | [+0.021, +0.112] | ✓ YES |

**关键发现 4**: BiomedCLIP fine-tune **基本和 ResNet18 supervised 持平**（+0.002，CI 跨 0）。所谓 "vs 旧 baseline 通过" 是 cohort 不同造成的 spurious win，不是真实的 foundation-model 优势。

**审稿 R8/M8 回答**: Foundation model fine-tune 不能为这个 task / data scale 提供超过 ResNet18 的收益。这是干净的负面结果，可以直接写进 supplementary。

---

## 3. 对论文当前论述的影响

### 3.1 加强（confirm 而非颠覆）的部分

1. **Negative-result thesis 更稳了**：4 种 teacher 表征 + 1 种 foundation backbone，**没有一个让 KD 通过 validation gate**。
2. **Cost-benefit framing (B2) 更稳了**：BiomedCLIP fine-tune（ViT-B/16）vs ResNet18（0.094M params）持平，foundation-model 部署成本完全不被 accuracy gain 偿付。
3. **数据规模瓶颈 thesis 更稳了**：换 4 种 teacher 表征、换 backbone，都打不破这个瓶颈。

### 3.2 需要更新的部分

1. **新的最佳 teacher upper-bound**：`proj` teacher (BA=0.676, ΔBA=+0.045, CI lo > 0) 通过 validation gate，**比 paper 当前引用的 DRR teacher 还强**。这是一个 cleanly positive 的 upper-bound 结果，应该写入 supplementary。

2. **Supervised baseline 数值矛盾**：
   - Paper Limitations § 现引用 "DRR pilot teacher_vs_supervised ΔBA = +0.065" 和 "gated KD ΔBA = +0.036 NEAR (seeds 42-44)" 
   - C1 同样 226 patients、同样 seeds 42-44 下，DRR teacher_vs_supervised 只有 +0.023（CI 跨 0），DRR gated_kd_vs_supervised 是 -0.005
   - 数值差异主要来自 batch_size + num_workers 改变后 supervised baseline 变强（0.566 → 0.631）
   - **需要在 paper 中说明这点**，避免 reviewer 发现两处数字打架

3. **审稿 M9 (CT representation under-specified) 现在有了直接答案**：proj teacher 通过、其他 3 种都失败，说明 CT representation 的选择对 teacher upper-bound 重要、但对 KD 转移效率不重要（因为 KD 全部失败）。

4. **审稿 R8/M8 (stronger baselines, foundation-model fine-tune) 有了直接答案**：BiomedCLIP fine-tune 持平 ResNet18，不能用 stronger backbone 拯救 cross-modal transfer。

### 3.3 应该写入论文的新内容

A) **Supplementary 新增 sec:ct_variants** (1 表):
   - 4 teachers × {teacher, supervised, plain_kd, gated_kd} × {BA mean, CI}
   - 1 句结论："Only the multi-slice projection teacher achieves a validated upper bound; no KD configuration closes the gap to supervised."

B) **Supplementary 现有 E3/E4 节扩展** (BiomedCLIP fine-tune):
   - 1 段 + 1 行表：BiomedCLIP fine-tune BA = 0.633，与 ResNet18 supervised 持平
   - 1 句结论："Foundation-model fine-tuning does not provide an inference-time advantage over the supervised ResNet18 baseline at the current paired-cohort scale."

C) **Main Limitations § 加 2 句**:
   - "We additionally tested four CT teacher representations (mid-slice, 3-slice stack, multi-slice projection, DRR) and a BiomedCLIP fine-tuned student under the same 5-fold protocol; the multi-slice projection teacher achieved a validated upper bound ($\Delta\text{BA}=+0.045$, CI~$[+0.008,+0.081]$), but no KD configuration and no foundation-model student exceeded the supervised ResNet18 baseline at the validation gate (Supplementary~\ref{sec:ct_variants})."

D) **Main Contributions §2 微调**:
   - 加入 "four CT teacher representations" 和 "a fine-tuned foundation-model student" 到 negative-boundary 清单

E) **Main Cost-benefit Conclusion 强化**:
   - 加 1 句: "Switching the student to a fine-tuned foundation-model backbone (ViT-B/16) does not shift this cost--accuracy frontier."

---

## 4. 关于 B4/B5/B6 的判断

### B4 Baseline 简化 — **建议 YES，与 C1+C2 整合一起做**

理由:
- C2 直接添加了 BiomedCLIP fine-tune 作为新 baseline，需要更新主稿 baseline 表格
- C1 4 个 teacher variants 形成了 cleaner teacher upper-bound 对比，可以替换主稿中对单一 DRR teacher 的依赖
- reviewer R8/M8 直接点名这个，做了能涨分

### B5 表图可读性 — **暂缓，B4 之后再看**

理由:
- B4 重组 baseline 表格后再做可读性优化更高效
- B5 是 polish，影响小

### B6 引用格式审查 — **暂缓**

理由:
- B6 是 mechanical 工作，临投稿前再 sweep 即可
- C1+C2 新增引用（如果未来要加新的 multi-slice CT 文献）应该一起处理

---

## 5. 建议的下一步顺序

1. **首先**: 把 C1+C2 结果写进 supplementary.tex（A 段 + B 段）+ main.tex Limitations §（C 段）。这是把已 commit 的实验数据兑现成 paper 的关键步骤。
2. **然后**: B4 baseline 简化，整合 BiomedCLIP 行 + 4-teacher 对比表。
3. **最后**: B5 + B6 一起做，准备 resubmit。

预计工作量：
- C1+C2 写入论文: 1.5-2 小时
- B4: 1 小时
- B5: 1-2 小时
- B6: 1 小时

总计: 4.5-6 小时，可以在 1-2 次 session 内完成。

---

## 6. 文件位置

| 类别 | 路径 |
|---|---|
| 本分析 | `docs/tmp/c1_c2_analysis.md` |
| C1 results | `src/results/bimcv_ct_variants_cv_3090_20260516/` |
| C2 results | `src/results/bimcv_biomedclip_cv_3090_20260516/` |
| C1 decision report | `src/results/bimcv_ct_variants_cv_3090_20260516/ct_variants_decision_report.md` |
| C2 decision report | `src/results/bimcv_biomedclip_cv_3090_20260516/biomedclip_decision_report.md` |
| DRR pilot results | `docs/tmp/drr_cv_decision_report.md` |
| C1+C2 task spec | `docs/tmp/report516.md` |
