# Academic Paper Reviewer 阶段规则（LLM/VLM/ML/CV 领域特化）

> 覆盖 Pipeline Stage 9 / 9'：同行评审与复核评审
> 基于 `agents/pipeline/academic-paper-reviewer/SKILL.md` v1.8 特化

---

## 领域范围

同 `deep-research.md`：LLM、VLM、ML、CV 方向，目标顶会顶刊。

---

## Stage 9 — 同行评审（5-Reviewer）

### 加载规则

```
agents/pipeline/academic-paper-reviewer/SKILL.md
agents/pipeline/academic-paper-reviewer/agents/field_analyst_agent.md
agents/pipeline/academic-paper-reviewer/agents/eic_agent.md
agents/pipeline/academic-paper-reviewer/agents/methodology_reviewer_agent.md
agents/pipeline/academic-paper-reviewer/agents/domain_reviewer_agent.md
agents/pipeline/academic-paper-reviewer/agents/perspective_reviewer_agent.md
agents/pipeline/academic-paper-reviewer/agents/devils_advocate_reviewer_agent.md
agents/pipeline/academic-paper-reviewer/agents/editorial_synthesizer_agent.md
agents/pipeline/academic-paper-reviewer/references/quality_rubrics.md
agents/pipeline/academic-paper-reviewer/references/review_criteria_framework.md
agents/pipeline/domain-venues.md
```

### Phase 0: 领域分析与 Reviewer 配置

`field_analyst_agent` 须根据论文内容动态配置 5 位评审人，对 LLM/VLM/ML/CV 领域特化配置如下：

#### LLM 论文 Reviewer 配置

| 角色 | 专长配置 | 关注重点 |
|------|---------|---------|
| **EIC** | 顶会 AC/SAC 经验（如 NeurIPS/ICML Area Chair） | Journal fit, significance, positioning vs recent LLM work |
| **R1 Methodology** | 大规模训练专家（分布式训练、优化、scaling法则） | 训练稳定性、scaling 分析、计算成本合理性、reproducibility |
| **R2 Domain** | LLM 核心研究者（预训练/微调/对齐/推理） | 与 GPT/Claude/LLaMA 等主流模型系列的差异、增量贡献 |
| **R3 Perspective** | 下游应用或安全性研究者 | 实际应用价值、safety/alignment 影响、跨领域推广 |
| **Devil's Advocate** | 挑战核心论点 | 见下方通用 DA 规则 |

#### VLM 论文 Reviewer 配置

| 角色 | 专长配置 | 关注重点 |
|------|---------|---------|
| **EIC** | 多模态领域 AC | 视觉-语言结合的创新性和完整性 |
| **R1 Methodology** | 多模态架构专家 | 跨模态对齐质量、训练策略、数据处理 pipeline |
| **R2 Domain** | VLM benchmark 专家 | Benchmark 覆盖度、与 GPT-4V/LLaVA/InternVL 比较、hallucination 评估 |
| **R3 Perspective** | 视觉理解或机器人应用研究者 | 视觉推理深度、实际部署场景、效率 |
| **Devil's Advocate** | 挑战核心论点 | 跨模态对齐是否真实有效、benchmark 选择是否 cherry-pick |

#### CV 论文 Reviewer 配置

| 角色 | 专长配置 | 关注重点 |
|------|---------|---------|
| **EIC** | CVPR/ICCV AC | 视觉理解/生成领域重要性和创新性 |
| **R1 Methodology** | 目标任务方法专家（检测/分割/生成/3D等） | 方法设计合理性、ablation 完整性、效率 |
| **R2 Domain** | 对应子领域专家 | 与最新 SOTA 的比较、benchmark 标准性、结果可信度 |
| **R3 Perspective** | 相邻领域或应用场景研究者 | 泛化性、部署可行性、跨领域推广 |
| **Devil's Advocate** | 挑战核心论点 | SOTA 提升是否来自 trick 而非核心方法 |

#### ML 论文 Reviewer 配置

| 角色 | 专长配置 | 关注重点 |
|------|---------|---------|
| **EIC** | ICML/NeurIPS AC | 理论和实验的平衡、长期 impact |
| **R1 Methodology** | 理论/优化专家 | 定理正确性、假设合理性、证明完整性 |
| **R2 Domain** | 对应 ML 子领域专家 | 与已有理论/方法的关系、增量贡献 |
| **R3 Perspective** | 应用 ML 或统计学家 | 实际意义、统计学规范、假设在实际中能否满足 |
| **Devil's Advocate** | 挑战核心论点 | 理论假设是否过于 restrictive |

### Phase 1: Venue 规格核实与合规评审（前置）

Stage 9 开始前**必须**执行以下 venue 规格核实：

1. 读取 `USAGE.md` 中 `目标会议或期刊：...` 一行
2. 按 `agents/pipeline/domain-venues.md` 的 **Venue 官网规格抓取协议** 抓取最新投稿规范
3. 在开始评审前，先确保生成 `paper/main.pdf` 与 `paper/appendix.pdf`；优先使用仓库现有 LaTeX 构建入口，若不存在则按当前论文工程的标准方式分别编译 `paper/main.tex` 与 `paper/appendix.tex`
4. 将 `paper/main.tex` + `paper/main.pdf` 视为同一篇论文的正文，将 `paper/appendix.tex` + `paper/appendix.pdf` 视为同一篇论文的附录；5 位 Reviewer 必须对“正文+附录”做联合整体评审，不得把 main 与 appendix 拆成两篇稿件分别判断
5. 将 venue 规格纳入评审范围，包括但不限于：

| 合规维度 | 评审内容 |
|---------|---------|
| **LaTeX 模板** | `\documentclass` / `\usepackage` 是否使用 venue 指定模板 |
| **页数限制** | 正文是否超出 venue 限制；引用/附录是否符合计入规则 |
| **双盲合规** | 是否存在自引泄露、致谢泄露、affiliation 泄露 |
| **Checklist** | venue 要求的 checklist 是否逐项填写 |
| **引用格式** | 是否符合 venue 引用风格（IEEE / APA / ACL 等） |

> Venue 合规问题应在评审报告中单独列为一个 section，不合规项标记为 **MUST FIX**。

### Phase 2: 评审维度（领域特化 0-100 评分）

| 维度 | 权重 | LLM/VLM/ML/CV 特化评估点 |
|------|------|------------------------|
| **Novelty** | 20% | Core insight 的原创性；不是简单组合现有方法；与 concurrent work 的差异 |
| **Methodology** | 25% | 方法设计合理性；理论分析（如有）的正确性；消融实验完整性 |
| **Experiments** | 25% | Benchmark 标准性和覆盖度；Baseline 公平性和强度；统计显著性；效率报告 |
| **Clarity** | 15% | 写作清晰度；Notation 一致性；图表质量和可读性 |
| **Significance** | 15% | 对该领域的贡献大小；实际应用价值；是否推动了 research frontier |

### 领域特化评审标准

#### 必查项（所有 ML/AI 论文）

| 检查项 | PASS 标准 | FAIL 信号 |
|--------|----------|----------|
| **Reproducibility** | 训练细节完整；代码提交或承诺开源 | 缺少 hyperparameter、无法复现 |
| **Fair Comparison** | 所有方法使用相同数据/compute/evaluation | 不公平的 baseline 设置 |
| **Statistical Rigor** | mean ± std（至少 3 次运行）；或置信区间 | 单次运行结果 |
| **Ablation** | 每个贡献组件有独立消融 | 缺少核心组件的消融 |
| **Limitations** | 有专门的 Limitations 讨论 | 完全不讨论局限性 |
| **Broader Impact** | 有社会影响讨论（NeurIPS 强制） | 忽略 safety/bias/misuse |

#### LLM 特化必查

| 检查项 | PASS 标准 |
|--------|----------|
| Scaling 分析 | 至少 2 个模型大小的对比 |
| 训练成本 | 报告 GPU hours 或 FLOPs |
| Tokenizer 说明 | 明确 tokenizer 类型和词表大小 |
| 数据质量 | 训练数据来源和处理流程透明 |

#### VLM 特化必查

| 检查项 | PASS 标准 |
|--------|----------|
| Hallucination 评估 | 至少一种 hallucination 评估方法 |
| 跨模态对齐验证 | attention map 或 probing 实验 |
| 多模态 Benchmark | ≥ 2 个标准多模态 benchmark |

#### CV 特化必查

| 检查项 | PASS 标准 |
|--------|----------|
| 可视化质量 | 成功 + 失败案例展示 |
| 推理效率 | FPS 或 FLOPs 报告 |
| 标准 Benchmark | 该任务的标准测试集 |
| 泛化测试 | 至少一个额外转移实验 |

### Devil's Advocate 领域特化攻击维度

| 攻击维度 | 具体检查 |
|---------|---------|
| **Novelty 挑战** | 是否是已有方法的简单组合？与 concurrent work 有何根本区别？ |
| **Scaling 挑战** | 方法在更大/更小规模下是否仍然有效？是否只在特定规模下有效？ |
| **Baseline 挑战** | Baseline 是否足够强？是否遗漏了重要的 recent baseline？ |
| **Cherry-pick 检测** | 是否只在有利的 benchmark 上报告结果？是否故意回避某些 metric？ |
| **数据泄露检测** | 训练集和测试集是否有重叠？预训练数据是否包含测试数据？ |
| **Ablation 漏洞** | 核心 insight 的贡献是否被 implementation detail 的 trick 掩盖？ |
| **泛化性挑战** | 方法是否过拟合于特定 benchmark / 数据分布 / 评估指标？ |

### Phase 3: Editorial Decision 标准（领域特化）

| 决定 | 条件 |
|------|------|
| **Accept** | Novelty ≥ 70, Methodology ≥ 75, Experiments ≥ 75, 无 CRITICAL issue, DA 无未解决 CRITICAL |
| **Minor Revision** | 总分 ≥ 65, 无 CRITICAL issue, DA 问题可通过补充实验解决 |
| **Major Revision** | 40 ≤ 总分 < 65, 有 MAJOR issue 但可修复, 核心 contribution 有价值 |
| **Reject** | 总分 < 40, 或有不可修复的 CRITICAL issue, 或核心 claim 不成立 |

### ⚠️ IRON RULES

1. **5 位 Reviewer 独立评审**，不互相参考
2. **Synthesizer 不得编造评审意见**，必须基于 Phase 1 的具体报告
3. **DA 发现 CRITICAL → 不可 Accept**
4. **READ-ONLY**：评审过程不得修改 `paper/` 中的任何文件

### 输入/输出

| 项目 | 内容 |
|------|------|
| **输入** | `paper/main.tex` + `paper/main.pdf` + `paper/appendix.tex` + `paper/appendix.pdf` + `docs/integrity_report_pre.md`（其中 main 为正文、appendix 为同一篇论文附录，需联合评审） |
| **输出** | `docs/review_reports/`（5 份）+ `docs/revision_suggestions.tex`（英文 LaTeX，含 % STAGE: 标注）+ `docs/revision_roadmap.md` |
| **人工确认** | ✅ 阅读评审报告，确认修改策略 |

### revision_suggestions.tex 自动标注

生成 `docs/revision_suggestions.tex` 时，必须先清空该文件的全部旧内容，再写入新的英文 LaTeX 评审结果；写入时自动为每个修改项添加 `% STAGE:` 和 `% RULES:` 标注：

```latex
% STAGE: 10 (revision)
% RULES: academic-paper/agents/draft_writer_agent.md
\subsection{R1.1: Strengthen problem statement}
...

% STAGE: 10 (revision) + src
% RULES: academic-paper/agents/argument_builder_agent.md
\subsection{R2.1: Add ablation for component X}
...
```

---

## Stage 9' — 复核评审

### 加载规则

```
agents/pipeline/academic-paper-reviewer/SKILL.md       # re-review 模式
agents/pipeline/academic-paper-reviewer/references/re_review_mode_protocol.md
```

### 复核流程

```
对照原 revision_roadmap.md 逐条检查：
  ├── 该修改是否在修改版中体现？
  ├── 修改是否到位（不是敷衍了事）？
  ├── 是否引入了新问题？
  └── 分项评分是否退步？
    ↓
输出 Verification Report（R&R Traceability Matrix）：
  ├── ADDRESSED：已到位
  ├── PARTIALLY_ADDRESSED：部分到位，补充建议
  ├── NOT_ADDRESSED：未修改
  └── NEW_ISSUE：修改引入的新问题
```

### 领域特化复核重点

| 原评审问题类型 | 复核标准 |
|--------------|---------|
| "补充实验" | 实验确实添加了？结果合理？写入论文了？ |
| "改写某节" | 文字确实改了？改后更清晰了？ |
| "补充 ablation" | ablation table 添加了？分析正确？ |
| "修复引用" | 引用已修复？BibTeX 条目完整？ |
| "效率对比" | 效率 table 添加了？对比公平？ |

### 输入/输出

| 项目 | 内容 |
|------|------|
| **输入** | 更新的 `paper/main.tex` + `docs/response_to_reviewers.md` + 原 `docs/review_reports/` |
| **输出** | `docs/re_review_report.md`（Traceability Matrix + 残留问题 + 新决定） |
| **人工确认** | ✅ 如有重大残留问题 → Stage 10'；否则 → Stage 11 |

---

## 评分标准速查（0-100）

| 分数 | 含义 | 对应 Venue 水平 |
|------|------|----------------|
| 90-100 | 顶级工作 | Best Paper 候选 |
| 80-89 | 优秀 | 强 Accept（Oral/Spotlight） |
| 70-79 | 好 | Accept（Poster） |
| 60-69 | 还行 | Borderline / Weak Accept |
| 50-59 | 不够 | Weak Reject |
| 40-49 | 较差 | Reject |
| 0-39 | 严重问题 | Strong Reject |

---

## 反模式

| # | 反模式 | 正确行为 |
|---|--------|---------|
| 1 | 给不够格的论文打高分 | 有方法论缺陷的论文 Methodology 分不可能 > 60 |
| 2 | 5 个 Reviewer 提出相同批评 | 每个 Reviewer 从不同角度评审，交叉 = 假多样性 |
| 3 | DA 找到 CRITICAL 但 Editorial 仍说 Accept | DA CRITICAL → 必须 Major Revision 或 Reject |
| 4 | 复核时橡皮图章 "all addressed" | 每个修改项必须独立验证 |
| 5 | 评审时直接修改论文 | READ-ONLY：只出报告，不碰论文 |
| 6 | 评审意见笼统无定位 | 必须引用论文具体段落/table/figure |
| 7 | 忽略 concurrent work | 必须检查近 6 个月有无高度类似的 arXiv preprint |
