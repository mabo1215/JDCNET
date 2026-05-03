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

## 未修改或部分修改 

无。

## 遗留问题

无。
