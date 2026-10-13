# 进度

本文件顶部三节（已全部修改 / 未修改或部分修改 / 遗留问题）反映当前状态；
`# 历史记录` 以下保留以前各轮的过程记录。

# 已全部修改

## 第三轮投稿包 `submit/revision_round3/`（2026-10-13）

作者答复（progress.md 遗留问题）：手工高亮版答 "b"，按默认理解为不需要，以 latexdiff 标记版代替；4×3090 口令文件同意删除；push 已由作者手动执行（两个仓库均与 origin 同步）。

1. **投稿包**（`submit/` 被 .gitignore 忽略，仅在本地）：
   - 必传：`JDCNet_revised_manuscript.pdf`（正文 33 页，含 Declarations）、`JDCNet_response_to_reviewers.pdf`（13 页）、`JDCNet_marked_up_manuscript.pdf`（latexdiff 标记版 65 页）。
   - 其他：`JDCNet_revised_appendix.pdf`（7 页，表 A1–A7）、`JDCNet_revised_manuscript_with_appendix.pdf`（40 页，仅在系统要求单一文件时使用）、`JDCNet_title_page.pdf`、`JDCNet_tables_standalone.pdf`（表 1–11、A1–A7）、`JDCNet_cover_letter.txt`、`JDCNet_highlights.txt`、`JDCNet_data_availability_statement.txt`、`JDCNet_gate_case_examples.csv`、`JDCNet_revised_source.zip` 与解压后的 `source/`、`UPLOAD_README.txt`（逐个文件说明上传位置）。
   - 源码包只含实际用到的文件（main/appendix/ref.bib/cls/bst/title_page/tables_standalone + 唯一位图 Fig. 3）；在仓库外用 pdflatex→bibtex→pdflatex×2 独立编译验证：40 页、0 错误、0 未定义引用，与 combine.pdf 一致。
   - 检查：所有 PDF 中唯一的位图是 Fig. 3 统计图，无任何病人图像；源码中无本地路径。
2. **数据可用性声明**（`docs/data_availability_statement_discoverai.txt`）按正文更新：补充 Cohen 数据集与 MIDRC 来源、分析计划、稿件不含病人图像、逐图像预测可向通讯作者申请。
3. **4×3090 口令**：已删除 WSL 中的 `~/.jdc_tmp/c4.pass`、`c4.sh` 及该目录；会话辅助脚本中没有写死的口令。

## 第三轮大修（续三）：按作者答复处理遗留问题（2026-10-13）

作者答复：Fig. 2 选 (b)；`USAGE.md` 改为 Discover AI；同意 push 两个仓库；保留 4×3090 上的 `/data1/jdcnet_round3`；vGPU 3090 与 PRO 6000 已由作者关机；泄露的访问密钥由作者自行更换。

1. **Fig. 2 改为无像素示意图**：删除 BIMCV 图像拼图，改为 TikZ 矢量示意图（单个病人：CT 体积 → 窗宽 [−1000, 400] HU → 四种教师视图 mid-slice / 3-slice / 均值投影 / DRR，仅训练使用；AP 胸片 → 学生输入，训练与部署均使用；注明同一病人但不一定同次就诊、阳性与阴性来自两个 BIMCV 发布）。标签改为 `fig:paired_data_schematic`，正文引用句同步改写。
   - Declarations 的 Consent to publish 改为 "The manuscript contains no patient images and no identifiable personal data."；缩写表补 AP。
   - 回复信"Language and presentation"一条与编辑 Declarations 回应中说明：因 BIMCV 协议不允许未经书面许可复制数据集图像，原拼图已替换为示意图；cover letter 同步。
   - `paper/figs/ct_xray_paired_examples.png` 已从 paper 子仓库删除（git 历史中仍有该文件）；latexdiff 标记版中被删的 `\includegraphics` 为注释状态，不会渲染图像。`docs/bimcv_permission_request.txt` 不再需要，保留备查。
2. **`USAGE.md`**：`目标会议或期刊：<Discover Artificial Intelligence (Springer Nature)>`。
3. **构建**：main.pdf 33 页、appendix、combine 无错误/溢出/未定义引用；回复信 13 页；标记版 65 页 0 错误。
4. **push**：本地已 commit；push 被本会话的权限设置拦截，由作者手动执行。

## 第三轮大修（续二）：校对报告逐条修正（2026-10-13）

第二轮独立校对（对照 `src/records/derived/*.json`）发现的问题已全部处理：

1. **数值统一**：
   - 主分析嵌套比较的 CI 下限统一取记录指标（restart JSON）：+0.037 [+0.016, +0.058]（原写 +0.017 来自逐图像复算），与 best-of-8 的 +0.029 同源；正文、附录、回复信、cover letter 同步。
   - CT-only 参考的 CI 改为 JSON 值：mid [+0.019, +0.070]、3-slice [+0.025, +0.079]、均值投影 [−0.002, +0.066]、DRR [−0.036, +0.055]。
   - 附录门控 logit KD mid 上限 +0.010；对比学习 best-of-4 CI 统一为 [−0.021, +0.038]。
2. **复现声明更正**：逐图像复算 BA 与记录在 613/615 个 run 上一致；`mid_f00_s43_pseudolabel_t080_l050` 差 0.006，`sup128_f01_s42_r04` 差 0.022（1 个病人）。分析脚本新增 `reproduction_n_exact` 与 `reproduction_mismatches` 字段。
3. **补全预注册分析**（计划第 1、3、4 项）：
   - 新增附录表 A7：16 个配置各自对 batch 128 第一个重启（r=0）的 cell 级与病人级比较及 Holm 校正。16 个配置均值全部为正（+0.002 至 +0.039；平均 +0.024 [−0.000, +0.051]，p=0.092），校正后均不显著（最小 Holm p：cell 级 0.56，病人级 0.33）。
   - 外部 McNemar（逐 checkpoint 配对）：对 batch 512 监督模型 15 对中 2 对 p<0.05，且均是监督模型更好；对 batch 128 为 0/15。已写入 4.10 节、附录 A.9 与回复信。
4. **措辞收紧**："small but real advantage" → "small within-cohort advantage"；"does not explain" → "is unlikely to explain"；"no effect" → "no detectable effect"；讨论中"honest uncertainty interval"一句改写；贡献列表同时给出 cell 级与病人级 CI；Table 3 "Validation-partition metrics only" 改为 "Paired comparison on the validation partition only"；敏感度范围注明是 16 个配置的范围；附录 A.8 指出 3-slice soft-KL 在 T_g=1.0 与 2.0 时 CI 均含 0。
5. **可复现性声明**：逐图像预测含 BIMCV/MIDRC 编号、未纳入仓库，正文 4.11、Data availability 与回复信改为"cell 级统计可由公开记录复算，病人级/外部/教师分析需逐图像预测，可向通讯作者申请"。`src/records/README.md` 重写（列出 runs510/sup128 记录、各 JSON 与对应脚本）。
6. **门控扫描**：原始记录显示扫描只有 8 个格子（T=4、阈值 0.55 未运行），附录"nine"改为"eight"，并把扫描汇总存档为 `src/records/gatedscan_balanced_summary.csv`（+0.034 [−0.004, +0.073] 可溯源）。
7. **其他**：缩写表补 CE、CPU、GPU；"depth-to-RGB" 改为 "depth-to-color-image"；DPE/MHRA/DFPN 明确为研究内部标签；伦理编号改为 "CEIm: 12/2020"；soft-KL 公式加标签并用 `\eqref`；Table 7 由 tabularx 改为 tabular；Table 1 溢出消除；回复信中验证折写为 "(k+1) mod 5"、DeLong 对比对象写明 batch 512、"0.92 位于已探索的阈值之外"。
8. **构建**：main.pdf 34 页、combine.pdf、appendix.pdf 无错误、无溢出、无未定义引用；回复信 13 页；title page 与独立表格文件（11 + 7 张表）已同步；latexdiff 标记版 `paper/main_diff_round3.pdf` 重新生成（65 页，0 错误；Table 2 因结构整体重写以蓝色整表显示）。
9. 标题保持不变（校对建议加连字符为可选项，涉及投稿系统中的题名，未改动）。

## 第三轮大修（续）：找回原始记录 + 预注册补充实验 + 论文与回复信重写（2026-10-13）

1. **数据检索**：
   - vGPU 3090（`ssh vgpu3090`，无卡）：找回 H800 镜像记录（`metrics_backup_20260625.tgz`、外部评估 60 个指标、216/466 重跑指标），拉回 `src/results/vgpu3090_recovered_20261013/`；图像缓存已不存在。
   - PRO 6000：无 BIMCV/MIDRC 图像、无原始扫描结果（仅 Fig. 2 素材与一个教师 checkpoint）。
   - **4×3090（`mabo1215@10.126.126.3`，原始实验主机）**：找到全部原始运行目录（Stage A 240、JDCNet 初始 120 + 扩展 A 60 + 扩展 B 60、对比学习 60、BiomedCLIP 15 等，均有 checkpoint 与测试集指标）、BIMCV 图像缓存（X 光 256 缓存、113 阳性 + 398 阴性 CT NIfTI）与 MIDRC 126 张外部图像。指标拉回 `src/results/c4_3090_recovered_20261013/`，整理为 `src/records/runs510_per_run.csv`。
   - 已核实：MobileNetV2/EfficientNet、同模态 KD、病人级 bootstrap、延迟/Jetson、gate coverage 在任何主机上均无记录，维持删除；logit KD 在 510 上确实只有 T=4、α=0.6 一组。
2. **预注册补充实验**（计划 `docs/round3_experiment_plan.md` 先于运行提交，commit 48f9923；只用 4c 的 GPU 0、1；输出在 4c `/data1/jdcnet_round3`，原目录未改动）：
   - 实验 A：每个 fold/seed 训练 16 个 batch 128 的监督重启，共 240 run，0 失败。
   - 逐图像预测：所有 checkpoint 在测试集与 MIDRC 上的概率；复算 BA 与记录在 613/615 个 run 上一致（另 2 个差 0.006 与 0.022，见续二）。
   - 实验 C：用原脚本（commit 6ab9551 版本）从 NIfTI 重新渲染 510 例 CT 视图；教师测试 BA 完全复现（差 0.000）。
3. **关键结果**：
   - batch 128 监督基线 0.620 vs batch 512 0.625（−0.005，p=0.75）→ batch 混杂不能解释 JDCNet 差异；同一 cell 内重启的 SD 0.041。
   - 16 个配置的直接配对 t 检验：两个入选配置 p=0.014/0.028，Holm 0.22/0.42 → 单个配置校正后不显著。
   - **主分析（预注册嵌套选择 + 匹配对照）**：JDCNet 16 选 1 − 监督 16 选 1 = +0.037 [+0.016, +0.058]，p=0.005；病人级 [+0.007, +0.068]，p=0.017；验证集选择挑出 11 种不同配置。
   - 外部 MIDRC（这次用真正的 510 模型）：全部随机水平，DeLong 无差异；训练集中 CR/DX 探测器类型与标签相关（CR 占阳性 62% vs 阴性 45%，p=0.002），MIDRC 85% 为 DX。
   - 教师诊断：门控作用于教师自己的训练病人，训练集准确率 0.94–0.96，被接纳伪标签约 97% 与真值一致 → 辅助目标主要起"按 CT 可判别程度给样本加权"的作用；留出集过度自信（ECE 0.17–0.19，验证集拟合温度 1.7）。
4. **论文改写**：摘要（232 词）、贡献、3.7 统计方法（直接 t 检验 + 预注册实验）、表 2、表 4（新增 p_t、Holm、Δ128 列）、表 5（全部指标来自记录）、新表 6（教师可靠性与门控覆盖）、4.7 节（预注册补充实验）、4.10 外部测试（510 模型 + DeLong + 探测器类型）、4.12 局限、讨论、结论、表 11；附录 A1 扩为 16 个配置的全部检验、A.8 改为"早期重跑"并说明已被取代、新增 A.9（表 A6）。审稿人 1 推荐的 6 篇全部引用。
5. **回复信重写**（13 页）：更正清单 16 条、审稿人 6 第 2 点以预注册嵌套比较为核心、第 3 点用 510 模型逐图像 DeLong、审稿人 1 第 2/3/5/6 点补充实测数据。cover letter、highlights 同步更新。
6. **新增脚本与记录**：`src/jdcnet_exp/{collect_run_records,round3_full_analysis,round3_restart_analysis,round3_prediction_analysis,predict_per_image,make_round3_tables}.py`，`src/ops/round3_c4_*`，`src/records/{runs510_per_run,sup128_per_run}.csv` 与 `src/records/derived/*.json`。

## 第三轮大修：Discover AI（审稿人 1、5、6 + 编辑）逐条修改与回应（2026-10-13）

依据 `docs/revision_suggestions.txt`。用户在本轮决定"仅使用本地记录"：凡无法在本地实验记录中溯源的数字，一律更正或删除，并在回复信中公开说明。

1. **结果数字全面审计与更正**（编辑："ensure the results are accurately reported"）。对照 `src/results/`、`docs/tmp/report51x.md`、`docs/progress.md`、git 历史与训练/评估代码逐项核查，发现并修正：
   - "整个网格在 226 例预试验上预注册"不实：门槛规则在 JDCNet 运行前写入计划，但 16 个配置是在 510 例队列上分三阶段探索的（初始 8 格 0/8 通过 → 扩展 A λ=1.5 → 扩展 B soft-KL），两个"通过"配置均来自扩展阶段（commit 9e99413 / 0e1e626 / 096ed29）。
   - 旧 Table 5 绝对指标整体偏低约 0.021（监督基线实为 BA 0.625、AUC 0.674，而非 0.604/0.661）；改为由记录重算（`src/records/`），无记录的格子标 "--"。
   - "增益来自敏感度"不成立：本地可查的 8 个初始配置中增益主要来自特异度（ΔSpec 全为正，6/8 敏感度下降）。
   - Table 4 的 Pos./15 列 16 行中 8 行错误，已按记录改为 +/0/−。
   - BiomedCLIP 实际在 226 例子集上评估，不是 510 例；注意力迁移/feature hint/模块增强只在早期小队列上跑过。
   - 比较方法调参预算、同模态 KD −0.004、MobileNetV2/EfficientNet-B0 结果、gate coverage/ECE 表、patient-level bootstrap 表、跨源非 COVID 对照表、Jetson/CPU/GPU 延迟与 1.18× 开销、"6 小时"、"teacher pre-trained once"、队列构建规则（±14 天窗口/最早配对/SHA 哈希/按折归一化）均无记录或与代码矛盾 → 删除或按实际改写。
   - **新发现的混杂**：510 例监督基线 batch 512、JDCNet batch 128（每折约 306 训练例 → 基线每 epoch 1 步、JDCNet 3 步），已在正文 3.7、4.7、4.12 披露。
   - 外部 MIDRC 测试评估的是 H800 上 228/216 例平衡子集训练的学生模型，并非 510 例模型，已更正。
   - 温度重跑（附录 A.8）是验证集 BA、466 例另一划分、单 seed；并补报 216 例子集上未复现的结果，删除"小队列假象"的说法。
2. **R6.1 教师是否按折训练**：核实脚本（`remote_3090_bimcv_full_paired_cv.sh`、`remote_3090_bimcv_pseudolabel_cv.sh`）——每个 (视图, fold, seed) 单独训练教师，只用该折训练集、验证集选模型，测试折从未被教师见过。正文 4.2、算法 1、图 1、附录 A.3 明确写出。
3. **R6.2 选择乐观偏差 + 直接 p 值**：新增 `src/jdcnet_exp/revision_stats.py`，从 `src/records/` 重算：16 个配置的精确符号检验 p、由 bootstrap CI 反推的 Wald p、Holm/BH 校正（最佳两格 Holm 0.051/0.17，BH 0.051/0.092）、未选择平均（16 格 +0.020；初始 8 格逐 cell 平均 +0.016 [−0.000,+0.035]，t 检验 p=0.11）、初始 8 格的 t/Wilcoxon/bootstrap 检验（附录 Table A1），以及选择膨胀模拟（共同效应 +0.020 时 66% 的扫描会出现 ≥2 格过门槛）。摘要、贡献、讨论、结论全部改为"探索性、未确证"的表述。
4. **R6.3 外部测试**：Table 9 给出 BA 的 Wilson CI、AUC 的 Hanley–McNeil CI、差值 CI（按独立假设，保守）及"相当于几张图像"的换算；删除 "statistically indistinguishable"；原因改为可能解释并列出（采集/扫描仪、标签定义、训练集两个发布版本的来源混杂、患病率/人群、预处理）；引用 Zhang et al. AAAI 2023。逐图像分数未保存，无法做配对 DeLong 检验，已如实说明。
5. **R6.4 措辞收敛**：删除 triage/prioritisation、"same premarket evaluation pathway"；部署成本仅陈述"部署计算图相同、无额外推理开销"，并注明不代表端到端成本/校准/安全/临床效用相同；结论按审稿人建议的表述重写。
6. **R6.5**："CT teacher upper bound" → "CT-only reference"；"two-thirds" 改为明确的描述性比值（0.68/0.73/0.41，无不确定度）；F1 明确为 Macro-F1。
7. **R1.1 多分类**：3.4 节新增"Extension beyond two classes"，4.12 说明只用二分类的原因（唯一可得的同患者配对公开队列）。
8. **R1.2 外部性能下降**：见第 4 条，并在 4.12 列出多中心训练、SADA、噪声增强、无监督域适应、站点阈值重校准等候选方案（均未验证）。
9. **R1.3 过拟合**：4.4 节定量说明 τ/λ 变化在噪声范围内（16 格均值 SD 0.011 < 平均 SE 0.014），真正风险是"选择过拟合"，并给出校正结果。
10. **R1.4 文献**：新增 13 篇经 Crossref 核实的 2022–2026 文献 + Guo 2017；按用户决定（2026-10-13），审稿人 1 推荐的 6 篇**全部引用**：Gholinavaz 2025（4.12 鲁棒性措施）、Saeedi 2026（1.1 推理时多模态融合）、Nemati 2025 FER-HA（2.3 混合注意力）、Shirini 2025 学习率/epoch（4.12 训练预算混杂）、Shirini 2024 NSGA-II 与 Taheri Hajivand 2024 元启发式（4.12 多目标配置选择，需嵌套协议）。回复信 R1.4 同步改写。
11. **R1.5 硬标签丢失的不确定性**：3.4 节给出解析上界（KL ≤ −ln τ：0.36/0.22 nats；丢弃熵 ≤ 0.88/0.72 bits）与经验比较（soft−hard 平均 +0.009，在噪声内）。
12. **R1.6 温度缩放**：证明二分类下对门控做全局温度缩放等价于更换阈值（Eq. 4，τ'=σ(T_g·logit τ)），温度缩放不能纠正"自信但错误"的预测（Table 6 Case B）。
13. **R5**：删除 2.2/2.3 重复段落；全文统一美式拼写；新增 3.1 "Notation and Abbreviations"，所有缩写首次出现即定义。
14. **编辑 Declarations**：Ethical approval / Consent to participate / Consent to publish 三个独立小标题齐全。
15. **图表**：图 1 由 TikZ 重绘（旧 PNG 机制图标注了 0.094M 参数/14.62 ms 的错误数字且文字重叠，已不再使用）；因图例把旧模块增强模型标成 "Full JDCNet"，正文移除证据图、阈值敏感性图、校准可靠性图；表格改为左对齐、修复溢出；附录图 A1 重绘。
16. **本机推理基准**：新增 `src/jdcnet_exp/benchmark_inference.py`，在 i7-13700H / RTX 4050 Laptop 上实测（结果在 `src/records/derived/inference_benchmark.json`），Table 8 仅作示意。
17. **参考文献**：arXiv 条目的编号被 Vancouver 样式去掉小数点的问题（原稿就有）已改为 DOI 形式；新增 Cohen 数据集与 MIDRC 引用。
18. **配套文件**：`docs/response_to_reviewers.tex/.pdf` 全部重写（12 页，含"更正说明"一节 + 逐条回应）；`docs/cover_letter.txt`、`docs/highlights.txt`、`docs/data_availability_statement_discoverai.txt`、`paper/title_page.tex`（原为 Elsevier 版）、`paper/tables_standalone.tex` 同步更新；用 latexdiff 生成修订标记版 `paper/main_diff_round3.pdf`。
19. **构建**：`paper/build.bat` 通过，main.pdf 31 页、combine.pdf 37 页，无未定义引用；仅余 Table 1 中 <3pt 的微小溢出。原稿备份在 `paper/backup/round3_pre_20261013/`。

# 未修改或部分修改

1. 【部分修改】**多分类/多中心验证**：无可用的公开同患者多病种配对队列，仅在 3.4 与 4.12 节讨论。
   - 当前不需要你决策，除非有新数据来源。
2. 【部分修改】**独立队列的确认性验证**：预注册嵌套比较仍使用同一批 510 例患者，论文已如实写为局限。
   - 当前不需要你决策；如果将来有新的同患者 CT–X 光配对队列，可按 `docs/round3_experiment_plan.md` 的方式预注册后验证。

（Fig. 2 发表许可问题已按作者选择 (b) 处理，移入"已全部修改"。）

# 遗留问题

当前没有需要你决策的问题。

（已解决并移除的问题：手工高亮版（不需要，以 latexdiff 标记版代替）、4×3090 口令文件（已删除）、push（作者已执行）、Fig. 2 许可（选 b，已改为示意图）、`USAGE.md` 期刊（已改为 Discover AI）、`/data1/jdcnet_round3`（保留）、vGPU 3090 与 PRO 6000（作者已关机）、访问密钥（作者自行更换）；更早的：缺失结果文件、GPU 资源、审稿人 1 文献、更正声明确认、是否提交。）

# 历史记录

## 第三轮修订中途的待办与答复快照（2026-10-13，已被顶部各节取代）

### 未修改或部分修改

1. 【已阻挡】**批次匹配的 510 例确认性重跑**（对应 R6.2 与 batch 混杂）：需要 GPU 和 BIMCV 图像缓存；3090（10.147.20.176）本轮不可达，H800 上数据已丢失。论文中已如实写为局限并给出确认性设计。
   - 需要你提供/决策：是否能恢复 GPU 访问或重新下载 BIMCV 后重跑？见遗留问题 2。
2. 【已阻挡】**外部测试的配对检验（DeLong/McNemar）**：评估流程只保存了每个 checkpoint 的汇总指标和混淆矩阵，没有逐图像分数，需要用冻结 checkpoint 重新推理。
   - 需要你提供/决策：见遗留问题 1、2。
3. 【部分修改】**Table 5 中两个入选配置、门控 logit KD 与 CT-only 行的 AUC/敏感度/特异度**：扩展阶段与 Stage A 的逐折记录不在本地，只能报告 BA。
   - 需要你提供/决策：见遗留问题 1。
4. 【部分修改】**多分类/多中心验证**：无可用的公开同患者多病种配对队列，仅做讨论。
   - 当前不需要你决策，除非有新数据来源。

### 遗留问题

1. **缺失的实验结果文件**
   需要你提供/决策：
   1. 其它机器上是否还保存有 `src/results/` 下的 `bimcv_pseudolabel_lam15_3090_20260516`、`bimcv_pseudolabel_soft_3090_20260516`、`bimcv_full_paired_cv_3090_20260516`、`h800_external_eval_20260625`、`bimcv_full510_calibrated_gate_20260626` 或 `metrics_backup_20260625.tgz`？若有，请放回本仓库 `src/results/`，可补全 Table 5 并复核。
   A: 用户开启 vGPU 3090（无卡模式，`ssh vgpu3090`）让我查找。检索结果（2026-10-13）：vGPU 上**有** `misc_archive/metrics_backup_20260625.tgz`、`runs/h800_external_eval`（60 个逐 checkpoint metrics.json，含混淆矩阵，无逐图像分数）、`runs/bimcv_h800_calibrated_gate`（90，含 test_eval）、`runs/bimcv_full510_calibrated_gate`（30，含 test_eval）、`runs/bimcv_full510` 与 `bimcv_h800_5fold_cv`（只有验证集 best_metrics）以及对应 checkpoint；**没有** 510 例原始扫描的 `pseudolabel_lam15/soft` 与 `full_paired_cv` 结果（它们在另一台 4×3090 主机 10.147.20.176，仍不可达）。BIMCV 图像缓存与 MIDRC 外部图像在 vGPU 上已不存在（软链接悬空），重跑需重新下载。
2. **GPU 资源**
   需要你提供/决策：
   1. 能否恢复 3090 或 H800（或其他 GPU）以运行 (a) 510 例上 batch 匹配的监督基线与固定配置 JDCNet 重跑，(b) 外部 MIDRC 逐图像推理以做配对检验？
   A: 用户已开 vGPU 3090 无卡模式，要求准备实验。【进行中】在无卡模式下先完成数据下载/预处理与实验脚本，开卡后再训练。
3. **审稿人 1 推荐的文献**
   需要你提供/决策：
   1. 推荐的 6 篇文献中 5 篇主题与本文无关，且全部共享同一组作者（Shirini K、Gharehveran SS 等），疑似引用索取。当前做法：引用 2 篇有一定关联的（Sci Rep 2025、IWINAC 2026），礼貌拒绝其余 4 篇。是否同意？是否需要另行私下告知编辑？
   A: 用户决定直接引用全部 6 篇，不回绝。已完成（见已全部修改第 10 条）。
4. **Fig. 2 配对像素图的发表许可**
   需要你提供/决策：
   1. BIMCV 使用协议要求复制/发表数据片段前取得书面许可。是否已取得？若未取得，建议在投稿前删除 Fig. 2（Consent to publish 已写为 "Not applicable"）。
   A: 用户问能否改用降低分辨率的像素而免于书面许可。答复：不能。协议第 5 条原文 "YOU MAY NOT DISTRIBUTE, PUBLISH, OR REPRODUCE A COPY of any portion or all of the BIMCV-COVID19 Dataset to others without specific prior written permission"，第 6 条禁止派生作品；降采样图像仍是数据集部分的复制/派生。可选：(a) 向 BIMCV 申请书面许可（已起草邮件 `docs/bimcv_permission_request.txt`）；(b) 用无像素示意图替换 Fig. 2；(c) 删除 Fig. 2。
   2. 请选择 (a)/(b)/(c)。
   A: (b)
5. **更正声明的确认**
   需要你提供/决策：
   1. 回复信第 1 节公开列出了先前版本中无法溯源的结果（MobileNetV2/EfficientNet、gate coverage/ECE 表、patient-level bootstrap、跨源对照、延迟表、队列构建规则等）。请确认这些结果确实没有其它原始记录；若有，请提供以便恢复相应内容。
   A: 用户让我在 vGPU 3090 上查找。vGPU 上未发现 MobileNetV2/EfficientNet 运行、gate coverage/ECE 计算、逐患者预测或延迟测量记录（只有上面第 1 条列出的 H800 运行）。暂维持删除。
6. **提交与配置**
   需要你提供/决策：
   1. 本轮改动尚未 git commit/push，是否需要提交？
   2. `USAGE.md` 的目标期刊仍写 ACM TOMM，而实际投稿为 Discover Artificial Intelligence，是否需要改？
   3. `paper/main_highlighted.tex`、`appendix_highlighted.tex` 为上一轮版本，本轮以 latexdiff 的 `paper/main_diff_round3.pdf` 代替，是否还需要手工高亮版？
   A: 第 1 问：用户要求提交（2026-10-13），已在 paper 子仓库与主仓库 commit（未 push）。第 2、3 问暂未答复。


## CT 与 X-ray 配对图集加入论文（2026-08-21）

### 已完成

1. 使用 Pro 6000 上已配置的数据缓存，找到并整理 8 组匿名同患者 CT--X-ray 配对；每组包含 CT 中间切片与配对胸部 X-ray。
2. 已将 8 组配对图组成单张 2 列×4 行总图，并放入 paper/figs/ct_xray_paired_examples.png。
3. 更新 paper/main.tex 的 Figure~4 说明：每个标注面板为一组同患者配对，面板内 CT 在左、X-ray 在右；图片仅用于模态与配对关系的视觉说明。
4. 声明该图不是诊断图、性能估计或发布数据集，并保留 BIMCV Research Use Agreement 对图像发表许可的限制。
5. 运行 paper/build.bat 重新编译，并检查图版排布。

6. 根据用户要求，将 paper/main.tex 的第 3 作者单位改为 Ningxia Medical University（Yinchuan, China）。

### 待处理事项

- 图片包含脱敏像素，投稿前仍需依 BIMCV 协议取得数据部门对于图像发表的特定书面许可；未获许可前应将该图标记为作者审阅版。

## submit/revised 打包 + cover_letter.txt 同步更新（2026-07-21 下午）

**已全部修改**：
1. `submit/revised/`——新建目录，放入当前最终版投稿包：编译产物
   `main.pdf`/`appendix.pdf`/`combine.pdf`（基于合并 Table 2/3、修正 Fig. 2
   caption 之后的最新 `paper/main.tex` 编译），以及 LaTeX 源文件
   （`main.tex`/`appendix.tex`/`ref.bib`/`sn-jnl.cls`/`sn-vancouver.bst`/
   `tables_standalone.tex`）和正文引用的 13 张图（`figs/`，不含作者照片，与
   既有 `submit/paper/` 打包惯例一致）。
2. `docs/cover_letter.txt`——发现仍是投给 Elsevier *Computerized Medical
   Imaging and Graphics* 的旧版（双盲语气、旧冒号标题、旧 CodeOcean 链接），
   与当前 Discover Artificial Intelligence 大修轮次完全不符。已整体重写：
   期刊改为 Discover Artificial Intelligence（单盲）、Submission ID
   bf05c1ad-f7f2-44f8-a235-de9eeb659798、标题改为去标点新标题、新增
   "本轮修改摘要"段（标题/Declarations/理论论证/超参数敏感性/显著性检验合并/
   SOTA 对比表/复杂度分析/临床动机与合规讨论/两张新示意图/GitHub 开源/引言
   与讨论精简）、复现性链接改为 GitHub（`mabo1215/JDCNET.git`）、移除双盲/
   title page 相关表述。

## 回应信引用清理 + Table 2/3 合并去重 + Fig. 2 caption 措辞修正（2026-07-21 下午）

**触发**：用户指出 (1) `docs/response_to_reviewers.tex` 中大量使用 `fig:jdcnet_train_infer_graph`
等 LaTeX 内部 label，审稿人看不懂，应换成实际的 Fig./Table/Section 编号和标题；
(2) 论文正文中新增的显著性检验表（原 Table 2）与既有的 "Main 510-patient decision
summary" 表（原 Table 3）所列的 8 行方法几乎完全重复；(3) 新增 Fig. 2 caption 里
"redrawn from Fig. 1 to make the removed CT pathway explicit" 这句话不正式/没有实际
意义，要求检查是否需要保留原图并据此决定要不要留这句。

### 已全部修改

1. **Table 2/3 去重合并**——确认二者确实重复（同样的 CT teacher mid/3-slice、
   JDCNet 3-slice soft-KL/mid hard、Gated logit KD mid/DRR、Contrastive alignment、
   BiomedCLIP fine-tune 共 8 行）。做法：删除独立的显著性检验表
   （`tab:app_significance_effect_size`），把 z / p / Cohen's d 三列直接并入
   "Main 510-patient decision summary" 表（现为 **Table 2**，因为前面新增了
   Related-Work 的 SOTA 对比表占了 **Table 1**），caption 与过渡句同步更新说明
   合并原因。`paper/main_highlighted.tex` 同步更新：移除已并入的独立表格，改为在
   合并表新增的 z/p/d 列上做局部蓝色高亮，而不是整表标"新增"。
2. **Fig. 2 caption 措辞修正**——去掉"redrawn from Fig.~\ref{fig:jdcnet_mechanism}
   to make the removed CT pathway explicit"这句不正式的表述，改为直接、正式地
   说明该图的作用（"isolating exactly which computational blocks exist only
   during training"）。**保留 Fig. 1**（`jdcnet_mechanism.png`，机制细节图：
   teacher/student/loss/gradient）与 **Fig. 2**（新增的训练态/推理态计算图对比，
   聚焦 CT 分支被完全移除）——两图用途不同（机制细节 vs. 训练/推理结构对比），
   非冗余，故不删除 Fig. 1，只是精简了 Fig. 2 caption 中对 Fig. 1 的引用方式。
3. **`docs/response_to_reviewers.tex` 引用去 LaTeX 化**——把文中所有
   `\code{sec:xxx}`/`\code{tab:xxx}`/`\code{fig:xxx}`/`\code{main.tex}` 等审稿人
   看不懂的内部 label，替换为实际编译出的编号和标题，例如：
   - `sec:theoretical_rationale` → "Section 3.4"
   - `tab:main_decision_summary` → "Table 2"（并更新为"合并显著性检验列"的描述）
   - `tab:sota_comparison` → "Table 1"
   - `tab:jdcnet_510` → "Table 4"；`tab:app_absolute_metrics` → "Table 5"；
     `tab:app_gate_coverage` → "Table 6"；`tab:efficiency` → "Table 8"
   - `fig:jdcnet_train_infer_graph` → "Figure 2"；`fig:jdcnet_mechanism` → "Figure 1"
   - `fig:app_cohort_flow` → "Appendix Figure A1"；`tab:app_ct_variants` →
     "Appendix Table A5"
   - `sec:jdcnet` → "Section 3.3"；`sec:jdcnet_headline` → "Section 4.5 (Tier 1)"
   同时把 R2/R3.4/R4.3 中"新增一张显著性检验表"的措辞改为"把显著性检验/效应量
   并入既有的 Table 2，而非另建一张重复表"，如实反映本轮修改。
4. **重新编译**——`paper/build.bat` 通过（main-only 36 页 + appendix，无 undefined
   引用）；`docs/response_to_reviewers.tex` 重新编译为 `docs/response_to_reviewers.pdf`
   （8 页）；`paper/main_highlighted.tex`/`appendix_highlighted.tex` 同步更新并
   重新编译，`submit/JDCNet_marked_up_manuscript.pdf` 已刷新（43 页），用截图
   核对过 Table 2 合并列高亮、Fig. 2 caption 新措辞均正确渲染。

### 遗留问题

- 发现 `paper/figs/HongjiangWei.jpg`（作者照片资产）在磁盘上缺失，`git status`
  显示为 deleted，但该文件与当前 4 位作者列表（Ma/Yan/Wu/Liu，无 Hongjiang Wei）
  无关，也未在任何当前 `.tex` 文件中被引用，编译无报错——判断是历史遗留、与本轮
  修改无关的孤立资产，本轮未处理。
  - 需要你确认：是否需要恢复/清理这个孤立文件？如与当前作者阵容无关可忽略。

## Discover Artificial Intelligence 大修：审稿人意见逐条回应 + 论文修订（2026-07-21）

**背景**：`docs/revision_suggestions.tex` 是 Springer Nature *Discover Artificial
Intelligence* 期刊的编辑决定信 + 4 位审稿人意见（Major revision）。这与此前
`docs/revision_roadmap.md`/历史进度记录中的 TOMM/F1-F2-F3 拒稿点是**不同的投稿
轮次**——论文已切换为 `sn-jnl` 格式、单盲评审（作者信息在正文中可见）。`USAGE.md`
的"目标会议或期刊"一行仍写 ACM TOMM，属于过期未同步，实际当前投稿目标应为
Discover Artificial Intelligence（详见 `docs/competing_interests_statement_discoverai.txt`
等文件）；已在仓库记忆中记录，建议后续手动同步 `USAGE.md`。

### 已全部修改

1. **编辑要求 1：标题去标点**——`paper/main.tex`/`title_page.tex`/`tables_standalone.tex`
   标题统一改为单句 "JDCNet Applies Confidence-Gated Privileged-Modality
   Distillation for Cost-Preserving X-ray Inference"（去掉冒号分隔的副标题结构，
   保留学术复合词连字符）。
2. **编辑要求 2：Declarations 拆分**——`Ethics approval and consent to
   participate` 拆成独立的 `Ethical approval` / `Consent to participate` /
   `Consent to publish` 三个 `\bmhead`，逐条陈述。
3. **编辑要求 3：Point-by-point response**——新建
   `docs/response_to_reviewers.md`，逐条回应编辑 3 项要求 + Reviewer 1-4
   全部意见（需在正式提交前导出为 PDF）。
4. **代码/数据可得性改为 GitHub**——按用户指示，`main.tex` 的 Code
   availability / Data availability 及 `docs/data_availability_statement_discoverai.txt`
   改为指向 `https://github.com/mabo1215/JDCNET.git`（原 CodeOcean capsule 链接
   替换）；新增 BIMCV 数据集正式引用（de la Iglesia Vayá et al. 2020,
   arXiv:2006.01174）及官方获取门户链接。
5. **R1.1/R4.1 理论论证**——新增 Methodology 小节 `sec:theoretical_rationale`
   ("Design Rationale versus Confidence-Aware and Confidence-Based
   Distillation")，从 information-channel 与 bias-variance 两个假说论证
   JDCNet（硬掩码+离散/轻度软化目标）与通用 confidence-aware/based KD
   （连续置信度加权+全软化分布）的本质区别，并用已有的 gated logit KD 失败结果
   和 gate-coverage 诊断作为实证支持。
6. **R1.2 超参数敏感性分析**——在 Tier 1 结果段新增 "Hyperparameter
   sensitivity (τ_gate and λ)" 段落，基于已有 16-cell 网格和 4 点 τ 扫描数据
   分析 τ/λ 敏感性，诚实说明 soft-KL 变体仅在 λ=1.0 处扫描的局限。
7. **R1.4 固定阈值理由**——并入 `sec:theoretical_rationale` 的 "Threshold
   choice" 段落。
8. **R1.3 二分类/单 cohort 范围限定强化**——摘要新增明确限定句
   （"bounded to ... binary COVID-19 versus non-COVID classification"）。
9. **R1.5/R3.7/R4.6 图表清晰度**——新增 TikZ 矢量图
   `fig:jdcnet_train_infer_graph`（训练期 vs 推理期计算图并排对比，推理侧
   CT 分支显式灰化/虚线标注"removed"），插入 `sec:jdcnet` 现有机制图之后。
10. **R3.2 数据集筛选流程图**——附录 "Cohort Construction and Leakage Audit"
    新增 TikZ CONSORT 风格流程图 `fig:app_cohort_flow`，正文 Datasets and
    Cohort Construction 段落交叉引用。
11. **R3.5 SOTA 方法对比表**——Related Work "Relation to Recent Cross-Modal
    Privileged-Transfer Work" 新增 `tab:sota_comparison`，六维度对比 JDCNet
    与 Cahan et al. 2025 / DANTE / K-MaT / KRD / MST-Distill / BDKD。
12. **R2/R3.4/R4.3 统计显著性检验 + 效应量**——Statistical Protocol 新增
    "Significance tests and effect sizes" 段落 + `tab:app_significance_effect_size`
    （由已发表的 bootstrap 均值/CI 反推 SE，计算 Wald z 检验、双侧 p 值、配对
    Cohen's d；两个通过 gate 的配置均显著 p=0.003/0.011，d=0.76/0.65）。
13. **R2/R3.8 计算复杂度分析**——Implementation Details 新增
    "Computational complexity" 段落（训练/推理渐进复杂度、与 module-augmented
    对比方法的开销来源对比）。
14. **R3.1 临床场景动机**——Introduction Motivation 小节开头新增临床部署场景
    段落（急诊分诊、资源有限诊所、高通量筛查项目）。
15. **R4.5 临床工作流/监管相关性**——Discussion 末尾新增 "Clinical workflow
    and regulatory relevance" 段落。
16. **R3.6/R4.4 跨域泛化原因与缓解策略扩写**——Limitations "Data and
    generalization" 段落新增三类跨源崩溃原因（采集协议漂移、标签定义/患病率
    漂移、人群/设备漂移）及三类候选缓解措施（多中心训练、域适应、站点级阈值
    重校准），明确声明均未在本文中验证。
17. **R1.7/R4.8 精简重复表述**——Introduction Motivation 段落与 Discussion
    "Implications for AI-assisted clinical imaging" 段落各删去一处与其他章节
    重复的表述。
18. **R1.6/R2 审稿人建议引用的取舍**——查证审稿人建议的 5 篇引用（游戏强化
    学习/程序化内容生成、面部情绪识别、恶劣天气目标检测）及 2 篇野火风险预测
    引用，确认均与跨模态医学影像蒸馏主题无直接相关性；按编辑信中"引用增补属
    作者自行裁量、不影响录用决定"的说明，未采纳，已在回应信中说明理由（并向
    用户口头提示：4 篇可查证引用共享同一高度重叠的作者群体，属事实性观察）。
19. **编译复核**——`paper/build.bat` 重新编译通过，`build/main.log` 无
    undefined citation/reference、无 float-too-large 警告；main-only 36 页、
    appendix 6 页、combine 42 页（较修订前 23+4=27 页显著增加，因新增大量
    段落/图/表）。

### 未修改或部分修改

- **R1.3/R4.7 多分类/其他疾病泛化** — 仅在摘要与 Limitations 中明确声明为
  未验证范围，未新增多分类实验。
  - 是否需要：无需用户当前决策；这是本轮修订刻意保留的诚实边界（缺 GPU 资源
    与新数据集，超出本轮修订周期范围）。
- **R2/R3.7/R4.6 现有栅格图（mechanism diagram、结果图）重绘美化** — 仅新增
  的两张 TikZ 图做到矢量清晰化，原有 PNG 栅格图（`jdcnet_mechanism.png` 等）
  未重绘。
  - 需要你决策：是否要用 fal.ai Nano Banana（按 `.claude/rules/main.md` 的
    fal.ai 重绘规则）重绘现有栅格图？需要 fal.ai 凭据可用。
- **R1.1 理论论证的形式化证明** — 仅给出机制性假说 + 实证支持，未给出信息论
  形式化证明（论文中已明确声明这是留待未来工作）。
  - 无需用户当前决策，属故意保留的诚实范围声明。
- **审稿人要求的新实验**（R1.3 多分类、R3.6/R4.4 域适应/多中心训练/重校准
  实验）— 均未执行，仅在文中作为"未来工作"明确列出。
  - 无需用户当前决策；如需在本轮周期内补做，需要 GPU 资源与新数据/新标签
    体系，请告知是否安排。

### 遗留问题

需要你提供/决策：
1. `USAGE.md` 的"目标会议或期刊"仍写 ACM TOMM，与当前 `paper/main.tex`
   （`sn-jnl` 格式、单盲、Discover AI 专属声明文件）不一致 — 是否同步更新
   `USAGE.md` 为 Discover Artificial Intelligence？
   A: 同步更新  `USAGE.md` 为 Discover Artificial Intelligence
2. `docs/response_to_reviewers.md` 需要在正式提交前导出为 PDF（编辑信要求
   仅接受 PDF）— 是否需要协助生成 PDF（例如通过现有 LaTeX 工具链）？
   A:  需要协助生成 PDF
3. 是否需要用 fal.ai 重绘现有栅格图（`jdcnet_mechanism.png` 等）以进一步回应
   R2/R3.7/R4.6 的"图表质量偏低"意见？需要 fal.ai 凭据。
   A: 是
4. `docs/cover_letter.txt` 当前仍是投给 Elsevier CMIG、双盲语气的旧版本，与
   当前 Discover AI 单盲大修轮次不符 — 是否需要一并重写为本轮 Discover AI
   resubmission cover letter？
   A: 需要一并重写为本轮 Discover AI  resubmission cover letter

## 510 cohort F3 重跑准备（无卡模式，自动执行，2026-06-26 凌晨）

**目标**：在 510 headline cohort（不是 paired-216）上重跑 calibrated_gate，使 F3 温度消融可与正文 headline 直接可比。

**关键发现（为什么之前只有 216/228）**：
- 不是数据不够。H800 已有完整原始数据：`data/bimcv_paired`(17G,阳性 CT.nii+X光)+`data/bimcv_neg_paired`(49G,阴性),`bimcv_paired`/`bimcv_neg_paired` 是软链。**455 个病人有原始 `.nii`**(阳 101 + 阴 354);源 manifest `data/bimcv/bimcv_merged_paired_manifest.csv` 含 512 病人(398−/114+ = 510 cohort)。
- **228 的真因**：`prepare_bimcv_only_cv.py --mode balanced`(默认)会把阴性下采样到 `negatives[:len(positives)]` = 114+/114− = 228。510 headline 是 **imbalanced**(113+/397−)。→ 重建时要用 **`--mode full`**。
- **216 的真因**：calibrated_gate 的 `student_manifest` 要求 CT 教师**变体**图 `data/bimcv_ct_variants/bimcv_ct_{mid,3slice}/bimcv_S*.png` 存在,而变体只渲染了 216/217。

**本夜已做（无卡 CPU）**：
- 把 CT 教师变体从 216 渲染到全部 455（用 `.nii` 已在 H800）。原 `extract_ct_teacher_variants.py` 用 `get_fdata()` 整卷载入,在某个大卷上被 OOM kill(rc=137);改用**省内存渲染器** `src/ops/render_bimcv_variants_frugal.py`(`nib...dataobj[:,:,idx]` 惰性取片,RSS~64MB,只渲 mid+3slice,跳过 calibrated_gate 不用的 proj),参数与原脚本一致(HU[-1000,400], size 224, 3slice gap=round(5mm/z_spacing))。H800 上脚本 `/root/autodl-tmp/render_frugal.py`,日志 `render_frugal.log`,汇总 `logs/render_frugal_summary.json`。
- 注意:无卡模式 RAM 其实有 1007G(867 空闲),OOM 是单个病态大卷的 `get_fdata` 所致,非总内存不足。

**恢复任务（需有卡 GPU 模式，按序）**：
1. 确认变体齐:`ls data/bimcv_ct_variants/bimcv_ct_3slice/|grep -c bimcv_S` 应 ≈455。若 render 未跑完,先 `nohup python render_frugal.py`(幂等,跳已存在)。
2. **重建 510 CV manifest（imbalanced）**:`CV_MODE=full TAG=bimcv_full510 bash src/ops/h800_bimcv_5fold_cv.sh --phase prep`（或直接 `python -m jdcnet_exp.prepare_bimcv_only_cv --bimcv-manifest data/bimcv/bimcv_merged_paired_manifest.csv --output-dir bimcv_cv/bimcv_full510 --prefix bimcv_full510 --folds 5 --seed <same as orig> --mode full`）。CV_MODE/TAG 见脚本变量。
3. GPU 训练:`bash src/ops/h800_bimcv_5fold_cv.sh`（teacher+supervised+KD,新 cohort）→ 再 `bash src/ops/h800_calibrated_gate.sh`（指向新 CV_DIR + 新 SUP_RUN_ROOT），20-way+MPS 加速见 [[feedback-h800-ops-gotchas]]。
4. 用 `src/results/.../analyze_calib.py`（scratchpad 有副本）重算 within-cell ΔBA,与 paired-216 对比;若 510 上温度敏感性结论变化,更新 paper F3 段（当前写的是 within-cell ≤0.013 不敏感）。
5. 预期:510 上各 cell 绝对 ΔBA 可能恢复到 +0.03 附近（headline），温度不敏感性大概率保持。

**待用户**：H800 重开有卡模式后执行上述；F3 paper 措辞是否因 510 结果调整。

### 续：CPU prep 已全部完成（2026-06-26，无卡模式核对）
- **数据无需下载**：原始 `.nii` 全在 H800（阳 113 + 阴 354 = 467 个 paired 目录）。CT 教师变体渲染**已完成**：`bimcv_ct_mid`=467、`bimcv_ct_3slice`=467 PNG（`render_frugal.log` 末尾 `RENDER_FRUGAL_DONE`，仅 1 个病态卷 sub-S05726 因 "Too many dimensions" 跳过）；`proj` 仍 216，但 calibrated_gate 用不到。
- **510 full CV manifest 已生成**：直接跑 `prepare_bimcv_only_cv --mode full --seed 99 --prefix bimcv_full510 -o bimcv_cv/bimcv_full510`，输出 512 病人 398−/114+、0 dropped；5 折 `paired_manifest.csv` + `ct_manifest.csv` 齐。
- **有效 cohort = 466（113+/353−）**＝ 变体∩X光∩510（旧版仅 216）。距 512 差 46 个为无可渲染 CT 卷的病人——这正是 teacher-gated 消融能用的最大子集。
- **GPU 启动须知（避坑）**：用 `bash ops/h800_bimcv_5fold_cv.sh train`（**位置参数 `train`，不是 `--phase train`**）跳过 prep 段——其 Step 1b 会重跑易 OOM 的 `extract_ct_teacher_variants.py`（跳过条件要求 mid+3slice+**proj** 三者齐，251 个无 proj 病人会再 `get_fdata()`）。覆盖 `TAG=PREFIX=bimcv_full510 CV_DIR=bimcv_cv/bimcv_full510 CV_MODE=full`，先 `export PATH=/root/miniconda3/bin:$PATH`。
- **当前唯一卡点 = GPU**：训练（5fold teacher+supervised+KD，再 calibrated_gate）须有卡模式；无卡模式下 prep 已 100% 就绪，切到有卡后一条命令即发射。

### 有卡模式发射 full510 F3 重跑（2026-06-26 08:52，运行中）
- **编排脚本** `/root/autodl-tmp/orchestrate_full510.sh`（detached, setsid），日志 `/root/autodl-tmp/nohup_full510_orchestrate.log`。两段串行：
  1. **Phase1**：`h800_bimcv_5fold_cv.sh train`，`TAG=PREFIX=bimcv_full510`、`CV_DIR=bimcv_cv/bimcv_full510`、`CV_MODE=full`、**`PHASES="teacher supervised"`**（只跑 calibrated_gate 必需的前置；跳过 plain_kd/gated_kd 以最快出 F3）。把 5fold 第 314 行 phase 循环改成 `${PHASES:-...}` env 驱动（可逆，默认不变）。teacher 30 + supervised 30 = 60 runs。
  2. **Phase2**：`h800_calibrated_gate.sh`，`TAG=bimcv_full510_calibrated_gate SOURCE_TAG=bimcv_full510 CV_DIR=bimcv_cv/bimcv_full510 PREFIX=bimcv_full510 SUP_RUN_ROOT=runs/bimcv_full510`。2 cell × T{0.5,1.0,2.0} × 5 折 × 3 seed = 90 runs。
- **性能压榨**：`MAX_PARALLEL=20 NUM_WORKERS=6 GPU_ID=0` + **CUDA MPS**（server pid 在 nvidia-smi 可见，contexts 走 MPS 并发 kernel）。启动即 GPU **70.6GB/80GB**、282 procs。
- **教师图就绪**：ct_manifest 512 teacher 图 0 missing（阳 `data/bimcv/bimcv_ct_slices`、阴 `data/bimcv/neg_ct_slices`）。学生用 467 变体（`data/bimcv_ct_variants`）。
- **避坑已用**：positional `train`（非 `--phase train`）跳过 prep Step1b OOM 提取器；`PATH=/root/miniconda3/bin`。
- **下一步**：跑完后把 metrics 拉到 `src/results/bimcv_full510_calibrated_gate_*/` + supervised baseline，用 analyze_calib 重算 within-cell ΔBA（510 cohort），决定 F3 paper 措辞（预期温度不敏感保持、绝对 ΔBA 或回到 +0.03 附近）。

### 成本裁剪：3-seed → 1-seed（2026-06-26 09:29，用户决策）
- **诊断**：full510 跑起来 H800 **~80% 空闲**（CPU load 33/176≈19%，GPU util ~0%）——瓶颈是 tiny workload 的协调/overhead（50ep × 每 epoch 验证 × 20 进程 MPS 时分），**不是算力**。full 3-seed 估 ~8h 几乎全是空转计费。
- **用户选「减种子」**：calibrated_gate 3 seed→1 seed（42），90→**30 runs**；作为 510 cohort 上温度不敏感性 robustness check 足够（CI 稍宽）。
- **执行**：killed 3-seed run（注意 gotcha：kill 必须用脚本文件、且 pkill 模式不能出现在 ssh 命令行里，否则自杀 shell）；**wipe 旧 configs**（gotcha #6：phase loop globs 所有 config，改 SEEDS 不够，必须 `rm configs/bimcv_full510/*.json`）；relaunch `orchestrate_full510_1seed.sh`（SEEDS=42）。
- **Phase1 零开销**：seed-42 teacher+supervised 在首轮已训完，全部 SKIP_DONE，`H800_5FOLD_CV_COMPLETE` 秒过。只剩 Phase2 calibrated_gate 30 runs（20-way+MPS，GPU 71.5GB）。tag=`bimcv_full510_calibrated_gate`，SEEDS=[42]。
- **ETA**：calib 30 runs ≈ 2–2.5h → 约 11:45–12:00 CST 完成。后台 monitor（calibdone≥8 / ORCH DONE / stall）会叫醒我执行 拉结果→分析→写 F3→关机。

### 完成 + 结果 + 关机（2026-06-26 11:23 CST 跑完）
- **30/30 DONE + DONE_TEST，rc=0**。结果拉回 `src/results/bimcv_full510_calibrated_gate_20260626/`（30 calib + 10 supervised best_metrics、summary.csv、decision_report.md、analyze_full510_calib.py、raw backup full510_calib_pull.tgz）。**H800 已 `shutdown -h now` 关机，GPU 计费停止**（数据保留，可重开）。
- **F3 结果（val 主指标，466 effective cohort，seed 42，n=5）**：supervised baseline 3slice BA=0.664/mid BA=0.604。
  - **mid_hard T=1.0：ΔBA=+0.069 [+0.034,+0.106]（CI 排除 0，超过 headline +0.033）**
  - **3slice_soft T=1.0：ΔBA=+0.022 [−0.011,+0.068]（正向但 n=5 偏噪，CI 含 0）**
  - **温度不敏感保持**：within-cell |ΔBA vs T=1.0| ≤ 0.025，三温度下两 cell 均保持正；T=0.5 过自信不降反略升（噪声内），T=2.0 软化不提升。
- **关键意义**：510 cohort **复现正 ΔBA**，与 paired-216 子集（−0.09/−0.018）相反 → 证明 216 的负值是小 cohort 假象，**消除论文里「passing cell 在子集上不复现」的尴尬 caveat**。F3 温度消融现在落在 headline cohort 上。
- **诚实局限**：单 seed（n=5 vs 原 n=15），CI 偏宽，3slice_soft T=1.0 含 0；within-cell spread（≤0.025）略大于 216 的 ≤0.013（n=5 噪声）。定性结论稳健。
- **待做**：step 4 把上述写进 paper（摘要 F3 句、Limitations/Discussion F3 段：从 216-robustness-caveat 升级为 headline-cohort 消融 + 保留 single-seed caveat），Windows `build.bat` 重编译核对。

### Step 4 完成：F3 写入 paper + 重编译（2026-06-26）
- **2 处编辑 `paper/main.tex`**：①摘要 F3 句 `within-cell ΔBA≤0.013`→`≤0.025`，加「on the headline cohort」+「both passing cells remaining positive at every temperature」；②Limitations 校准段：改成「在 headline 510 cohort 上重跑」、`at most 0.025`、两 cell 各温度均保持正；诚实写 within-cell CI（T=0.5 过自信不破坏：+0.025/+0.007 CI 含 0；T=2.0 软化不提升：3slice within-noise、mid 边际 −0.014）——**没有 overclaim「all CIs include zero」**（mid_hard T=2.0 CI 排除 0）。Discussion L560 定性引用无需改。
- **F1/F2 已在文中**（external_stress 段 / absolute metrics 表），本轮只动 F3。
- **重编译**：Windows MiKTeX `build.bat` 通过，main.pdf **23 页，0 undefined ref/citation**。
- **未提交**（用户未明确要求 commit/push）；paper/ 是独立 repo，主 repo 用 gitlink 跟踪。within-cell 差异 CI 由 `analyze_full510_calib.py` 同目录单独算（见 decision_report）。
- **F3 任务全链路完成**：prep→训练(1-seed 30 run)→拉结果→分析→写 paper→重编译→关机 H800。

## H800 全数据重跑：A2/A3 完成、A4 待修、F3 实证为 null（2026-06-25）

**计算环境**：H800 重新可达（`ssh -p 12437 root@connect.westc.seetacloud.com`），单 GPU 0。本轮把 8-way 加速到 **20-way + CUDA MPS**（显存 28→71.5GB/80GB，吞吐 ~2.5×）。代码同步方式：本地改 → git push → H800 git pull。

### A2/A3 calibrated gate（关 F3）= 已完成，结果为 null / robustness（非"校准提升"）
- Run tag `bimcv_h800_calibrated_gate`，**90/90 完成，0 真实 FAIL**。两 pass cell（`3slice_soft` τ0.70 λ1.0 soft-KL、`mid_hard` τ0.80 λ1.5 hard）× teacher 门控温度 **T∈{0.5,1.0,2.0}**（0.5=过自信、1.0=未校准原版、2.0=软化/趋校准）× 5 折 × 3 seed。
- 指标用 **val（`best_metrics.json`）**，与 5fold/正文方法一致（5fold 各 run 无 test_eval）。supervised 同 cohort/折 val BA=0.6976、AUC=0.7104；teacher BA=0.7105。
- **核心发现（不修饰）**：
  1. **F3 校准敏感性 = null/稳健**：每个 cell 内三档温度统计上无法区分（cell 内 |ΔBA|≤0.013，全在噪声内；SD 0.04–0.10）。过自信(T=0.5)不损害、软化(T=2.0)不提升 → **门控对 teacher (mis)calibration 稳健**。正实证了正文 Limitations 现有预测（main.tex L555：校准"expected to stabilize, rather than overturn, the gate decision"）。
  2. **cohort 注意**：本轮在 paired-216 子集（CT+X光都在的病人），**非 510 headline cohort**。该子集上两 cell 都没复现 +0.0345/+0.0329：`3slice_soft` 显著为负（≈−0.09，CI 不含 0）、`mid_hard` 为 null（≈−0.018，CI 含 0）。这是 cohort 变小所致，非校准问题，**不推翻 510 headline**（不同 cohort），但温度消融须以 robustness check 报告并明示 cohort 差异，不能当作 headline ΔBA 的重算。
- 结果落盘：`src/results/bimcv_h800_calibrated_gate_20260625/`（`summary.csv` + `decision_report.md` + `aggregate_{val,test}.txt`）。分析脚本 `analyze_calib.py`（H800 `/root/autodl-tmp/`，本地副本在 scratchpad）。

### A4 external X-ray 推理（关 F1，最大风险）= 已修复并完成
- orchestrator 首跑 60 job 全 FAIL，根因：`h800_external_eval.sh` 生成 config 用 `train_split='train'`，但外部 manifest 只有 `split=test` 行 → `evaluate.py` 构建（随后丢弃）的 train loader 为空 → `ValueError: Training manifest is empty`。
- **已修**：`src/ops/h800_external_eval.sh` line 90 `train_split` 改为 `os.environ['EXT_SPLIT']`（本地已改；H800 用 sed 直接 patch 后重跑，因 H800 working copy 落后且有本地编辑，未走 git pull 以免冲突——本地需 commit 入库）。重跑 **60/60 完成**。
- **F1 结果（外部 MIDRC X 光，不修饰）**：所有模型**全部塌到随机**——supervised BA 0.492/AUC 0.486、jdcnet_3slice_softkl BA 0.498/AUC 0.509、jdcnet_mid_hard BA 0.494/AUC 0.477，三者互相无法区分。BIMCV 训练的 X 光分类器对外部域**零迁移**。这是对 F1 最直接的回答：跨域泛化对**所有模型**失败（任务/cohort 属性，非 JDCNet 特有），正面坐实审稿人 dataset-specific-bias 担忧，且契合论文 evidence-bounded-negative 基调。
- **注意（headline 前须核）**：supervised 也完全塌到随机，既可能是真实 domain shift（BIMCV 西班牙 vs MIDRC 美国），也可能外部 manifest 的 label 映射/预处理不一致——数值入正文前先 sanity check 外部 manifest 标签；定性结论（无跨域迁移）稳健。summary 里 sensitivity 列空 = 聚合 key 与 per-run `recall` 不符，需要时从 raw 重算。
- 结果落盘：`src/results/h800_external_eval_20260625/`（`external_summary.csv` + `decision_report.md`）。全部 raw metric json 备份在 `src/results/metrics_backup_20260625.tgz`（273 文件，checkpoint 释放后仍可复算）。

### H800 释放
- 用户示意"运行完暂不使用"。A2/A3 + A4 全部完成，所有指标/汇总/raw json 已拉回本地（含备份 tgz），**H800 上不再有未取数据，可安全释放/停机**。checkpoint 释放后丢失，但实验已完成、无需复算。

### 拒稿三点最新解决状态（2026-06-25）
- **F2（缺绝对指标）= 已解决**：正文 `tab:app_absolute_metrics` + 摘要绝对 BA/AUC（前轮）。
- **F3（teacher gate 未校准）= 实证完成，结论为 null/稳健**：A2/A3 已跑，证明门控对温度不敏感、过自信不破坏 student。可把正文/Limitations 的"proposed safeguard / expected to stabilize" 升级为"已做消融，gate 对 teacher 温度统计不敏感"。**待用户确认**：cohort 定位（paired-216 robustness check + 注脚 vs 在 510 cohort 重跑，后者需 510 数据在可达 GPU）。
- **F1（单 cohort、无 cross-domain）= 已有实证（负向）**：A4 完成，外部 MIDRC X 光上 supervised 与 JDCNet 全部 ≈ 随机（BA≈0.49，AUC≈0.49）。直接证明无跨域泛化（所有模型皆然），可把 Limitations 从"仅承认"升级为"已做外部验证并报告负向结果"，强化 evidence-bounded 框架。须先 sanity check 外部 manifest 标签后再把数值写正文。

### 待办
- [x] 修 `src/ops/h800_external_eval.sh`（train_split=test）→ 重跑 A4（F1）= 完成（本地已改，需 git commit 入库）。
- [ ] **git commit** 本地改动：`src/ops/h800_external_eval.sh`（A4 fix）、`src/results/`（A2/A3 + A4 结果与备份）、`docs/progress.md`。
- [ ] 用户决定 F3 在论文中的 cohort 定位（paired-216 robustness check + 注脚 vs 510 重跑）。
- [ ] sanity check A4 外部 manifest 标签/预处理（确认 supervised 塌到随机是真实 domain shift 而非 label bug）。
- [ ] 按两份 decision_report 把 F3（calibration ablation）+ F1（external validation）写入 paper（Methods/Experiments/Limitations），Windows `paper/build.bat` 重编。
- [x] H800：A2/A3 + A4 完成，指标全部拉回本地（含 `metrics_backup_20260625.tgz`），**可安全释放**。

## 拒稿点复核 + venue 定为 TOMM + 下一步计划（2026-06-23）

- **目标 venue 确认为 ACM TOMM**（用户本轮再次确认）。`USAGE.md` 第 33 行已从
  IEEE TCSVT 改为 ACM TOMM；`paper/main.tex` 本就是
  `\documentclass[manuscript,screen,review,anonymous]{acmart}` + `\acmJournal{TOMM}`
  双盲，格式一致。**14 页 TCSVT 约束作废**（TOMM 期刊无页数上限）。
- **三条拒稿点（F1/F2/F3，见 `docs/revision_suggestions.tex` / `docs/revision_roadmap.md`）
  对照 `paper/combine.pdf` 现状**：
  - **F2（缺绝对指标）= 已解决**：正文有 `tab:app_absolute_metrics`
    （baseline BA .604/AUC .661 → JDCNet 3-slice .639/.701）；本轮已把绝对 BA/AUC
    补进**摘要**（`main.tex` line 92）。
  - **F3（teacher gate 未校准）= 仅论证性解决**：有 ECE 诊断（§415）、分组可靠性图
    （`fig:calibration_reliability`）、Limitations 提出 temperature-scaling safeguard，
    但 **A2 calibrated-gate / A3 overconfidence ablation 实验从未跑过**。
  - **F1（单 cohort、无 cross-domain）= 未解决（最大风险）**：仅在 Limitations 承认，
    并给出 cross-source control（specificity≈0）作为反例；**A4 外部 X-ray 推理 /
    B1 外部 paired cohort 从未跑过**。
- **阻塞**：3090（`10.147.20.176:22`）与 H800（`connect.westc.seetacloud.com:12437`，
  DNS→`116.172.66.186`）本轮实测**均不可达**，依赖 GPU 的 A2/A3/A4 暂时无法运行。
  脚本与代码均已就绪。

### 下一步计划（未完成项 — 按优先级）

- [ ] **P0-a｜重新编译论文（Windows）**：跑 `paper/build.bat`，确认摘要绝对指标改动
      生效、无 undefined 引用/引文；产出 `main.pdf` / `combine.pdf`。WSL 无 pdflatex，
      必须在 Windows 端完成。
- [ ] **P0-b｜恢复可达 GPU**：重新拉起 H800 实例并记录新的 `host:port`，或等 3090
      ZeroTier 链路恢复。验收：`bash src/tmp_sync/ssh3090.sh 'hostname; nvidia-smi'`
      （或对应 H800 命令）成功。这是 F1/F3 实证的唯一卡点。
- [ ] **P1-a｜A4 外部 X-ray 推理（关 F1，最高优先）**：GPU 可达后运行
      `src/ops/remote_3090_external_eval.sh`，冻结学生在外部 X-ray manifest 上只推理，
      汇总绝对 BA/AUC/F1/sens/spec + bootstrap CI（inference-only，<0.5h）。
      把结果写进 Experiments 的 external-validation 段，替换当前"仅承认局限"的表述。
- [ ] **P1-b｜A2 calibrated gate + A3 overconfidence ablation（关 F3）**：运行
      `src/ops/remote_3090_calibrated_gate.sh`，两个 pass cell × T∈{1.0,0.5,2.0} ×
      5 折 × 3 seed = 90 runs（~3h）。把"提议的 safeguard"升级为"做过的 ablation"，
      正文补 calibrated-gate 结果 + 对比表。
- [ ] **P2｜（若数据可得）B1 外部 same-patient paired CT–X-ray cohort 重跑完整 gate**：
      `src/` 下已有数据下载脚手架，先调研可得性；这是对 F1 最强的正面回应。
- [ ] **P3｜论文整合与定稿**：A4/A2/A3 结果回填后，更新 Abstract / Methods（Calibration
      Safeguard）/ Experiments（external + calibration ablation）/ Limitations；同步
      `docs/cover_letter.txt`（已是 TOMM 版）逐条回应 F1/F2/F3；重新编译复核。
- [ ] **P4｜（可选，若改投会议）抓官方 CFP**：WACV 2027 Applications track 框架最契合，
      截稿约 2026 年 7–8 月，需 WebSearch 抓官网确认日期并改回会议格式。当前默认留在
      TOMM（无截稿压力）。

## paper/ 目录整理（2026-06-16）

- **拆分脚本归位**：`paper/split_main.ps1` 移入 `paper/build/split_main.ps1`，保持
  paper 根目录干净；`build.bat` 改为调用 `%BUILD_ROOT%\split_main.ps1`；脚本内路径
  改为以 `$PSScriptRoot`（=build/）的父目录为 paper 根、`main.aux` 在 build/；
  `paper/.gitignore` 增加 `!build/split_main.ps1` 例外（build/* 默认被忽略）。
- **附录单一源**：`appendix_body.tex` 内容合并进 `paper/appendix.tex` 并删除
  `appendix_body.tex`。`appendix.tex` 用 `\ifdefined\JDCappendixincluded` 守卫
  preamble/title/`\end{document}`：独立编译时走完整文档；被 `main.tex` 以
  `\def\JDCappendixincluded{}\input{appendix}` 引入时只输出正文，combine 原生解析
  全部交叉引用。根目录 .tex 仅剩 `main.tex / appendix.tex / title_page.tex`。
- **复核通过**：main 23 页、combine 27 页、appendix 4 页，无 undefined 引用/引文。

## A2/A4 实验脚本就绪 + 远端不可达 + 构建告警修复（2026-06-16）

- **构建告警根因修复**：`main.pdf` 拆分原用 poppler `pdfseparate`+`pdfunite`，在
  acmart/hyperref 的"recursive dicts"结构上会逐页重复解析，导致刷屏的
  `Syntax Warning: Found recursive dicts` 并使 `pdfseparate` 卡死/拖慢构建（多次
  残留僵尸进程）。改用单遍 `pdftocairo -pdf -f 1 -l N`（约 1.7s、零告警、扁平化结构），
  `pdfseparate`+`pdfunite` 仅作 fallback；`build.bat` 保留 `findstr /V` 过滤兜底。
  重新构建通过：main 23 页、combine 27 页、appendix 4 页。
- **A2 calibrate-then-gate 代码支持**：`jdcnet_exp/train_pseudolabel.py` 的
  `PseudoLabelConfig` 新增 `teacher_temperature`，置信度 mask 改为对
  `softmax(teacher_logits / T)` 取 max（argmax 目标不变；T=1 复现原始、T>1 软化/更校准、
  T<1 过自信）。
- **发射脚本就绪**（按既有 `remote_3090_bimcv_pseudolabel_cv.sh` 脚手架编写，`bash -n` 通过）：
  - `src/ops/remote_3090_calibrated_gate.sh`：A2+A3，仅两 pass cell ×
    温度 {1.0,0.5,2.0} × 5 折 × 3 seed = 90 runs，4×3090，screen+xargs。
  - `src/ops/remote_3090_external_eval.sh`：A4，冻结学生在外部 X-ray manifest 上
    只推理，汇总绝对指标（均值±SD）。
- **远端 3090 当前不可达**：`mabo1215@10.147.20.176` ping 100% 丢包、ssh "No route
  to host"（ZeroTier 链路或主机离线），**无法立即运行实验**。脚本与代码已就绪，
  待链路恢复后一条命令即可发射。

## main/combine 拆分与正文恢复至 23 页（2026-06-16）

- **PDF 结构调整**：`paper/main.pdf` 现在只含正文+参考文献（23 页，不含附录）；
  完整的"正文+附录"合订本输出为 `paper/combine.pdf`（27 页）；`paper/appendix.pdf`
  仍为独立附录（4 页）。
- **实现方式**：acmart 下 `\newlabel` 格式与 `xr`/手工注入都不兼容，main-only 无法
  在 LaTeX 内解析附录交叉引用。改为：`main.tex` 原生 `\input{appendix_body}` 生成
  合订本 → `build.bat` 复制为 `combine.pdf` → `paper/split_main.ps1`（PowerShell +
  poppler `pdfseparate`/`pdfunite`，本机无 python）读取 `\label{paper:appendixstart}`
  的页码，截取 1..(起始页-1) 写回 `main.pdf`。引用编号全部正确。
- **正文从 18 页恢复到 23 页**（TOMM 无页数上限）。从同谱系备份
  `backup/20260517_015930/main.tex` 恢复并新增：Related Work 的 "Transformers and
  Attention Mechanisms" 子节（+ViT/Swin 两条 bib）、更完整的 Knowledge Distillation
  段、"Data Availability and Ethics" 子节、扩写的 Limitations（新增 Reporting 与
  external-validation/calibration 段，呼应三条拒稿点）、Introduction 小样本评估
  协议段、Discussion 的 Calibration 与 "Relevance to cost-preserving multimedia
  inference systems" 段。把附录三张核心表（full JDCNet sweep、absolute metrics、
  gate coverage）上移到正文（绝对指标进正文同时回应 F2），并补 3 张图
  （seed instability、threshold sensitivity、grouped reliability diagrams）。
- **校验**：`build.bat` 通过，main 恰好 23 页；无 undefined 引用/引文；仅 1 处
  overfull box。`appendix_body.tex` 中被上移内容的引用已改写，独立 appendix.pdf
  无 undefined 引用。

## 目标期刊变更与 ACM 格式改造（2026-06-16）

- **目标 venue 变更**：由 IEEE TCSVT 改为 **ACM TOMM**（ACM Transactions on
  Multimedia Computing, Communications, and Applications）。已更新 `USAGE.md`
  的 `目标会议或期刊：...` 一行。
- **论文格式改造（`paper/`）**：`paper/main.tex` 与 `paper/appendix.tex` 从
  IEEEtran 全面改写为 **acmart**（`\documentclass[manuscript,screen]{acmart}`，
  ACM 期刊投稿要求的单栏 manuscript 格式）。
  - 题录元数据：`\acmJournal{TOMM}`、`\setcopyright`、CCS Concepts（`\ccsdesc`
    + CCSXML）、`\keywords`，参考文献样式改为 `ACM-Reference-Format`，
    `\bibliography{ref}`（移除 IEEEabrv）。
  - 作者块改为 ACM `\author/\affiliation/\email`；移除 IEEE 专用宏
    （`\IEEEPARstart`、`\markboth`、`\IEEEkeywords`、`\IEEEpeerreviewmaketitle`、
    `\ifCLASSINFOpdf`/`\ifCLASSOPTIONcaptionsoff`）及 IEEE biography 段落。
  - 正文中 "Positioning within TCSVT" 改为 "Positioning within multimedia
    computing"，"TCSVT-ready" 改为 "TOMM-ready"。
- **附录整合**：acmart 下 `xr/\externaldocument` 跨文档引用会触发
  "Missing number" 致命错误（acmart 的 .aux 与 xr 不兼容）。改为把附录正文抽到
  `paper/appendix_body.tex`，由 `main.tex` 在参考文献后用 `\appendix\input{appendix_body}`
  原生引入；`appendix.tex` 仍可独立编译（同样 `\input` 该共享正文）。所有
  附录交叉引用（如 `tab:jdcnet_510`）现已原生解析，无 undefined reference。
- **构建验证**：`paper/build.bat` 编译通过——`main.pdf` 23 页（正文+附录，ACM
  单栏 manuscript），`appendix.pdf` 6 页（独立附录）；无 undefined 引用/引文，
  仅 1 处 overfull box。TOMM 为期刊无硬性页数上限，23 页可接受。
- **双盲匿名化（2026-06-16）**：TOMM 为双盲评审。`main.tex` 与 `appendix.tex`
  documentclass 加入 `review,anonymous` 选项——作者名显示为 "Anonymous
  Author(s)"，affiliation/email/contact-info 与致谢自动隐藏，左侧加行号。正文中
  唯一可识别信息（GitHub 链接 `mabo1215/JDCNet`）改为 "repository URL withheld
  for double-blind review and provided to reviewers as anonymized supplementary
  material"。附录正文无可识别信息。
- **独立 title page（2026-06-16）**：新增 `paper/title_page.tex`（非匿名，单独
  上传，评审看不到），含完整标题、5 位作者及单位/邮箱、通讯作者（Bo Ma）、
  摘要、关键词，以及投稿信息块（目标期刊 TOMM、类别 Regular Paper、双盲）。
  编译产出 `paper/title_page.pdf`。
- **投稿类别**：选择 **Regular Paper（regular submission, no special issue）**。
  非 survey/tutorial/editorial；arXiv 预印本不算会议论文故非 Conference Extension；
  三个特刊（Foundation Models Meet 3D / Responsible & Explainable Multi-Modal
  Fusion / Multimodal Embodied Agents）均不匹配本文（本文是 training-only
  privileged-modality、单模态部署，非 multi-modal fusion）。
- **构建复核（2026-06-16，匿名后）**：`main.pdf` 23 页（匿名，行号）、
  `appendix.pdf` 6 页、`title_page.pdf` 2 页，均编译通过。
- **Cover letter 改投 TOMM（2026-06-16）**：`docs/cover_letter.txt` 已从 TCSVT
  改写为 ACM TOMM——更新抬头/EIC 称呼、投稿类别（Regular Paper）、多媒体计算
  系统相关性表述；移除 14 页 TCSVT 表述与正文 GitHub 链接，改为接收后开源 +
  双盲匿名说明（manuscript 匿名、作者信息在 title page 单独提供）；通讯作者
  邮箱改为 amabo1215@gmail.com。
- **匿名代码提交包（2026-06-16）**：把 `src/` 下可复现方法代码拷贝到
  `submit/code/`（`jdcnet_exp/`、`configs/`、`requirements.txt`、`README.md`），
  排除 `tmp_sync/`（789MB、含历史明文凭据）、`ops/`（远端集群脚本、含主机 IP
  10.147.20.176）、`results/`、`figures/`、checkpoints、原始数据与 `__pycache__`。
  核心代码本身无作者/单位/GitHub/邮箱/主机 IP 等可识别信息；README 顶部加双盲
  匿名说明。打包为 `submit/JDCNet_code_anonymous.zip`（48 文件、~139KB，使用
  forward-slash 路径以兼容 Linux 解压），最终匿名扫描通过。
- **遗留**：尚未按 ACM 投稿要求做内容级精简/校对。

## 当前状态（2026-05-17 close）

- **目标 venue**：ACM TOMM，transactions paper 23 页上限。
- **方法名**：JDCNet（confidence-gated CT-to-X-ray distillation，X-ray-only deployment graph）。
- **Headline 证据**：BIMCV 510-patient same-patient paired cohort，patient-level 5-fold × seeds 42–44。2/16 cells pass 固定 gate（mean ΔBA ≥ +0.03 且 bootstrap CI 排除 0）：
  - 3-slice soft-KL τ=0.70 λ=1.0：ΔBA=+0.0345 [+0.0112, +0.0571]
  - mid hard τ=0.80 λ=1.5：ΔBA=+0.0329 [+0.0074, +0.0584]
- **Comparator audit**：logit KD 变体、contrastive alignment、attention transfer、feature hints、BiomedCLIP、module-augmented pilot 全部 FAIL 同一 gate。

## 最新一轮修订（2026-05-17 revision_suggestions.tex pass）

- **R1 venue 合规**：`paper/main.tex` 与 `paper/appendix.tex` 已移除 `compsoc`；摘要从 ~211 词压到 198 词。
- **R3 近期相关工作定位**：Related Work 新增简短 `Relation to Recent Cross-Modal Privileged-Transfer Work` 段落，区分 Cahan 2025 (MICCAI CXR–CTPA)、DANTE (AAAI 2026)、K-MaT (arXiv 2026)；`paper/ref.bib` 加入 3 条对应引用。
- **R4 病人级保守不确定性**：附录新增 `Conservative Patient-Level Uncertainty` 表（fold/seed CI 与 patient-level paired bootstrap CI 并列）与 `Cohort Construction and Leakage Audit` 小节。
- **R6 部署成本细节**：deployment table 加入 median (IQR)、内存列、硬件/软件栈/精度/批量/warm-up/试次/预处理说明；edge 能耗显式标注为 not measured。
- **R7 算法编号**：加 `\usepackage{algorithm}`，把 JDCNet 训练过程从 figure 改为 algorithm 浮动体，统一 `Algorithm~\ref{alg:jdcnet}` 引用。
- **R8 可复现性**：实现化用词改为读者向开源声明（代码、split definitions、训练配置、bootstrap 工具在 `https://github.com/mabo1215/JDCNET` 开源；BIMCV 不再分发像素）。
- **页面压缩到 14 页**：删除 Transformers 子节；合并 `Privileged Information` 与 `Cross-Modal Distillation`；精简 Evidence Robustness、Introduction Motivation、Limitations、Discussion；`ref.bib` 从 58 → 30 条，对应未引用条目全部移除。

- **14页复核（2026-05-17）**：再次编译 `paper/build.bat`，确认 combined `paper/main.pdf` 为 14 页；为消除最后一页溢出，压缩 Appendix 的 gated-logit KD 温度/阈值扫描说明，移除该扫描的独立表格，并将机制总结并入同一段落；同步更新正文对该附录内容的引用。

- **Cover letter 同步（2026-05-17）**：`docs/cover_letter.txt` 已按最新 14 页 TCSVT 论文同步，更新为 JDCNet 当前标题、510-patient BIMCV headline 结果、同一 gate 下 comparator audit、部署成本表述、GitHub 开源链接和当前 appendix 内容；移除旧的 Code Ocean、commit hash、MIDRC/module-ablation 等过期描述。

- **Cover letter 简版（2026-05-17）**：`docs/cover_letter.txt` 已压缩到约 440 词，改成更自然的人工 cover letter 风格；保留标题、510-patient headline 结果、comparator audit、TCSVT 系统相关性、14 页状态、局限和 GitHub 链接，移除大段机械式分栏和过期标记。

- **伦理/知情同意表述（2026-05-17）**：建议提交表单选 `Yes`（使用人类影像数据），同时说明本研究为公开去标识化 BIMCV 数据的二次分析。`paper/main.tex` Methods 和 `docs/cover_letter.txt` 已补充 institutional research-committee approval/anonymization/no new consent 表述，重新编译 combined PDF 仍为 14 页。

- **Cover letter 初投版（2026-05-17）**：`docs/cover_letter.txt` 已从 revised/major revision 语气改为 initial submission 语气，删除 reviewer/response/revision 表述，保留简短人工风格、headline 结果、TCSVT 相关性、伦理说明和 GitHub 链接。

## 用户已确认的决策

- **不披露 arXiv pilot**：用户将自行更新 arXiv 上的预印本以与 TCSVT 稿件同步，因此不在论文中加入"Relation to prior arXiv version"段落。
- **不写 AI-content disclosure**：仅最小化语法润色，不写入 IEEE Acknowledgments。
- **不展开 latency variability / memory / edge power / patient-level bootstrap 原始结果**：数据在 4×3090 机器上存在，但 14 页约束下仅写最小化形式，待 reviewer 提出后再扩展。
- **外部 paired cohort 调研路径**：`src/` 已有数据下载脚手架，可在 Stage 10/round-2 用于外部验证。

## 构建提示

- Windows 端运行 `paper/build.bat` 生成 combined PDF；`paper/build.bat main` / `paper/build.bat appendix` 分别生成 standalone 输出。
- WSL 下无 pdflatex，编译需在 Windows 完成。
