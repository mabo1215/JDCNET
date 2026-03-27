# 进度日志

## 2026-03-28

### 已完成

- 已确认 `paper/` 是嵌套项目目录，并补齐 PDF 构建流程。
- 已在 `src/` 下建立可复现实验脚手架，覆盖 teacher/student 训练、蒸馏、评估、manifest 生成与论文资产导出。
- 已将本地数据集 `D:\source\covid-chestxray-dataset` 接入实验流水线，并生成 `xray_all`、`ct_all` 以及配对的 `CT -> X-ray` cohort manifests。
- 已完成真实数据实验矩阵运行，包含 repeated seeds、late fusion、temperature/alpha ablation 和模块消融（`w/o DPE`、`w/o MHRA`、`w/o DFPN`）。
- 已在可执行代码中加入可配置的 `DPE / MHRA / DFPN` 开关和配对输入的 late-fusion 支持。
- 已新增 `src/jdcnet_exp/download_kaggle_datasets.py`，并下载整理 Kaggle 上的 CT/MRI 与 COVID 影像数据到 `src/data/kaggle/`。
- 在 repeated runs 显示 late fusion 与 cross-modality distillation 都不能稳定超过 student-only baseline 后，已将论文重新定位为“诚实、可复现的 pilot study”，而非性能提升论文。
- 已创建 `paper/build.sh`，并验证投稿包现在可从命令行分别生成 `main.pdf` 与 `appendix.pdf`。
- 已创建独立可编译的 `paper/appendix.tex`。
- 已新增 `src/jdcnet_exp/generate_submission_assets.py`，使主文表格和附录资产尽量由代码生成，而不是手工硬编码进 LaTeX。
- 已将主文中的 cohort table 和 main results table 替换为 `paper/tables/generated/` 下的自动生成 LaTeX 片段。
- 已生成并接入可复现附录资产，包括：
  - patient-level split audit table
  - per-seed paired-cohort results table
  - module ablation summary table
  - per-seed instability figure
- 已清理 `paper/references.bib`，仅保留正文实际引用且相关的医学影像文献和数据集引用。
- 已在实验部分加入显式的数据集引用和数据集作者的 caution，避免把该资源写成正式 benchmark。
- 已强化方法部分文字，使 DPE、MHRA、DFPN 的文字描述与当前可执行实现更一致。
- 已重新生成关键图，并加入 per-seed overlays，让结果不稳定性在图上可见。
- 已加入附录级定性误差分析表，展示四个 paired validation case 在代表性 seed-42 checkpoint 下的预测情况。
- 已将早先偏概念化的架构图替换为与当前代码一致的 implementation-faithful schematic，并加入自动生成的 appendix implementation-details table。
- 已从主文 headline table 中去掉在极小 split 下不稳定的次级指标，只保留更可辩护的 repeated-run 比较。
- 已加入 seed-aggregated paired confusion summaries，用于揭示主导性的假阳性偏置，同时明确说明这不是更大的独立测试集。
- 已将 `main.tex` 和 `appendix.tex` 分开编译，并移除主文中对附录的跨文件编号引用，避免独立编译时出现 `??`。
- 已根据 `docs/revision_suggestions.tex` 收紧稿件，包括：
  - sharpened abstract framing
  - introduction gap paragraph
  - related-work gap summary
  - method design-rationale subsection
  - 将 experiments 明确区分为 benchmarking / stress-test / reproducibility
  - 围绕三条 transferable lessons 重组 discussion
  - 新增结构化 `Limitations and Future Work`
- 已进一步澄清各 baseline 的确切角色，明确说明更干净的 minimal cross-modal KD baseline 仍属于 future work，而不是假装当前仓库已经实现。
- 已在主文和附录中写清“minimum decisive next experiment”，并且明确停止对当前四张验证图像做更多 micro-analysis，以避免把 pseudo-evidence 包装成更强证据。
- 已规范参考文献标题中的大小写，保护 `{COVID-19}`、`{CT}`、`{X}-ray`、`{FitNets}` 等术语在独立编译时不被错误折叠。
- 已根据最新 revision 建议继续收紧主文：
  - 在 `Related Work` 中进一步强调本文核心贡献是“受控实验设定 + 可执行评估框架”，而不是成熟的新范式
  - 在方法部分新增 `Why the Current Method Is Still Hypothesis-Driven`
  - 在实验协议中明确写出“当前实验矩阵足以测试可行性和暴露 failure modes，但不足以给 cross-modality 设计排出最终名次”
  - 在主文限制部分新增 field-level evidential standard 表述
  - 在附录中进一步解释“minimum next experiment”不是泛泛地要更多数据，而是要满足明确证据条件
- 已进一步按 `revision_suggestions.tex` 做最后一轮“收口式”强化：
  - 摘要改得更偏“问题-答案-意义”，进一步压缩模块列举感
  - 引言新增“为什么这个设定若不被厘清，领域会继续误读小样本 cross-modality 结果”的说明
  - 方法部分明确区分 conceptual architecture 与 current executable instantiation
  - 实验部分补上“当前最重要的是划清哪些结论可以写、哪些不能写”的原则性表述
  - 主文更明确召回 supplementary appendix 中的 split audit、per-seed instability 和 confusion evidence
  - 结论末尾新增“未来 CT-to-X-ray transfer claim 的可信最低实验条件”总结句
- 已进一步统一 `paper/references.bib` 中 `X-Ray / X-Rays` 等题目大小写写法。
- 已成功重新编译最新 PDF。

### 进行中

- 正在判断：当前仓库是否还能诚实地补出一个比现有 student-only / same-modality KD / module-ablation 更“剥离式”的 executable cross-modal logit-KD anchor，而不破坏当前论文作为 pilot study 的诚实定位。

### 下一步

- 继续审查 `src/` 当前训练与蒸馏实现，确认是否真的存在可单独抽离出的 stripped-down cross-modal logit-KD baseline。
- 如果当前仓库仍无法支撑更强 baseline，就继续收紧主文与附录的论证，使论文稳定定位为“negative-result-informed feasibility paper”，而不是“性能声明论文”。

### 本轮精确修改文件

- `paper/main.tex`
- `paper/appendix.tex`
- `paper/references.bib`
- `docs/progress.md`

### 目前累计修改文件

- `paper/main.tex`
- `paper/appendix.tex`
- `paper/references.bib`
- `paper/build.sh`
- `paper/build.ps1`
- `paper/tables/generated/dataset_protocol.tex`
- `paper/tables/generated/main_results.tex`
- `paper/tables/generated/split_audit.tex`
- `paper/tables/generated/module_ablation.tex`
- `paper/tables/generated/paired_seed_results.tex`
- `paper/tables/generated/failure_cases.tex`
- `paper/tables/generated/implementation_details.tex`
- `paper/tables/generated/paired_confusion_summary.tex`
- `paper/images/generated/covid_matrix_main.png`
- `paper/images/generated/covid_matrix_ablation.png`
- `paper/images/generated/covid_matrix_module_ablation.png`
- `paper/images/generated/covid_paired_seed_instability.png`
- `paper/images/generated/jdcnet_executable_architecture.png`
- `paper/images/generated/paired_confusion_summary.png`
- `src/jdcnet_exp/models.py`
- `src/jdcnet_exp/data.py`
- `src/jdcnet_exp/train.py`
- `src/jdcnet_exp/evaluate.py`
- `src/jdcnet_exp/run_covid_matrix.py`
- `src/jdcnet_exp/download_kaggle_datasets.py`
- `src/jdcnet_exp/generate_submission_assets.py`
- `src/jdcnet_exp/generate_error_analysis.py`
- `src/results/covid_matrix_summary.csv`
- `src/results/covid_matrix_per_run.csv`
- `src/results/covid_matrix_module_ablation.csv`
- `src/results/covid_dataset_summary.json`
- `src/results/kaggle_download_report.json`
- `src/results/submission_assets_report.json`
- `src/results/failure_analysis_report.json`
- `paper/results/paired_failure_analysis.csv`
- `paper/results/paired_confusion_summary.csv`

### 已运行实验与命令

- `python -m jdcnet_exp.run_covid_matrix --force`
- `python -m jdcnet_exp.download_kaggle_datasets`
- `python -m jdcnet_exp.generate_submission_assets`
- `python -m jdcnet_exp.generate_error_analysis`
- `bash paper/build.sh`

### 已重新生成图表

- `paper/images/generated/covid_matrix_main.png`
- `paper/images/generated/covid_matrix_ablation.png`
- `paper/images/generated/covid_matrix_module_ablation.png`
- `paper/images/generated/covid_paired_seed_instability.png`
- `paper/images/generated/jdcnet_executable_architecture.png`
- `paper/images/generated/paired_confusion_summary.png`
- `paper/tables/generated/dataset_protocol.tex`
- `paper/tables/generated/main_results.tex`
- `paper/tables/generated/split_audit.tex`
- `paper/tables/generated/module_ablation.tex`
- `paper/tables/generated/paired_seed_results.tex`
- `paper/tables/generated/failure_cases.tex`
- `paper/tables/generated/implementation_details.tex`
- `paper/tables/generated/paired_confusion_summary.tex`

### 当前前 10 个投稿阻塞项

1. `cross-modality novelty 目前没有被稳定优于最强 paired-cohort baseline 的结果支撑`
   - 状态：`部分解决`
   - 已做修改：已将论文重写为可复现 pilot study，并删除早先偏“方法优越”的表述。
   - 未完全解决原因：写作可以降级表述，但不能替代真正缺失的经验性增益证据。

2. `验证协议过弱，因为 paired validation split 只有 4 张 X-ray`
   - 状态：`未解决`
   - 已做修改：已在主文和附录中明确 split 大小、报告 per-seed instability，并避免更强 claim。
   - 未解决原因：这需要更多 patient-level paired data，不是文字能补出来的。

3. `MHRA 被写作创新点，但当前并没有被正向验证`
   - 状态：`部分解决`
   - 已做修改：已加入可执行模块消融，并将 MHRA 改写为 provisional / hypothesis-driven 组件。
   - 未解决原因：当前消融结果反而显示去掉 MHRA 的平均结果略好。

4. `主文表格最初是手工硬编码，不利于可复现`
   - 状态：`已解决`
   - 已做修改：已加入 `generate_submission_assets.py`，并用自动生成的 LaTeX 输入替换主表。

5. `投稿包不完整，最初缺少 paper/build.sh 和独立 appendix`
   - 状态：`已解决`
   - 已做修改：已创建 `paper/build.sh` 和 `paper/appendix.tex`，并验证可分开编译。

6. `参考文献曾包含较多无关、重复或非当前稿件需要的条目`
   - 状态：`已解决`
   - 已做修改：已清理为“正文实际引用且相关”的 bibliography，并进一步规范术语大小写。

7. `数据协议和 leakage 防御原先写得不够清楚`
   - 状态：`部分解决`
   - 已做修改：已加入 dataset citation、curator caution、split audit、train/val patient counts，并收缩主文 headline metrics。
   - 未完全解决原因：当前 split 仍然太小，不足以构成 submission-grade benchmark protocol。

8. `图表证据过去不能直观看出 run-to-run instability`
   - 状态：`已解决`
   - 已做修改：已重新生成主结果图和模块消融图，加入 per-seed overlays，并加入附录 instability 图与 confusion summary。

9. `附录层面的 reproducibility 细节和 implementation-faithful packaging 原先不足`
   - 状态：`已解决`
   - 已做修改：已补齐 split audit、per-seed results、module ablations、failure cases、implementation details，以及与主文呼应的 appendix evidence。

10. `当前可执行架构和 backbone 仍更像 lightweight scaffold，而不是 submission-grade final model`
   - 状态：`未解决`
   - 已做修改：已让主文措辞与实际实现严格对齐，并明确说明这是 scaffold。
   - 未解决原因：这需要更实质的建模工作或更强的数据支持，而不是单靠改文稿。

### 根据 revision_suggestions.tex 的修改状态

#### 已修改

- `摘要改成更结果驱动、避免过度方法堆砌`
  - 状态：`已修改`
  - 说明：本轮已继续压缩模块罗列感，把摘要进一步改成“问题-答案-意义”导向，并明确本文价值是 benchmark scaffold 与 evidence boundary，而不是性能增益。

- `引言补 gap paragraph，并把贡献收束为统一三层结构`
  - 状态：`已修改`
  - 说明：已明确区分 same-modality KD、multi-modal fusion 和 training-only cross-modality transfer，并将贡献写成 problem formulation / executable framework / empirical finding。

- `Related Work 末尾补更强的 gap-summary 和比较定位`
  - 状态：`已修改`
  - 说明：已明确指出本文更像“module-augmented cross-modality logit-distillation scaffold”，并进一步补上“controlled experimental formulation and executable evaluation scaffold”这一定位。

- `Method 改成 top-down 结构并加入 design rationale`
  - 状态：`已修改`
  - 说明：已完成 Problem Formulation、Architecture、DPE、MHRA、DFPN、Training Objective 的 top-down 组织。

- `补一段 Why the current method is still hypothesis-driven`
  - 状态：`已修改`
  - 说明：已在方法部分明确写出 DPE/MHRA/DFPN 是机制驱动假设，不应被读成已验证最优解。

- `Experiments 明确区分 benchmarking / stress-test / reproducibility`
  - 状态：`已修改`
  - 说明：已在实验协议中分清三类结果的角色，避免 reviewer 误读为性能榜单。

- `补一句说明当前实验矩阵足以测试 feasibility，但不足以给 cross-modality 设计做 definitive ranking`
  - 状态：`已修改`
  - 说明：已加入明确表述，主动限制结论边界。

- `明确每个 baseline 的比较角色`
  - 状态：`已修改`
  - 说明：teacher-only X-ray、student-only、late fusion、same-modality KD 的比较职能都已写清。

- `late-fusion baseline`
  - 状态：`已修改`
  - 说明：代码和论文中都已纳入，并有重复运行结果。

- `temperature / alpha ablation`
  - 状态：`已修改`
  - 说明：已执行并写入主文，结论是当前 split 下几乎平坦，主要受数据稀缺主导。

- `module ablations (w/o DPE / MHRA / DFPN)`
  - 状态：`已修改`
  - 说明：代码、图表、主文和附录都已接入。

- `Results 围绕 transferable lessons 重写`
  - 状态：`已修改`
  - 说明：discussion 已围绕“无稳定收益 / prevalence bias / 复杂模块缺乏支撑”三条经验结论组织。

- `Limitations and Future Work 改成结构化，并定义 minimum decisive next experiment`
  - 状态：`已修改`
  - 说明：主文和附录都已明确写出最小决定性后续实验需要满足的条件。

- `把 minimum next experiment 提升为 field-level evidential standard`
  - 状态：`已修改`
  - 说明：主文末尾已加入“这不仅是 JDCNet 的下一步，也是未来 CT-to-X-ray transfer claim 的最低证据标准”这一层含义。

- `附录补 reproducibility、failure cases、implementation details、minimum next experiment`
  - 状态：`已修改`
  - 说明：附录现在已承担证据仓库角色，而不只是堆材料。

- `主文更明确召回附录中的关键证据`
  - 状态：`已修改`
  - 说明：本轮已在主文中更明确召回 supplementary appendix 的 split audit、per-seed instability 和 confusion evidence，同时避免正文被补充材料细节淹没。

#### 部分修改

- `Results/Discussion 再进一步提升为 field-level takeaway，而不只是当前实验总结`
  - 状态：`部分修改`
  - 原因：本轮已把三条 lessons 写得更判断驱动，但受当前 paired split 极小这一事实限制，仍不能把这些 takeaway 扩展成更普适的强结论。

#### 未修改

- `补充 2--3 篇更贴近 cross-modal distillation / modality transfer 的近年文献`
  - 状态：`未修改`
  - 原因：当前仓库和现有引用集中没有经过核实且可直接接入的新文献条目；为避免引入未核实或虚构引用，这一项暂不硬加。

- `加入一个 cleaner stripped-down cross-modal KD baseline`
  - 状态：`未修改`
  - 原因：当前仓库尚未实现一个比现有 student-only / same-modality KD / module-ablation 更“剥离式”的可执行 cross-modal logit-KD anchor；在没有真实实现和结果前，不能把它写成已完成。

- `把论文写成方法 superiority 论文`
  - 状态：`未修改（刻意不修改）`
  - 原因：当前真实结果并不支持这种叙事；保持 negative-result-informed pilot framing 更诚实，也更符合现有证据。
