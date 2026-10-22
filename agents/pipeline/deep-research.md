# Deep Research 阶段规则（LLM/VLM/ML/CV 领域特化）

> 覆盖 Pipeline Stage 0-5：方向探索、文献收集、逐篇精读、创新图谱、定向迭代扩展
> 基于 `agents/pipeline/deep-research/SKILL.md` v2.8 特化

---

## 领域范围

- 大模型（LLM）：GPT 系列、Claude 系列、LLaMA、Mistral、Qwen、DeepSeek 等开源/闭源大语言模型
- 视觉语言模型（VLM）：GPT-4V/4o、LLaVA、InternVL、Qwen-VL、CogVLM 等多模态模型
- 机器学习（ML）：优化、泛化理论、自监督学习、强化学习、图神经网络、联邦学习等
- 机器视觉（CV）：目标检测、语义分割、3D 视觉、视频理解、图像生成、NeRF/3DGS 等

---

## Stage 0 — 方向探索（苏格拉底对话）

### 加载规则

```
agents/pipeline/deep-research/SKILL.md          # 入口
agents/pipeline/deep-research/agents/socratic_mentor_agent.md   # 苏格拉底引导
agents/pipeline/deep-research/agents/research_question_agent.md # RQ 形成
agents/pipeline/deep-research/references/socratic_mode_protocol.md  # 对话协议
agents/pipeline/domain-venues.md     # 领域 venue 数据库
```

### 领域特化规则

1. **RQ 形成时须匹配顶会 scope**：
   - RQ 必须能对应到至少一个目标 venue（NeurIPS/ICML/ICLR/CVPR/ACL/TPAMI 等）
   - 如果 RQ 过于工程化（如"如何部署 LLM"），引导向学术化转化（如"在资源受限场景下 LLM 推理效率与质量的 Pareto 前沿分析"）

2. **苏格拉底引导须包含的领域探针**：
   - "你的工作主要是提出新方法、新理论、新 benchmark，还是对现有方法做深入分析？" → 确定贡献类型
   - "目标场景是通用的还是特定领域的？" → 确定 scope
   - "与 SOTA 相比，你的核心 insight 是什么？" → 确定 novelty
   - "你有多少 GPU/计算资源可用？" → 评估实验可行性（FINER-F）

3. **FINER 评分领域特化**：
   - **Feasible**：考虑 GPU 资源、数据可获得性、训练时间
   - **Interesting**：是否解决了社区公认的 pain point
   - **Novel**：是否有 concurrent work（arXiv 检查）
   - **Ethical**：大模型安全性、bias、隐私
   - **Relevant**：是否符合目标 venue 的 scope 和 trend

### 输入/输出

| 项目 | 内容 |
|------|------|
| **输入** | 研究者对感兴趣方向的描述 |
| **输出** | `docs/rq_brief.md` |
| **输出内容** | RQ、子问题、FINER 评分、scope 边界、关键词、目标 venue 初选、贡献类型 |
| **人工确认** | ✅ RQ + 目标 venue 确认后方可进入 Stage 1 |

---

## Stage 1 — 文献高召回收集

### 加载规则

```
agents/pipeline/deep-research/SKILL.md
agents/pipeline/deep-research/agents/bibliography_agent.md
agents/pipeline/deep-research/agents/source_verification_agent.md
agents/pipeline/deep-research/references/semantic_scholar_api_protocol.md
```

### 领域特化检索策略

1. **必检数据库**：
   - Semantic Scholar（API 优先）
   - arXiv（cs.CV, cs.CL, cs.LG, cs.AI, cs.MM）
   - OpenReview（ICLR/NeurIPS 全部公开评审）
   - Google Scholar（补充）
   - DBLP（会议论文索引）
   - Papers With Code（代码关联）

2. **时间窗口**：
   - 核心文献：近 2 年（2024-2026）
   - 开创性工作：不限时间（如 Attention Is All You Need, ResNet, BERT）
   - Concurrent work：近 6 个月 arXiv preprint 必查

3. **检索关键词策略**：
   - 使用 RQ 中的关键术语 + 同义词/变体
   - 必须包含方法名（如 "LoRA", "DPO", "RLHF", "SAM"）
   - 必须包含任务名（如 "visual grounding", "object detection", "text generation"）
   - 使用引用链追踪：找到核心论文后，追踪其引用和被引

4. **会议论文特殊处理**：
   - ICLR 论文同时拉取 OpenReview 的 reviewer scores、reviews、author response、decision
   - NeurIPS/ICML 论文检查是否有 oral/spotlight/poster 标记
   - CVPR/ICCV/ECCV 检查是否有 best paper 提名

5. **召回目标**：
   - 15-30 篇高度相关论文
   - 5-10 篇间接相关（可借鉴方法或思路）
   - 3-5 篇 concurrent work / 竞品

### 输入/输出

| 项目 | 内容 |
|------|------|
| **输入** | `docs/rq_brief.md` |
| **输出** | `docs/papers/` + `docs/collection_manifest.json` |
| **manifest 字段** | paper_id, title, authors, venue, year, doi, arxiv_id, openreview_id, pdf_path, status, relevance_score, has_code, code_url |
| **人工确认** | ✅ 确认文献库覆盖范围 |

---

## Stage 2 — 逐篇深度精读

### 加载规则

```
agents/pipeline/deep-research/SKILL.md
agents/pipeline/deep-research/agents/synthesis_agent.md
agents/pipeline/deep-research/agents/risk_of_bias_agent.md
```

### 领域特化精读框架

对每篇论文，提取以下结构化信息：

```json
{
  "paper_id": "...",
  "problem": "解决什么问题",
  "motivation": "为什么现有方法不够",
  "method": {
    "core_idea": "核心 insight（一句话）",
    "architecture": "模型架构概述",
    "key_components": ["组件1", "组件2"],
    "training": "训练策略（数据、loss、optimizer、schedule）",
    "inference": "推理流程与效率"
  },
  "experiments": {
    "benchmarks": ["benchmark1", "benchmark2"],
    "baselines": ["baseline1", "baseline2"],
    "main_results": "核心数论 (key numbers)",
    "ablations": "ablation 要点",
    "compute": "GPU hours / FLOPs / 模型大小"
  },
  "limitations": ["局限1", "局限2"],
  "review_context": {
    "venue": "...",
    "decision": "accept/reject",
    "scores": [6, 7, 5, 8],
    "main_criticisms": ["批评1", "批评2"],
    "author_response_effectiveness": "high/medium/low"
  },
  "relevance_to_rq": "与我们 RQ 的关联",
  "borrowable_ideas": ["可借鉴的点1", "可借鉴的点2"],
  "open_questions": ["遗留问题1", "遗留问题2"]
}
```

### 特殊关注

- **实验可复现性**：代码是否开源？结果能否复现？是否有已知的复现问题？
- **Scaling 行为**：在不同模型大小/数据规模下表现如何？
- **消融实验完整度**：每个组件的贡献是否独立验证？
- **评审意见模式**：如果有 OpenReview，关注审稿人的共性批评（这些是该方向的"地雷"）

### 输入/输出

| 项目 | 内容 |
|------|------|
| **输入** | `docs/collection_manifest.json` + `docs/papers/` |
| **输出** | `docs/deep_reads/{paper_id}_report.md` + `docs/deep_reads/{paper_id}_struct.json` |
| **不做的事** | 不做外部检索；不做跨篇综合 |

---

## Stage 3 — 创新图谱 & 候选方向

### 加载规则

```
agents/pipeline/deep-research/agents/synthesis_agent.md
agents/pipeline/deep-research/agents/research_architect_agent.md
agents/pipeline/deep-research/references/argumentation_reasoning_framework.md
```

### 领域特化综合框架

1. **问题层级构建**：
   ```
   顶层问题（如：高效大模型推理）
   ├── 子问题 1：模型压缩（量化 / 剪枝 / 蒸馏）
   │   ├── 方法族 A：Post-training Quantization
   │   ├── 方法族 B：Quantization-Aware Training
   │   └── 方法族 C：Knowledge Distillation
   ├── 子问题 2：推理加速（硬件/系统级）
   │   ├── 方法族 D：KV Cache 优化
   │   └── 方法族 E：投机解码
   └── 子问题 3：架构设计（效率友好架构）
       ├── 方法族 F：Linear Attention
       └── 方法族 G：Mixture-of-Experts
   ```

2. **创新点提取维度**：
   - **理论贡献**：新定理、新 bound、新 framework
   - **方法贡献**：新架构、新 loss、新训练策略
   - **系统贡献**：新 pipeline、新工具、新 benchmark
   - **实证贡献**：大规模实验、新发现、反直觉现象

3. **候选方向评估标准**：

   | 维度 | 权重 | 评估方法 |
   |------|------|---------|
   | Novelty | 30% | 与现有工作的差异度 + 是否有 concurrent work |
   | Feasibility | 25% | 计算资源需求 + 数据可获得性 + 实现复杂度 |
   | Impact | 25% | 解决问题的重要性 + 潜在引用 |
   | Venue Fit | 20% | 与目标 venue（CVPR/NeurIPS/ICML/ICLR等）scope 的匹配度 |

### 输入/输出

| 项目 | 内容 |
|------|------|
| **输入** | `docs/deep_reads/` 所有结构化报告 |
| **输出** | `docs/innovation_graph.md` + `docs/directions.json` |
| **directions.json 字段** | direction_id, title, description, novelty_score, feasibility_score, impact_score, venue_fit_score, total_score, supporting_papers, gaps, risks, estimated_compute |
| **人工确认** | ✅ **关键决策点**：选定 1 个方向 |

---

## Stage 4 — 定向文献扩展

### 加载规则

同 Stage 1 的子集。

### 领域特化扩展策略

1. **时效性优先**：近 6 个月内的 arXiv preprint + 已接收/发表论文
2. **方法迁移搜索**：在相关但不同的领域寻找可借鉴方法（如 NLP 方法用于 CV）
3. **Concurrent work 专项排查**：搜索该方向近期所有 preprint，避免重复研究
4. **Benchmark 进展跟踪**：目标 benchmark 上的新 SOTA 是否改变了方向的可行性

### 输入/输出

| 项目 | 内容 |
|------|------|
| **输入** | 选定方向 + `docs/directions.json` + 现有文献 |
| **输出** | 新增论文 + 更新 `docs/collection_manifest.json` + `docs/expansion_log.md` |

---

## Stage 5 — 深读新文献 & 刷新方向图

### 加载规则

同 Stage 2 + Stage 3 的组合。

### Loop 终止条件

1. 连续一轮扩展新增论文 < 3 篇
2. 方向的 novelty 评估无实质性变化
3. 人工判断方向已足够稳定
4. 已执行 ≥ 3 轮 loop

### 输入/输出

| 项目 | 内容 |
|------|------|
| **输入** | Stage 4 新增论文 + 当前 `docs/innovation_graph.md` |
| **输出** | 更新版 `docs/innovation_graph.md` + `docs/directions.json` + `docs/loop_decision.json` |
| **人工确认** | ✅ 每轮结束确认是否继续 loop |

---

## 质量标准（领域特化）

1. ⚠️ **IRON RULE**：每个 claim 必须有 citation，不接受无来源断言
2. ⚠️ **IRON RULE**：灰区 = FAIL，无法确认存在的文献不得进入报告
3. **Benchmark 数据必须可核实**：报告的数值必须能追溯到原论文的具体 table/figure
4. **关注顶会审稿人的共性批评**：这些是方向的已知"地雷"，在 Stage 3 必须标注
5. **Concurrent work 必须排查**：不能到写论文时才发现有人做了一样的工作
6. **代码可复现性分级**：Official code > Community code > No code，影响对结果的信任度

---

## 反模式

| # | 反模式 | 正确行为 |
|---|--------|---------|
| 1 | 只看 arXiv 不看正式出版物 | arXiv 和正式出版物都要检索 |
| 2 | 忽略 OpenReview 评审意见 | ICLR 论文必须读评审和 author response |
| 3 | 对 SOTA 数字不加验证地引用 | 必须追溯到原论文的具体 table |
| 4 | 忽视负面结果和 failure cases | 负面结果同样有价值，必须纳入综合 |
| 5 | 只在一个数据库检索 | 多数据库交叉检索是最低要求 |
| 6 | Concurrent work 排查不充分 | 每轮 loop 都要搜 arXiv 近 6 个月 preprint |
