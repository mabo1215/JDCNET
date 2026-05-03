# 进度日志

## 已全部修改

- 已消化 `## 遗留问题` 中关于 BIMCV paired cohort 的作者回答；`paper/main.tex` 与 `paper/appendix.tex` 已明确写入 BIMCV-COVID19+ 作为已准备好的下一队列资源。
- 已删除旧进度中"当前没有更大 paired cohort"的过期判断。
- 已在主文中修正数据与限制表述；BIMCV 不能直接并入当前 headline tables 已在多处说明。
- 已在附录中补充可复现边界；BIMCV 准备流程、限制均已写入。
- 已处理 stronger generic feature-alignment baseline 的遗留解释。
- **cross-source non-COVID control 决策已消化**：Limitations 明确"Any future cross-source non-COVID control must be reported explicitly as a category-level control, not as same-patient evidence."
- **目标期刊确认 IEEE TCSVT，IEEEtran 模板无需切换**：已消化作者答复，`USAGE.md` 已正确设置为 IEEE TCSVT，无需修改。
- **Abstract 重构（Minor 15）**：resampling 证据前置，fixed-split 降格为次级 screen，首定义 `\emph{same-case evaluation}`。
- **same-case evaluation 定义（Minor 22）**：Section 3.3 新增括号定义句。
- **DPE/MHRA/DFPN 作者自创缩写声明（Minor 5）**：Section 3.2 末段新增说明。
- **KL 方向说明（Minor 6）**：Equation 1 后补充 teacher-to-student 方向及梯度路径。
- **Equation 1 格式修复（Typog 3）**：重写为单行公式，消除 KL scope 歧义，使用统一 `\bigl/\Bigl` 括号。
- **CT 时间配对细节（Minor 18）**：无 offset 时使用唯一 CT、axial slice 选取方法。
- **CT 预处理说明（Minor 19）**：8-bit 灰度、bilinear resize、无均衡化。
- **AT/FH 实现细节（Minor 8）**：Section 4.2 新增 attention transfer 和 feature hint 描述段。
- **Table 4 late-fusion 标注（Minor 9）**：`\textdagger` caption 脚注 + table 行标注。
- **±0.000 解释（Minor 12）**：Table 4 caption + Section 4.4 说明 trivial collapse。
- **DPE 参数量说明（Minor 14）**：Section 4.5 解释 +DPE 不增加参数原因。
- **参考文献 arXiv → 发表版（Minor 24）**：`dosovitskiy` → ICLR 2021；`romero` → ICLR 2015。
- **新增参考文献（Minor 25）**：`lin2017fpn`、`tian2020contrastive`、`nie2018medical`、`liu2021swin`。
- **Related Work 扩展（Minor 1/25）**：新增 CRD、Nie TMI、FPN、Swin 引用及背景说明；解释为何不使用 ViT/Swin 骨架。
- **Figure 1 caption 排版修复（Typog 1）**：删除 tab 字符。
- **Limitations 压缩（Minor 23）**：从 ~1100 词压缩至 ~280 词，结构化三组要点。
- **标题优化（Minor 16）**：`CT-to-X-ray Distillation Under Tiny Paired Cohorts: An Evidence-Bounded Reproducible Pilot Study` → `CT-to-X-ray Knowledge Distillation Under Patient-Level Paired Cohorts: An Evidence-Bounded Evaluation Framework`；PDF metadata 同步更新；appendix title 同步。
- **TCSVT scope 段落（M6）**：Section 1.1 Motivation 开头新增 3 句 TCSVT scope justification，说明 cross-modal distillation 与 efficient visual computing 的关联。
- **Table 2 列标题修复（Typog 2）**：`Positives` → `COVID-Pos.`；`Negatives` → `COVID-Neg.`。
- **Manifest 独立性确认（Minor 20）**：Section 4.1 新增段，明确三套 manifest 患者集合完全不相交。
- **KD 缩写词表（Minor 11/Typog 6）**：Section 3.1 开头新增 5 个缩写定义（KD / Logit KD / Same-modality KD / Plain cross-modal KD / Full JDCNet）。
- **Appendix AUC 一致性说明（Minor 13）**：Table A2 caption 新增说明：固定 split 用 ROC-AUC，主文 resampling table 用 PR-AUC，并解释 seeds 42/43 结果相同不是复制粘贴错误。
- **Category-level cross-source non-COVID control 实验（M3 回应）**：下载 NORMAL CXR 1583 张 + normal CT 215 张；运行 `run_noncovid_controls.py`；结果 sensitivity=1.0、specificity 均值 0.00–0.32（distribution shift 确认）；附录新增 Table A3 + subsection；主文 Limitations "Data" 段引用 Table A3。同行评审 M3 以 category-level control + distribution shift 证据作为当前数据规模下的最终回应，更大 paired cohort 仍是下一轮实验前提。
- **标题再次重命名（2026-05-03）**：`CT-to-X-ray Knowledge Distillation Under Patient-Level Paired Cohorts: An Evidence-Bounded Evaluation Framework` → `JDCNet: Cross-Modal CT-to-X-ray Knowledge Distillation with Evidence-Bounded Evaluation on Patient-Level Paired Cohorts`；`paper/main.tex` `\title` 与 `\markboth` 同步；`docs/cover_letter.txt` 标题行同步。
- **Code Ocean capsule 公开（2026-05-03）**：`https://codeocean.com/capsule/6030764/tree`；`paper/appendix.tex` 新增 `A.1 Code and Data Availability` 子节（含 `\url{}` 渲染、capsule 内容描述）；`paper/main.tex` Contributions bullet 与 Implementation/Reproducibility 子节通过 `\ref{sec:code_availability}` 双向闭环；`docs/cover_letter.txt` Reproducibility artefact 段与 manuscript details `Code/data` 行同步 capsule URL；`paper/main.tex` 启用 `\usepackage{url}`、`paper/appendix.tex` standalone preamble 同步加入 `\usepackage{url}`。
- **实验侧追加（2026-05-03，回应 revision_suggestions.tex E5/E7/E8/E9/M1/M5/M9）**：基于已完成的 10-resample 实验产物（`src/runs/covid_resampling/` 11 方法 × 10 splits）追加六项分析，无需重新训练：
  - **E7 Robust statistical reporting**：新增 `src/jdcnet_exp/robust_stats_report.py`，对每个方法按 balanced accuracy / macro-F1 计算 median + IQR + 95% bootstrap CI（BCa 优先，degenerate 时回退至 percentile bootstrap，并以 `\ddagger`/`\dagger` 在表中标记）；`appendix.tex` 新增 `A.5 Robust Statistical Reporting` 子节（`tab:robust_stats`），替代旧的 mean±SD 解读，明确说明 $n_{\text{neg}}=1$ 下 SD 退化为单 Bernoulli draw 的二项展宽。
  - **E8 / O6 Rank stability**：脚本计算 fixed-split matrix 与 10-resample 之间的方法排名对应；Spearman $\rho=0.625$、Kendall $\tau=0.571$；`appendix.tex` 新增 `A.6 Rank Stability Across Evaluation Regimes`（`tab:rank_stability`）。
  - **E5 Convergence diagnostics**：脚本聚合 110 份 `history.csv`，画八方法 × mean ± IQR-band 的 train_loss / val balanced_accuracy 双面板图；新增 `paper/figs/covid_resampling_convergence.png` 与 `appendix.tex` `A.7 Training Convergence Diagnostics`（`fig:resampling_convergence`）；明确收敛在 ~30 epoch，否决"under-training artefact"备择解释。
  - **E9 Power analysis**：闭式 sign-test 功效表（$n_{\text{val}} \in \{20, 30, 50, 80\}$），给出 critical $k$、最小可检测 $P(\Delta>0)$、近似 balanced-accuracy gap；`appendix.tex` 新增 `A.17 Power Analysis for the Next-Cohort Experiment`（`tab:power_analysis`），把 BIMCV 50 患者的 minimum decisive 论断量化。
  - **M9 Distillation loss code listing**：`appendix.tex` 新增 `A.14 Distillation Loss Reference Implementation`，逐字嵌入 `src/jdcnet_exp/distillation.py` 的 `distillation_loss`，并交叉引用 `train.py` 的 `teacher.eval()` + `with torch.no_grad():` 位置，确认 KL 方向 $\mathrm{KL}(p_T \,\|\, p_S)$ 与 PyTorch `F.kl_div(input=log\_p\_S, target=p\_T)` 实现一致、teacher 不参与梯度。
  - **M1 / M5 Deployment efficiency**：修复 `src/jdcnet_exp/efficiency_report.py`（输入通道数 1→3 与模型 stem 对齐），用 `fvcore.FlopCountAnalysis` 计 MACs，在 CPU-only WSL 上跑 4 配置；`paper/main.tex` 新增 `4.8 Deployment-Time Efficiency` 子节（`tab:efficiency`），覆盖 reviewer 关于 TCSVT 部署/效率叙事的 M1+M5 缺口；与 `tab:progressive_complexity` 区分了"训练时 teacher+student 总参数"与"部署时 student-only 参数"两种视图，量化指出 +DPE+MHRA+DFPN 让部署参数 6×、CPU 延迟 3.7×，进一步加固 H4 否定。
  - **附带订正**：`tab:implementation_details` 中 `Epochs & 5` 与实际训练（50 epochs，history.csv 共 50 行）不符，更新为 `50 (early-stopping on validation balanced accuracy; convergence reached by ~30 in every method)`。
  - **paper preamble**：`appendix.tex` standalone preamble 加入 `\usepackage{multirow}` 与 `\usepackage{amsmath}` 以支持新表的 `\multirow` 与 `$n_{\text{neg}}$` 数学排版；main 与 appendix 双双重新编译（main 21 页、appendix 10 页）。
- **未做（仍需 GPU 或新数据，沿用既有 deferred 项）**：
  - E1 BIMCV-COVID19+ headline 整合（仍需在 H800 上完成 BIMCV 阴性 same-patient 配对；目前仅准备好 manifest）。
  - E3 ImageNet/RadImageNet 预训练 + cosine LR（Task #19）。
  - E4 BiomedCLIP frozen-feature baseline（Task #20）。
  - E6 校准（reliability diagram + ECE + Youden-J）：当前只有 fixed-split 6 个 group 的 `covid_control_val_probabilities.csv`，resampling cohort 需要从 `best.pt` 重新评估输出概率，待 GPU 环境就绪后补。
  - E10 非医学跨模态示范（如 RGB↔depth）：需引入额外数据集，规划留待下一次大改。

## 未修改或部分修改

> 本节按 `docs/revision_suggestions.tex` 的章节编号（M = Major, O = Moderate, E = New experiments, Pres. = Presentation, Eth. = Ethical, Cls. = Closing）系统化对照当前 `paper/main.tex` 与 `paper/appendix.tex` 状态。"PARTIAL" 表示在主线方向已动手但 reviewer 列出的子项仍有缺口；"NOT DONE" 表示尚未着手。

### Major Concerns (M1–M10)

- **M1 Venue fit (TCSVT) — PARTIAL**：Section 1.1 已加入 cross-modal/efficient visual computing 段；附录新增 `tab:efficiency` 给出 params/MACs/CPU latency。仍缺：(a) GPU 端 latency（本地 WSL 无 CUDA）、(b) embedded/edge 设备测量、(c) video-temporal 维度（CT volumes 仍按 axial 单切片处理）、(d) coding/compression 视角。Reviewer 给的两条出路（"重新建效率论证 vs. 改投 MIA/TMI/JBHI"）目前选了前者但只完成了一半。
- **M2 Sample size — PARTIAL**：resamples 8→10、加入 BCa CI（E7）、Wilcoxon 已报告。仍缺：BIMCV 折入 headline tables（Task #23）、paired non-COVID arm（structurally blocked，见遗留问题）、≥30 resamples 且 $n_{\text{neg}} \geq 5$。
- **M3 The proposed method does not work, paper does not pivot cleanly — PARTIAL/STRUCTURAL**：标题改为 `JDCNet: ...` 等于隐式选了"positive method"叙事，但 DPE/MHRA/DFPN 在主文与附录中仍被反复 disclaim（"executable pilot scaffold"、"not validated"）。Reviewer 在 closing note 把"naming three modules and disclaiming them"列为 single most damaging editorial choice。彻底解决需要二选一：要么撤名重写为纯 protocol paper（删 DPE/MHRA/DFPN 与 Fig.1），要么换大数据集让模块真正起效。两条路当前均未走通。
- **M4 Baseline coverage too narrow — PARTIAL**：MH/CRD/DKD/DIST 都已实跑（E2 完成）。仍缺：Cross-Modal Distillation for Supervision Transfer（Gupta 2016）作为 named baseline、BiomedCLIP/MedCLIP/GLoRIA frozen-feature baseline（Task #20）、CheXNet/ConvNeXt-Tiny strong same-modality teacher。
- **M5 Architecture below TCSVT practice — PARTIAL**：epochs 5→50 且新增收敛曲线（E5 已确认 ~30 收敛）。仍缺：ImageNet/RadImageNet 预训练（Task #19）、cosine LR schedule + warmup、224×224 训练分辨率（efficiency table 用 224 仅为测量；训练仍 128×128）。
- **M6 Statistical reporting — MOSTLY DONE / PARTIAL**：median + IQR + BCa CI 全套已加入（E7 / `tab:robust_stats`）。仍缺 reviewer 明确列出的两项：(a) 显式的 per-resample $n_{\text{pos}}/n_{\text{neg}}$ 表（revision_suggestions.tex `tab:resample_support` 占位）、(b) PR-AUC 改报 $\Delta$PR-AUC（相对于 prevalence baseline）或在 caption 中显式说明 prevalence 偏差。
- **M8 Reproducibility statement — PARTIAL**：anonymized code link 已通过 Code Ocean capsule 给出（M8 主项达成）。仍缺 reviewer 列出的：environment file pinning（main paper 应一句话写明 `requirements.txt` / Docker 在 capsule 内）、hardware/runtime details（GPU model、训练时长）、随机种子控制声明（`torch.use_deterministic_algorithms`、CuDNN benchmark off）、BIMCV redistribution restriction sentence。
- **M10 Single dataset — NOT DONE**：协议仍只在 Cohen COVID-19 Image Data Collection 上演示。Reviewer 要求至少在第二个独立 thoracic 数据集上跑同一协议；BIMCV 已准备但未折入。

### Moderate Concerns (O1–O10)

- **O1 Figure 1 described but not analyzed — NOT DONE**：架构总览图仍按 designed pipeline 呈现；reviewer 建议二选一（重画为多基线对比图 / 删除）。
- **O2 Threshold sweep descriptive, not actionable — NOT DONE**：threshold sweep 图存在但未做 calibration 介入；reviewer 要求加 prevalence-matched argmax + Youden-J 最优阈值的指标行（与 E6 部分重叠，需要 best.pt 重评估）。
- **O5 Related-work coverage dated — PARTIAL**：DKD/DIST/CRD/MH 已引用并实跑。仍缺 reviewer 点名的：Knowledge Distillation via Softmax Regression Representation Learning (ICLR 2021)、2022–2024 cross-modal medical distillation（CT-to-X-ray for tuberculosis、MR-to-CT distillation）、BiomedCLIP/MedCLIP/GLoRIA。
- **O7 "Anonymous Authors" / blinding — NOT DONE**：当前 `\author{...}` 块（main.tex 行 85–93）仍含真实姓名与机构。如果是双盲投稿需要在评审 PDF 中替换为 `Anonymous Authors`；TCSVT 当前流程需在投稿前确认。
- **O8 Inconsistent terminology — PARTIAL**：Section 3.1 有缩写词表，但 reviewer 仍指出 "Cross-modality distillation" / "Full JDCNet" 在 Table III 与 Table IV 之间互换使用。需统一表头与文段措辞。

### New Experiments (E1–E10) 未完成项

- **E1 BIMCV-COVID19+ headline integration — NOT DONE**：manifest 已准备好，但 BIMCV 缺 same-patient 阴性配对（结构性阻塞）；H800 上的训练尚未启动（Task #23）。
- **E3 ImageNet/RadImageNet pretraining + cosine LR — NOT DONE**（Task #19）。
- **E4 BiomedCLIP/MedCLIP frozen-feature baseline — NOT DONE**（Task #20）。
- **E6 Calibration（reliability diagram + ECE + Youden-J）— NOT DONE**：当前只存在 fixed-split 6 group 的 `covid_control_val_probabilities.csv`；resampling cohort 需要从 `best.pt` 重新评估输出概率，待 GPU 环境就绪后补。
- **E10 Non-medical paired-modality demonstration（如 RGB→depth）— NOT DONE**：需引入额外数据集，规划留待下一次大改。

### Required New Citations 未补

- BiomedCLIP (Zhang et al. 2023)
- MedCLIP (Wang et al. 2022, EMNLP)
- RadImageNet (Mei et al. 2022)
- Demšar (2006) on classifier comparison
- Benavoli et al. (2017) Bayesian alternatives to NHST

### Presentation & Cross-reference Hygiene

- **Pres. resizebox**：`\resizebox{\textwidth}{!}{...}` 仍用于 main 表 III/IV 与 appendix A1/A6/`tab:robust_stats`。Reviewer 建议改为 `\small` + 列重排或 `sidewaystable`，否则字号低于 IEEE 可读性下限。NOT DONE。
- **Pres. PNG → PDF**：图片仍是 PNG。Reviewer 建议同时提供 PDF 以避免期刊缩放时栅格化失真。NOT DONE。
- **Cross-ref `tab:hypothesis_status`**：仅被引用一次，reviewer 建议升格为 abstract-level 摘要。NOT DONE。
- **Cross-ref `tab:module_ablation`**：5 行表只有 1 行非零 delta，reviewer 建议改为柱状图。NOT DONE。

### Ethical & Closing

- **Eth. CLAIM checklist — NOT DONE**：reviewer 建议作为 supplementary 提供 CLAIM (Checklist for AI in Medical Imaging) 完成版。
- **Cls. 选 venue / 选叙事**：closing note 三条（数据规模不足、negative-result 在 TCSVT 文化中难发、命名又否定模块）当前均未根本解决，等同于 M2 / M3 / M10 的统一表达。

### 主文 Minor 行级项（revision_suggestions.tex 的 longtable）

- 主文 / 附录 PDF metadata（`pdftitle`/`pdfauthor`）目前未声明，技术上未泄露但也未按 reviewer 建议显式置为匿名占位 — NOT DONE（如未走双盲可忽略）。
- Main.tex 行 87–93 的 commented-out author block 含真实姓名，reviewer 建议删除而不仅是注释 — NOT DONE。
- Abstract 中按 reviewer 要求"插入每 split 的 prevalence 比例（4 pos / 1 neg）"句 — NOT DONE。
- "Computer-aided diagnosis systems"（line 121）/ "currently supported by the data and implementation"（line 131）等措辞 — NOT DONE，属低优先级。
- "Move problem-formulation table to end of Sec. I or beginning of Sec. III"（line 156） — NOT DONE。
- ViT/Swin 论证（line 175）按 reviewer 要求改写为"小队列禁用 pretrained-ViT 比较"句 — NOT DONE。
- Section III.A "Notation and Glossary" + "Task Formulation" 拆为两子节 — NOT DONE。
- BIMCV 段（main.tex 253–258）按 reviewer 要求迁出 Datasets and Cohort Construction，移入 Limitations — NOT DONE。
- "5–10 validation images per resample (mean 6.9)" 应替换为显式分布 list — NOT DONE。
- Table III `\resizebox` → `\small` — NOT DONE。
- Promote Discussion 一段进入 Section I — NOT DONE。

## 遗留问题

> 这些不是写作层面就能闭环、需要外部资源（GPU 时间、新数据、双盲规则确认、venue 决策）。

1. **BIMCV-COVID19+ same-patient negative 缺失（结构性阻塞 M2 / M10 / E1）**：BIMCV 现成的阳性 paired CT-X-ray 共 638 patients、3,080 CXR；阴性侧没有 same-patient 配对 CT。可行路径：在 BIMCV 内把 COVID-negative pneumonia patient 的 paired CT 作为阴性类（需要重新过滤 manifest、改变 label space），或换 MIDRC/MIMIC-CXR linked CT records。任一路径都会改变标签空间定义并要求作者明确说明。
2. **GPU 资源调度（影响 E1 / E3 / E4 / E6 / M5）**：所有"需要重新训练"的项（pretraining、cosine schedule、BiomedCLIP frozen baseline、resampling cohort 的 reliability/ECE/Youden-J、224×224 训练）当前都被压在 H800 启动等待中（参见 `memory/project_jdcnet.md`）。
3. **TCSVT 双盲/单盲规则（影响 O7 / Minor 85, 87–93）**：需要确认 TCSVT 当前 Information for Authors 是否双盲。若双盲：必须把 `\author{...}` 改为 `Anonymous Authors`、删 commented-out author block、确认 PDF metadata 无姓名残留。若单盲：现状即可。
4. **Venue 战略（M3 / Cls.）**：closing note 把"以 negative-result protocol 论文身份在 TCSVT 投稿"列为最大风险。若不打算 pivot 到 positive method（需要换架构 + 大数据集），更稳的策略是改投 *Medical Image Analysis* "Survey & Critical Review" 或 *NeurIPS Datasets and Benchmarks*。这是元决策，不在写作层面闭环。
5. **额外 thoracic dataset（M10）**：协议必须在第二个独立数据集上演示才能支持"protocol generality"叙事。即便 BIMCV 解了 M2，也仍需 MIMIC-CXR 子集或 RSNA Pneumonia Detection 之类的第二来源。
6. **图像资产格式（Pres.）**：PNG → PDF 的转换需要重出所有 figure 生成脚本，工作量小但需要再跑一轮分析 pipeline。可以放进下一次 batch revision。
