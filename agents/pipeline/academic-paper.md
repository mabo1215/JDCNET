# Academic Paper 阶段规则（LLM/VLM/ML/CV 领域特化）

> 覆盖 Pipeline Stage 6-7 + Stage 10/10'：论文规划、全文起草、基于评审意见修改
> 基于 `agents/pipeline/academic-paper/SKILL.md` v3.0 特化

---

## 领域范围

同 `deep-research.md`：LLM、VLM、ML、CV 方向，目标顶会顶刊。

---

## Stage 6 — 论文规划（Socratic）

### 加载规则

```
agents/pipeline/academic-paper/SKILL.md
agents/pipeline/academic-paper/agents/intake_agent.md
agents/pipeline/academic-paper/agents/structure_architect_agent.md
agents/pipeline/academic-paper/agents/socratic_mentor_agent.md
agents/pipeline/academic-paper/references/plan_mode_protocol.md
agents/pipeline/domain-venues.md
```

### Phase 0: 配置采集（领域特化）

Configuration Interview 须收集以下领域特化信息：

| 配置项 | 选项 | 默认值 |
|--------|------|--------|
| **论文类型** | Conference paper / Journal article / Workshop paper | Conference paper |
| **目标 Venue** | NeurIPS / ICML / ICLR / CVPR / ICCV / ECCV / ACL / EMNLP / TPAMI / IJCV / 其他 | 从 `USAGE.md` 读取 |
| **引用格式** | IEEE / NeurIPS style / ICML style / ACL style | 按目标 venue 自动选择 |
| **输出格式** | LaTeX（venue 模板） | LaTeX |
| **页数限制** | 按 venue 规定 | 见 `domain-venues.md` |
| **贡献类型** | 新方法 / 新理论 / 新 benchmark / 大规模实证 / Survey | 新方法 |
| **已有材料** | deep-research 产出 / 实验代码 / 初步结果 / 无 | — |

### 论文结构选择（领域特化）

| 贡献类型 | 推荐结构 | 典型章节 |
|---------|---------|---------|
| **新方法** | IMRaD 变体 | Abstract → Intro → Related Work → Method → Experiments → Conclusion |
| **新理论** | 理论论文 | Abstract → Intro → Preliminaries → Main Results → Proof → Experiments → Conclusion |
| **新 Benchmark** | Benchmark 论文 | Abstract → Intro → Related Benchmarks → Benchmark Design → Experiments → Analysis → Conclusion |
| **大规模实证** | Empirical Study | Abstract → Intro → Background → Experimental Setup → Results → Analysis → Discussion → Conclusion |
| **Survey** | 综述论文 | Abstract → Intro → Taxonomy → Detailed Survey → Open Problems → Conclusion |

### 大纲构建领域特化规则

1. **Introduction 必须回答的 4 个问题**：
   - 解决什么问题？为什么重要？
   - 现有方法有什么不足？（gap）
   - 我们的核心 insight / 方法是什么？
   - 主要结果和贡献是什么？（contributions list）

2. **Related Work 组织方式**：
   - 按问题/方法族分组，不按时间线排列
   - 每组最后一句总结"与我们方法的区别"
   - 避免仅列举论文名：必须讨论方法差异

3. **Method 必须有的元素**：
   - 问题形式化定义（notation）
   - 方法整体架构图（Figure 1 或 2）
   - 每个核心组件的动机和设计
   - 训练和推理流程

4. **Experiments 必须有的元素**（见 `domain-venues.md` 各领域详细要求）：
   - Benchmark + 评估指标
   - Strong baselines + 公平比较
   - Main results table
   - Ablation study
   - 效率对比（FLOPs / params / 推理速度）
   - 定性结果 / Visualization
   - Failure case analysis

### 输入/输出

| 项目 | 内容 |
|------|------|
| **输入** | `docs/innovation_graph.md` + `docs/directions.json` + `docs/deep_reads/` |
| **输出** | `docs/paper_plan.md` + `docs/intake_config.json` |
| **人工确认** | ✅ 确认大纲、论证链、目标 venue 后进入 Stage 7 |
| **副作用** | 将确定的目标 venue 写入 `USAGE.md` 的 `目标会议或期刊：...` 行 |

---

## Stage 7 — 全文起草

### 加载规则

```
agents/pipeline/academic-paper/SKILL.md
agents/pipeline/academic-paper/agents/literature_strategist_agent.md
agents/pipeline/academic-paper/agents/argument_builder_agent.md
agents/pipeline/academic-paper/agents/draft_writer_agent.md
agents/pipeline/academic-paper/agents/citation_compliance_agent.md
agents/pipeline/academic-paper/agents/abstract_bilingual_agent.md
agents/pipeline/academic-paper/agents/visualization_agent.md
agents/pipeline/academic-paper/references/anti_leakage_protocol.md
agents/pipeline/academic-paper/references/writing_quality_check.md
agents/pipeline/academic-paper/references/latex_template_reference.md
agents/pipeline/shared/runtime_resource_and_secrets.md
```

### 起草流程（领域特化）

```
Phase 1: RESEARCH      → [literature_strategist]      → 引用策略（可跳过，如已有 deep-research 产出）
Phase 2: ARCHITECTURE   → [structure_architect]        → 最终大纲 + Evidence Map
Phase 3: ARGUMENTATION  → [argument_builder]           → 论证链（Claim-Evidence-Reasoning）
Phase 4: DRAFTING       → [draft_writer]               → 逐章起草
Phase 5a: CITATIONS     → [citation_compliance]        → 引用合规
Phase 5b: ABSTRACT      → [abstract_bilingual]         → 双语摘要（如需要）
```

### 领域特化写作规则

#### 通用

1. **Anti-Leakage Protocol**：
   - 所有 claim 必须来自 session 材料（deep_reads/ 和 papers/）
   - 无法找到依据时标注 `[MATERIAL GAP]`，不得用 LLM 参数记忆填空
   - 实验数字必须来自实际运行结果，不得编造

2. **Writing Quality Check**：
   - 禁止 AI 典型用语："delve into", "crucial", "it is important to note", "plays a pivotal role"
   - 禁止 em dash 滥用（每页不超过 2 个）
   - 禁止开头虚话："In this section, we will discuss..."
   - 段落长度变化自然（2-8 句，非均匀 4-5 句）

3. **LaTeX 质量**：
   - 数学公式用 `\( \)` 或 `equation` 环境，不用 `$` 直接嵌入正文
   - 表格用 `booktabs`（\toprule, \midrule, \bottomrule）
   - 图表必须有 `\label{}` 和正文 `\ref{}`
   - 参考文献用 `.bib` 管理

#### LLM 论文特化

4. **模型描述必须包含**：参数量、训练数据规模、tokenizer 类型、context length
5. **训练细节必须包含**：optimizer、learning rate schedule、batch size、训练步数/epoch、GPU 类型和数量
6. **Benchmark 报告格式**：使用该 benchmark 社区公认的评估指标和报告格式
7. **安全性讨论**：如涉及开源模型，讨论潜在 misuse

#### VLM 论文特化

8. **跨模态对齐**：必须专门一节描述视觉-语言对齐机制
9. **多模态 Benchmark**：至少覆盖 2+ 多模态 benchmark（如 MMBench, SEED, LLaVA-Bench, POPE）
10. **Hallucination 评估**：必须包含幻觉评估（POPE, CHAIR, 或自定义评估）
11. **可视化样例**：必须展示多模态理解的定性结果

#### CV 论文特化

12. **可视化要求**：定性结果 figure 必须包含成功和失败案例
13. **标准 benchmark**：必须在领域标准 benchmark 上评测（如 COCO, ImageNet, ADE20K）
14. **效率报告**：必须报告 FPS/FLOPs/参数量
15. **消融实验**：每个贡献组件必须有对应的消融实验

#### ML 论文特化

16. **理论分析**：如有理论贡献，Main Results 在正文，完整证明在 Appendix
17. **统计显著性**：报告 mean ± std（至少 3 次运行），或置信区间
18. **复杂度分析**：必须分析时间/空间复杂度

### 仓库规则约束

- `paper/` 目录全英文
- 论文正文不得出现本地路径、脚本名、代码文件名
- 实验代码在 `src/` 实现，论文中以学术散文描述方法和结果
- 最终论文用图放 `paper/figs/`
- 使用目标 venue 的官方 LaTeX 模板

### 输入/输出

| 项目 | 内容 |
|------|------|
| **输入** | `docs/paper_plan.md` + `docs/intake_config.json` + `docs/deep_reads/` + `docs/innovation_graph.md` |
| **输出** | `paper/main.tex` + `paper/appendix.tex` + `paper/references.bib` + `paper/figs/` |

---

## Stage 10 / 10' — 基于评审意见修改

### 加载规则

```
agents/pipeline/academic-paper/SKILL.md            # revision 模式
agents/pipeline/academic-paper/agents/revision_coach_agent.md
agents/pipeline/academic-paper/agents/draft_writer_agent.md
agents/pipeline/academic-pipeline/references/score_trajectory_protocol.md
agents/pipeline/shared/runtime_resource_and_secrets.md
```

### 修改流程

```
读取 docs/progress.md（优先消费 ## 遗留问题 下的 A: 回答）
   ↓
将 A: 回答映射到 ## 未修改或部分修改 的对应条目
   ↓
已解决条目：移入 ## 已全部修改，并同步删除 ## 遗留问题 中对应问题块
   ↓
读取 docs/revision_suggestions.tex（含 % STAGE: 和 % RULES: 标注）
    ↓
按 Stage 分组修改项
    ↓
Stage 10 类修改：
  ├── 叙述改进 → draft_writer_agent 规则
  ├── 新实验 → src/ 实现 → paper/figs/ 出图
  ├── 引用修复 → citation_compliance_agent 规则
  └── 方法描述 → draft_writer_agent + structure_architect_agent
    ↓
对每项修改：生成 Response to Reviewers（R→A→C 格式）
    ↓
追踪各维度评分变动（Score Trajectory）
    ↓
同步 docs/progress.md（三段式强一致：已全部修改 / 未修改或部分修改 / 遗留问题）
```

### `docs/progress.md` 联动规则（Stage 10 强制）

1. 只把 `## 遗留问题` 下 `A: ...` 行当作作者已确认输入；无 `A:` 的问题视为待决策。
2. 每次 Stage 10 执行前先处理已回答的遗留问题，再处理 `revision_suggestions.tex`。
3. 某条目从 `## 未修改或部分修改` 转入 `## 已全部修改` 时，必须同步删除 `## 遗留问题` 的对应问题块。
4. 若条目仍未完成，必须在该条目下明确写出当前剩余问题，便于作者继续以 `A: ...` 回答。
5. 当本轮条目改动较大或争议项较多时，自动触发 Stage 9' 复核；复核通过后再进入 Stage 11。
6. 默认不进入 Stage 9，也不重写 `docs/revision_suggestions.tex`；Stage 10-13 循环的基线文件始终是当前 `docs/revision_suggestions.tex`。
7. 仅在以下任一条件成立时，才允许提议进入 Stage 9：
   - 现有评审意见明显过时或与当前稿件不一致。
   - `目标会议或期刊` 已变化，需要按新 venue 重新评审。
   - 作者希望做一轮全新独立评审（重置评审视角）。
   - `docs/revision_suggestions.tex` 可执行项基本清空，且 `docs/progress.md` 的 `## 未修改或部分修改` 也清空，仍希望生成新一轮评审意见。
8. 即使满足上述条件，也必须先在 `docs/progress.md` 的 `## 遗留问题` 发起“是否进入 Stage 9”的确认问题；仅当作者给出明确同意（如 `A: 是`）才进入 Stage 9。
9. 对 `## 未修改或部分修改` 下每个子问题，必须在其后单独一行维护推进状态，建议格式：`推进状态：进行中 | 已完成 | 失败待修复 | 等待作者输入`。
10. 当子问题属于“可继续推进但未阻塞”（例如 `src/` 实验运行中），优先执行运行状态巡检：检查日志、报错与产物路径，并更新该子问题的状态行与下一步动作。

### 领域特化修改重点

| Reviewer 常见意见类型 | 应对策略 |
|---------------------|---------|
| "缺少与 XXX 方法的对比" | 在 `src/` 中实现对比实验，结果加入 table |
| "Ablation 不够" | 补充 ablation，每个组件单独移除 |
| "缺少效率分析" | 补充 FLOPs/params/FPS 对比 table |
| "理论分析不够" | 在 appendix 中增加理论推导 |
| "可视化不足" | 增加 failure cases 和更多定性结果 |
| "Scaling 分析缺失" | 在不同模型大小/数据量下跑实验 |
| "Reproducibility 问题" | 检查训练细节是否完整，承诺开源代码 |
| "Safety/Ethics 讨论缺失" | 增加 Broader Impact / Limitations 讨论 |

### Response to Reviewers 格式

```latex
\textbf{R1.1}: [Reviewer's comment verbatim]

\textbf{Response}: [Our response]

\textbf{Changes}: [Specific changes made, with line/section references]
```

### 输入/输出

| 项目 | 内容 |
|------|------|
| **输入** | `paper/main.tex` + `docs/revision_suggestions.tex` + `docs/review_reports/` |
| **输出** | 更新的 `paper/main.tex` + `docs/response_to_reviewers.md` + `docs/score_trajectory.json` |
| **同步** | `docs/progress.md` 三段式更新 |

---

## 反模式

| # | 反模式 | 正确行为 |
|---|--------|---------|
| 1 | 用 AI 典型语言写论文 | 用领域专业词汇，避免 "delve", "crucial", "pivotal" |
| 2 | Introduction 没有 Contributions list | ML/CV 顶会论文 intro 结尾必须有 numbered contributions |
| 3 | Related Work 只列举不对比 | 每组方法最后一句必须说明与本工作的差异 |
| 4 | 实验只报告好的结果 | 必须包含 failure cases 和 limitation analysis |
| 5 | 编造实验数字 | Anti-Leakage：数字必须来自实际运行，否则标 [MATERIAL GAP] |
| 6 | 消融实验不完整 | 每个贡献组件必须有对应消融 |
| 7 | Reviewer 说什么都改 | 对不合理意见使用 REVIEWER_DISAGREE + 证据支撑 |
| 8 | Appendix 放不了的内容放正文 | 按 venue 页数限制严格控制正文内容 |
| 9 | 忽略正文-附录一致性 | 附录中的 notation 和正文必须一致 |
