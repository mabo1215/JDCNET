# 进度日志

## 已全部修改

- 已建立可复现实验流水线并接入本地数据；修改说明：`src/` 已覆盖 manifest 生成、teacher/student 训练、蒸馏、评估、论文图表导出，并接入 `D:\source\covid-chestxray-dataset` 与仓库内现有结果资产。
- 已完成当前仓库中的核心实验矩阵；修改说明：已经跑通并写回论文的结果包括 student-only、late fusion、same-modality KD、plain cross-modal logit KD、full JDCNet、模块消融、imbalance controls、threshold sweep、progressive complexity 与 repeated patient-level resampling。
- 已将主文统一收口为 evidence-bounded pilot study；修改说明：`paper/main.tex` 已统一 problem formulation，明确当前研究的是 `patient-level paired`、`training-only CT supervision`、`deployment-time X-ray-only`、`binary COVID-19 vs non-COVID` 的问题，并新增主文问题边界总表。
- 已把 fixed split 与 repeated resampling 的证据层级分清；修改说明：fixed split 在主文中已明确降级为 feasibility screen，repeated same-case resampling 已提升为 primary evidence，并在主文加入对应 summary table、主图和 `hypothesis -> evidence status` 总表。
- 已把主文中的 evaluation regime 与 support counts 做到 reviewer 可见；修改说明：主文已新增 `evaluation regimes used in the paper` 总表，显式写出 reference / feasibility / primary evidence 的角色、patient/image support 和主要局限，并同步强化 fixed-split / resampling 的表格与图 caption。
- 已继续提升 headline tables 的可解释性；修改说明：主文 fixed-split 主表已显式标出 reference-only、non-same-case comparable 的 teacher-only 行，resampling 主表和附录表的 `Specificity / MCC / PR-AUC` 也已统一写成 `mean ± std`。
- 已继续压缩方法部分的重复性 framing；修改说明：主文已把原先重复的 `Why the Current Method Is Still Hypothesis-Driven` 与 `Implementation-Faithful Scope` 收敛成更短的 `Current Interpretive Scope`，降低 architecture-heavy 的观感。
- 已同步收紧附录与主文的证据表达；修改说明：`paper/appendix.tex` 已纳入 split audit、per-seed instability、resampling summary、module ablation、error analysis、imbalance controls、threshold behavior、progressive complexity、implementation notes 与 minimum next experiment。
- 已完成新一轮独立 review 并覆盖重写 `docs/revision_suggestions.tex`；修改说明：新 review 只基于当前 `paper/main.tex`、`paper/appendix.tex`、`paper/references.bib` 以及最新编译 PDF 重新给出建议，不再沿用旧轮次 review 文本。
- 已修正投稿包一致性问题；修改说明：`paper/appendix.tex` 的作者信息现已与主文一致地匿名为 `Submission ID: XXX`，`paper/main.tex` 中残留的 PDF metadata 模板占位内容也已清理。
- 已重新编译并验证最新 PDF；修改说明：`paper/build/main.pdf` 与 `paper/build/appendix.pdf` 当前都可成功生成，没有新的未定义引用，只剩少量排版级 underfull box 和已知的 MiKTeX/`caption` 提示。
- 已完成论文图片目录从 `images/` 到 `figs/` 的引用切换；修改说明：`paper/main.tex` 与 `paper/appendix.tex` 中所有 `\includegraphics{images/generated/...}` 已统一改为 `\includegraphics{figs/generated/...}`，并确认 `paper/` 下不再残留旧路径引用。
- 已修复 Windows 下的独立论文构建脚本；修改说明：`paper/build.bat` 已改为使用 `pdflatex + bibtex + pdflatex` 独立构建 `main` 与 `appendix`，产物输出到 `paper/build/`，并在成功后自动复制 `main.pdf` 与 `appendix.pdf` 回 `paper/` 根目录。

## 未修改或部分修改

- 更大 patient-level paired cohort 与真正独立的 external validation 仍未完成；修改说明：主文和附录已经把这部分写成限制与 minimum next experiment；未修改原因：当前仓库内没有更大且任务匹配的 same-patient CT+CXR 数据，现有外部资源也不足以诚实支撑独立外部验证；后续准备如何修改：优先继续寻找更大的 patient-level paired 数据，若找不到就维持 pilot-study 定位而不伪造外部验证。
- 更强的 generic feature-alignment baseline 仍未补跑；修改说明：当前仓库已补 plain logit KD、attention transfer、feature hint 等控制，但还没有更系统的 representation-alignment family；未修改原因：在当前 tiny paired regime 下继续扩展 baseline family 的边际收益有限，且容易继续堆叠方法细节而不改变证据规模；后续准备如何修改：只有在保持同一 repeated same-case resampling protocol 的前提下，才补一个更强且更通用的 feature-alignment baseline。
- Method 部分相对当前 pilot-paper 定位仍略偏 architecture-heavy；修改说明：这轮已经合并和压缩了重复的 interpretive framing，但 3.2--3.9 的模块展开仍然偏多；未全部修改原因：本轮优先处理主文 support-count 可见性与证据层级收口；后续准备如何修改：下一轮继续压缩模块叙事，把较低信号的方法细节往 appendix 迁移。
- Related Work 和 scholarly positioning 仍可再补强；修改说明：当前主文已加入 privileged modality、cross-modal transfer 和 evidence robustness 三条线，但 canonical references 仍可继续补 2--4 篇；未全部修改原因：这一轮没有再做文献层面的深补；后续准备如何修改：按新写入的 `docs/revision_suggestions.tex`，优先补 privileged modality、cross-modal supervision transfer 与 small-cohort evidence robustness 的更强定锚文献。
- 本轮没有新增新的实验运行或新的图像资产；修改说明：这一轮的重点是继续统一 problem formulation 与主文证据结构，让表格、图和正文对同一证据边界给出一致表达；未全部修改原因：在没有改变 evidence scale 的前提下，再加固定 split 微型实验的收益很低；后续准备如何修改：只有当新增实验能显著改变 evidence scale 或 baseline strength 时才继续跑，否则优先继续收紧论文写法和主文图表表达。
