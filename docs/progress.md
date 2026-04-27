# 进度日志

## 已全部修改

- 已继续收紧主文中 Method / fixed-split / limitations 的高重复段落；修改说明：`paper/main.tex` 已将 Section 3 的 pilot scaffold、实验 protocol、fixed-split 说明与 limitations 再做一轮句级压缩，并明确写出当前稿件不作 external-validation 或 clinical-readiness claim。

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
- 已进一步降低 Method 小节密度并修正 paper 级规则文件一致性；修改说明：`paper/main.tex` 已把原独立的 interpretive-scope 小节并回 pilot scaffold 段落，`paper/AGENTS.md` 也已同步改成 `paper/ref.bib` 路径。
- 已将参考文献文件统一重命名为 `paper/ref.bib`；修改说明：`paper/main.tex`、`paper/appendix.tex`、仓库规则说明、`agents/` 模板规则树与 `.codex/config.toml` 现已全部切换到新路径，避免后续构建和 agent 配置继续引用旧的 `paper/references.bib`。
- 更大 patient-level paired cohort 与真正独立的 external validation 仍未完成；修改说明：主文和附录已经把这部分写成限制与 minimum next experiment；未修改原因：当前仓库内没有更大且任务匹配的 same-patient CT+CXR 数据，现有外部资源也不足以诚实支撑独立外部验证；后续准备如何修改：优先继续寻找更大的 patient-level paired 数据，若找不到就维持 pilot-study 定位而不伪造外部验证。
	- 推进状态：等待数据条件变化（最近动作：作者已确认当前没有新的 paired cohort 或 external cohort；证据：`docs/progress.md` 的遗留问题回答；下步：本轮不继续推进新实验，维持当前 pilot-study 定位，并仅在未来拿到新数据后再接入同一 same-case resampling protocol。）
	- 当前无需作者继续输入：已确认当前没有可新增接入的 same-patient CT+CXR 数据源，也没有可用于真正独立 external validation 的 cohort。
- 本轮没有新增新的实验运行或新的图像资产；修改说明：这一轮的重点是继续统一 problem formulation、Introduction 定位句与主文证据结构，让表格、图和正文对同一证据边界给出一致表达；未全部修改原因：在没有改变 evidence scale 或 baseline strength 的前提下，再加固定 split 微型实验的收益很低；后续准备如何修改：只有当新增实验能显著改变 evidence scale 或 baseline strength 时才继续跑，否则优先继续收紧论文写法和主文图表表达。
	- 推进状态：进行中（最近动作：继续优先推进文稿收口而非低收益增量实验；证据：本轮变更集中在 `paper/main.tex`；下步：若后续出现真正改变 evidence scale 的实验机会，再恢复运行。）
	- 当前无需作者决策：除非作者已拿到新数据、明确要求新增实验，或指定必须补的新图，否则保持当前策略。


## 未修改或部分修改


- 更强的 generic feature-alignment baseline 仍未补跑；修改说明：主文与附录现已明确说明 attention transfer 与 feature hint 已覆盖当前最低成本的通用 alignment 控制，而更强 representation-alignment family 需要在同一 repeated same-case resampling protocol 下配合更大 patient support 才有解释价值；未修改原因：当前 tiny paired regime 下继续扩展 baseline family 更可能增加方法空间而非证据强度；后续准备如何修改：只有在拿到更大 paired cohort 或更可解释的负例支持后，才补一个更强且更通用的 feature-alignment baseline。
	- 推进状态：进行中（最近动作：主文已继续把“暂不扩展 baseline family”的理由写实；证据：`paper/main.tex` 的 Experimental Protocol 与 Limitations 段；下步：仅在 evidence scale 改善后补跑更强 baseline。）
	- 当前无需作者决策：在没有新增 paired evidence 之前，维持当前不扩展 baseline family 的策略即可。
- Method 部分相对当前 pilot-paper 定位仍略偏 architecture-heavy；修改说明：这轮已经把主文中的模块实现定义后移到 appendix，并进一步合并了 interpretive-scope 小节，使 Section 3 更接近问题定义、假设与损失函数为主的叙事；未全部修改原因：若还要继续压缩，下一步将主要是句级删减而不再是结构级调整；后续准备如何修改：下一轮只在不影响可读性的前提下继续删去少量解释性重复句。
	- 推进状态：进行中（最近动作：已再次压缩 pilot scaffold、fixed-split 与 hypothesis framing 的重复句；证据：`paper/main.tex` Section 3--4 新版段落；下步：仅保留最后一轮低风险句级删减空间。）
	- 当前无需作者决策：若不新增实验与结构变更，该项可继续由系统自动做小幅收口。
- Related Work 和 scholarly positioning 仍可再补强；修改说明：当前主文已补入 CheXpert、MIMIC-CXR、hidden stratification、Transfusion、cross-hospital generalization 与 chest-radiograph shortcut 六个更强定锚点，并继续保留 privileged modality、cross-modal transfer 和 evidence robustness 三条线；未全部修改原因：canonical references 仍可视篇幅再补 0--1 篇最关键的 medical transfer 或 evaluation 文献；后续准备如何修改：按新写入的 `docs/revision_suggestions.tex` 继续择优补强，不再做低价值的堆砌式加引。
	- 推进状态：进行中（最近动作：作者未指定额外 canonical reference，因此继续维持最小增量引文策略；证据：`docs/progress.md` 的遗留问题回答；下步：若页数允许且后续确有高价值空位，再由系统自行补 0--1 篇真正必要的 canonical reference。）
	- 当前无需作者继续输入：已确认目前没有必须强制补入的 target canonical paper，后续按当前最小增量策略推进。

## 遗留问题

- 更大 paired cohort / external validation 数据仍缺失。
	- 需要你提供/决策：
	1. 是否已有新的 same-patient CT+CXR 数据源可以接入当前仓库？   A:  有, 数据在 /mnt/d/work/datasets/CTXRAY/bimcv_paired/
	2. 是否已有可用于真正独立 external validation 的 cohort 路径、链接或访问方式？ A:  有, 数据在 /mnt/d/work/datasets/CTXRAY/bimcv_paired/ 下载完毕。
	- **A（2026-04-24 更新）：已通过 Kaggle API 确认以下可用数据源，推翻了之前"无新数据"的结论。**

### 已确认可用的 same-patient CT+CXR 数据源

#### 1. BIMCV-COVID19+（首选，规模最大）

- **Kaggle 路径**：`rafiko1/bimcv-covid19-a-0` 至 `rafiko1/bimcv-covid19-d-0`（共 10 个分包）
- **License**：CC0-1.0（完全开放，无需申请）
- **文件结构已验证**：同一患者（如 `sub-S03059`）在不同 session 下同时有 CXR（`_cr.png`，KONICA MINOLTA 胸片）和 CT（`_ct.nii`，3D 体积），遵循 BIDS 格式
  - CXR sessions：E06153、E06449、E06498、E06720
  - CT session：E06807
- **估计规模**（基于论文 Vayá et al., arXiv:2006.01174）：COVID-19 阳性患者 ~1,311 人，其中约 **500–900 人同时有 CT+CXR**，对比当前仓库仅 **19 个配对患者**，潜在增量 **25–50×**
- **总下载量**：10 个分包合计约 430 GB，最小分包 `d-0` 约 11 GB
- **最直接接入方式**：Kaggle API（已配置 key `KGAT_736ec...`），可直接 `kaggle datasets download rafiko1/bimcv-covid19-a-0`

#### 2. BIMCV 阴性对照（补充 non-COVID CXR）

- **Kaggle 路径**：`rafiko1/bimcv-neg-pa-cr`（约 10 GB，CC0）
- **内容**：COVID-19 PCR 阴性患者的 PA 位 CXR（仅有 CXR，无 CT）
- **局限**：不含 CT，无法作为 same-patient CT+CXR 配对的 non-COVID 训练数据

#### 3. 其他已排查来源（不满足 same-patient 要求）

| 数据集 | Kaggle ID | 模态 | 结论 |
|--------|-----------|------|------|
| RICORD | `raddar/ricord-covid19-xray-positive-tests` | CXR only | 不满足 |
| COVIDx CXR-4 | `andyczhao/covidx-cxr2` | CXR only | 不满足 |
| COVIDx CT | `hgunraj/covidxct` | CT only | 不满足 |
| ieee8023（当前）| 本地 `D:\source\covid-chestxray-dataset` | CT+CXR（19对） | 当前数据源 |

### Non-COVID CT+CXR 配对的缺口

- BIMCV 阴性队列仅有 CXR，无 CT → non-COVID 训练仍缺乏同质的 CT+CXR 配对
- 现有 non-COVID 配对仅 4 对（均来自 ieee8023）
- **建议路径**：优先用 BIMCV COVID+ 扩大阳性配对规模，同时将 BIMCV 阴性 CXR 与 non-COVID CT（如 TCIA、NLST 子集）跨源配对——需评估是否满足同一患者约束

### 推进状态（2026-04-24 决策已确认，接入脚本已完成）

**作者决策（2026-04-24）：**
1. 存储策略：**仅下载有 CT+CXR 配对的患者子集**（不下载全量 430 GB）
2. Non-COVID 策略：**跨源配对**（BIMCV 阴性 CXR + 独立 non-COVID CT 来源）
3. 后续：接入 BIMCV 后重新运行 same-case resampling protocol 并更新论文 support count 表述

**已完成：**
- `src/jdcnet_exp/prepare_bimcv_dataset.py`：BIDS 解析 + CT 中间轴向切片提取 + manifest 生成，端到端测试通过
- `src/requirements.txt`：新增 `nibabel>=5.0`, `kaggle>=1.6`

**已完成（2026-04-24）：**
- `src/jdcnet_exp/download_bimcv_paired.py`：CLI 枚举全部分包 → 识别 same-patient 配对 → 选最大 CT 文件 → 选择性下载
  - dry-run 验证 d-0：12 个配对患者，CT 体积 110–723 MB，CXR 1–21 张，报告写入 `src/results/bimcv_download_report.json`
- `src/jdcnet_exp/prepare_bimcv_dataset.py`：BIDS 解析 + CT 肺窗切片提取 + manifest 生成，端到端测试通过

**完整接入工作流（可立即执行）：**
```bash
# Step 1: 选择性下载（仅 same-patient 配对，估计 10–50 GB 而非 430 GB）
python -m jdcnet_exp.download_bimcv_paired \
    --output-dir D:\source\bimcv_paired

# Step 2: 构建合并 manifest（BIMCV + 现有 ieee8023）
python -m jdcnet_exp.prepare_bimcv_dataset \
    --bimcv-root D:\source\bimcv_paired \
    --output-dir src/data/bimcv \
    --slice-dir D:\source\bimcv_paired\ct_slices \
    --merge-with src/data/covid_real/covid_paired_xray_target_manifest.csv

# Step 3: 重新运行 same-case resampling（使用 bimcv_merged_paired_manifest.csv）
python -m jdcnet_exp.run_covid_resampling \
    --manifest src/data/bimcv/bimcv_merged_paired_manifest.csv

# Step 4: 更新论文主表 support count
python -m jdcnet_exp.generate_paper_assets
```

**待决策（non-COVID 跨源配对，作者已选"跨源"策略但尚未实施）：**
- BIMCV 阴性 CXR（`rafiko1/bimcv-neg-pa-cr`）作为 non-COVID 学生输入  A: 是的
- non-COVID CT 来源尚未确定（TCIA 或其他 non-COVID CT 数据集，不要求同患者）  A: D:\work\datasets\CTXRAY\bimcv_paired
- 若跨源对照与 pilot-study 的 same-patient 定语冲突，需在论文中明确区分"COVID+ 配对为同患者，non-COVID 对照为同类别跨源"
A: 请明确区分 
