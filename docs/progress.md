# 进度日志

## 已全部修改

- 已重新开始独立评审，并将 `docs/revision_suggestions.tex` 完全重写为新的 English-only 评审建议。
- 已建立可复现实验流水线并接入本地数据；修改说明：`src/` 已覆盖 manifest 生成、teacher/student 训练、蒸馏、评估、论文图表导出，并接入 `D:\source\covid-chestxray-dataset` 与仓库内现有结果资产。
- 已完成当前仓库中的核心实验矩阵；修改说明：已经跑通并写回论文的结果包括 student-only、late fusion、same-modality KD、plain cross-modal logit KD、full JDCNet、模块消融、imbalance controls、threshold sweep、progressive complexity 与 repeated patient-level resampling。
- 已根据最新 `docs/revision_suggestions.tex` 继续迭代：收紧固定拆分段落、确认主文高可见位置的 pilot framing、并保持主表仅聚焦同案例配对证据。
- 已将主文统一收口为 evidence-bounded pilot study；修改说明：`paper/main.tex` 已统一 problem formulation，明确当前研究的是 `patient-level paired`、`training-only CT supervision`、`deployment-time X-ray-only`、`binary COVID-19 vs non-COVID` 的问题，并新增主文问题边界总表。
- 已把 fixed split 与 repeated resampling 的证据层级分清；修改说明：fixed split 在主文中已明确降级为 feasibility screen，repeated same-case resampling 已提升为 primary evidence，并在主文加入对应 summary table、主图和 `hypothesis -> evidence status` 总表。
- 已把主文中的 evaluation regime 与 support counts 做到 reviewer 可见；修改说明：主文已新增 `evaluation regimes used in the paper` 总表，显式写出 reference / feasibility / primary evidence 的角色、patient/image support 和主要局限，并同步强化 fixed-split / resampling 的表格与图 caption。
- 已继续提升 headline tables 的可解释性；修改说明：主文 fixed-split 主表已显式标出 reference-only、non-same-case comparable 的 teacher-only 行，resampling 主表和附录表的 `Specificity / MCC / PR-AUC` 也已统一写成 `mean ± std`。
- 已继续压缩方法部分的重复性 framing；修改说明：主文已把原先重复的 `Why the Current Method Is Still Hypothesis-Driven` 与 `Implementation-Faithful Scope` 收敛成更短的 `Current Interpretive Scope`，降低 architecture-heavy 的观感。
- 已同步收紧附录与主文的证据表达；修改说明：`paper/appendix.tex` 已纳入 split audit、per-seed instability、resampling summary、module ablation、error analysis、imbalance controls、threshold behavior、progressive complexity、implementation notes 与 minimum next experiment。
- 已完成新一轮独立 review 并覆盖重写 `docs/revision_suggestions.tex`；修改说明：新 review 只基于当前 `paper/main.tex`、`paper/appendix.tex`、`paper/ref.bib` 以及最新编译 PDF 重新给出建议，不再沿用旧轮次 review 文本。
- 已修正投稿包一致性问题；修改说明：`paper/appendix.tex` 的作者信息现已与主文一致地匿名为 `Submission ID: XXX`，`paper/main.tex` 中残留的 PDF metadata 模板占位内容也已清理。
- 已重新编译并验证最新 PDF；修改说明：`paper/build/main.pdf` 与 `paper/build/appendix.pdf` 当前都可成功生成，没有新的未定义引用，只剩少量排版级 underfull box 和已知的 MiKTeX/`caption` 提示。
- 已完成论文图片目录从 `images/` 到 `figs/` 的引用切换；修改说明：`paper/main.tex` 与 `paper/appendix.tex` 中所有 `\includegraphics{images/generated/...}` 已统一改为 `\includegraphics{figs/generated/...}`，并确认 `paper/` 下不再残留旧路径引用。
- 已修复 Windows 下的独立论文构建脚本；修改说明：`paper/build.bat` 已改为使用 `pdflatex + bibtex + pdflatex` 独立构建 `main` 与 `appendix`，产物输出到 `paper/build/`，并在成功后自动复制 `main.pdf` 与 `appendix.pdf` 回 `paper/` 根目录。
- 已完成当前 revision cycle 中面向 MICCAI 的主文收口；修改说明：`paper/main.tex` 已进一步压缩 Section 3 的 architecture-heavy 叙事、强化 fixed split 与 resampling 的 evidential role/support-count 可见性，并在 `paper/ref.bib` 中补入 privileged information、modality hallucination 与 medical-imaging evaluation robustness 的定锚引用后重新编译通过。
- 已继续压缩主文 Method 叙事并把低信号模块定义后移；修改说明：`paper/main.tex` 现仅保留 pilot scaffold、interpretive scope 与 hypothesis-control mapping，DPE/MHRA/DFPN 的具体机制定义与 generic feature-alignment baseline 的取舍说明已转移到 `paper/appendix.tex`。
- 已补强主文的 scholarly positioning 文献锚点；修改说明：`paper/ref.bib` 新增 CheXpert、MIMIC-CXR、hidden stratification、Transfusion 与 cross-hospital generalization 五个定锚文献，并已写入 `paper/main.tex` 的 thoracic benchmark、medical transfer 与 evidence-robustness 叙述。
- 已继续压缩 Introduction 的定位句并补入 1 篇关键 shortcut/domain-shift 文献；修改说明：`paper/main.tex` 现将引言收紧为更接近 MICCAI submission voice 的问题界定，并在 `paper/ref.bib` 中补入 chest-radiograph shortcut 证据以支撑对 tiny paired gains 的谨慎解读。
- 已继续压缩 Abstract 与 Conclusion 的开头句；修改说明：`paper/main.tex` 现将摘要与结论开头统一改写为与 Introduction 一致的 deployment-oriented pilot-study 口径，减少泛化式铺垫并更快收口到 training-only CT supervision for X-ray deployment 的问题定义。
- 已将参考文献文件统一重命名为 `paper/ref.bib`；修改说明：`paper/main.tex`、`paper/appendix.tex`、仓库规则说明与 `.codex/config.toml` 现已全部切换到新路径，避免后续构建和 agent 配置继续引用旧的 `paper/references.bib`。

## 未修改或部分修改

- 更大 patient-level paired cohort 与真正独立的 external validation 仍未完成；修改说明：主文和附录已经把这部分写成限制与 minimum next experiment；未修改原因：当前仓库内没有更大且任务匹配的 same-patient CT+CXR 数据，现有外部资源也不足以诚实支撑独立外部验证；后续准备如何修改：优先继续寻找更大的 patient-level paired 数据，若找不到就维持 pilot-study 定位而不伪造外部验证。
- 更强的 generic feature-alignment baseline 仍未补跑；修改说明：主文与附录现已明确说明 attention transfer 与 feature hint 已覆盖当前最低成本的通用 alignment 控制，而更强 representation-alignment family 需要在同一 repeated same-case resampling protocol 下配合更大 patient support 才有解释价值；未修改原因：当前 tiny paired regime 下继续扩展 baseline family 更可能增加方法空间而非证据强度；后续准备如何修改：只有在拿到更大 paired cohort 或更可解释的负例支持后，才补一个更强且更通用的 feature-alignment baseline。
- Method 部分相对当前 pilot-paper 定位仍略偏 architecture-heavy；修改说明：这轮已经进一步把主文中的模块实现定义后移到 appendix，并将主文收紧为 hypothesis-control 叙事；未全部修改原因：Section 3 仍需后续继续评估是否还能再删减一层小节密度；后续准备如何修改：下一轮继续检查 3.1--3.5 是否还能合并表述，尽量只保留问题定义、损失函数和可检验假设。
- Related Work 和 scholarly positioning 仍可再补强；修改说明：当前主文已补入 CheXpert、MIMIC-CXR、hidden stratification、Transfusion、cross-hospital generalization 与 chest-radiograph shortcut 六个更强定锚点，并继续保留 privileged modality、cross-modal transfer 和 evidence robustness 三条线；未全部修改原因：canonical references 仍可视篇幅再补 0--1 篇最关键的 medical transfer 或 evaluation 文献；后续准备如何修改：按新写入的 `docs/revision_suggestions.tex` 继续择优补强，不再做低价值的堆砌式加引。
- 本轮没有新增新的实验运行或新的图像资产；修改说明：这一轮的重点是继续统一 problem formulation、Introduction 定位句与主文证据结构，让表格、图和正文对同一证据边界给出一致表达；未全部修改原因：在没有改变 evidence scale 或 baseline strength 的前提下，再加固定 split 微型实验的收益很低；后续准备如何修改：只有当新增实验能显著改变 evidence scale 或 baseline strength 时才继续跑，否则优先继续收紧论文写法和主文图表表达。
