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

无。

## 遗留问题

无。
