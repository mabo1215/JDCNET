# Academic Pipeline 阶段规则（LLM/VLM/ML/CV 领域特化）

> 覆盖 Pipeline Stage 8/11：完整性核查门控 + 流程编排 + Stage 12-13：定稿与归档
> 基于 `agents/pipeline/academic-pipeline/SKILL.md` v3.2 特化
> 本地扩展：对齐 ARS v3.6.3+ 的 passport reset boundary / resume 语义、v3.5 的协作深度观察员、v3.6.4-3.6.5 的 `literature_corpus[]` 协议与 v3.7.3 的 NO-LOCATOR 引用硬门控

---

## 领域范围

同 `deep-research.md`：LLM、VLM、ML、CV 方向，目标顶会顶刊。

---

## 编排总览

本文件负责以下 Stage 的规则：
- **Stage 8**：Pre-Review 完整性核查（硬性门控）
- **Stage 11**：Final 完整性核查（硬性门控）
- **Stage 12**：格式转换 & 最终定稿
- **Stage 13**：过程记录报告
- **流程编排**：跨 Stage 状态管理、检查点、中途入场

---

## Stage 8 / 11 — 完整性核查（Integrity Verification Gate）

### 加载规则

```
agents/pipeline/academic-pipeline/SKILL.md
agents/pipeline/academic-pipeline/agents/integrity_verification_agent.md
agents/pipeline/academic-pipeline/agents/collaboration_depth_agent.md
agents/pipeline/academic-pipeline/references/integrity_review_protocol.md
agents/pipeline/academic-pipeline/references/claim_verification_protocol.md
agents/pipeline/academic-pipeline/references/passport_as_reset_boundary.md
agents/pipeline/academic-pipeline/references/literature_corpus_consumers.md
agents/pipeline/deep-research/references/semantic_scholar_api_protocol.md
agents/pipeline/academic-paper/references/vlm_figure_verification.md
```

### ⚠️ 硬性门控：100% 通过才放行

### Phase 0: Venue 规格核实（前置）

Stage 8 / 11 开始前**必须**先执行 venue 规格核实：

1. 读取 `USAGE.md` 中 `目标会议或期刊：...` 一行
2. 按 `agents/pipeline/domain-venues.md` 的 **Venue 官网规格抓取协议** 抓取 venue 最新投稿规范
3. 核实并更新 `domain-venues.md` 中对应 venue 的 LaTeX 模板、页数限制、双盲要求、Checklist 要求等
4. 将核实后的 venue 规格作为后续 Phase A-F 的核查基线

### 核查清单（6 Phase）

#### Phase A: Venue 合规核查（新增）

| 检查项 | 方法 | PASS 标准 |
|--------|------|----------|
| LaTeX 模板正确 | 检查 `\documentclass` / `\usepackage` 使用的模板与 venue 要求一致 | 模板文件名和版本匹配 |
| 正文页数合规 | 统计编译后 PDF 正文页数 | ≤ venue 限制 |
| 双盲合规 | 扫描正文中是否泄露作者身份（自引、致谢、affiliation） | 双盲 venue 无身份泄露 |
| Checklist 完整 | 逐项核对 venue 要求的 checklist（如 NeurIPS Checklist） | 所有 mandatory 项已填写 |
| Supplementary 合规 | 检查附录格式、大小是否符合 venue 限制 | 格式和大小均合规 |

#### Phase B: 参考文献核查

| 检查项 | 方法 | PASS 标准 |
|--------|------|----------|
| 文献真实存在 | Semantic Scholar API Tier 0 验证 | 100% 文献可查到 |
| 标题匹配 | Levenshtein distance ≤ 3 | 无 title mismatch |
| DOI 正确 | DOI 解析到正确论文 | 100% DOI 有效 |
| 作者匹配 | 第一作者和通讯作者匹配 | 无主要作者错误 |
| BibTeX 完整 | year, title, author, venue 齐全 | 无缺失字段 |
| 引用-正文一致 | `\cite{}` 都有对应 BibTeX entry | 无孤立引用 |
| 正文-引用一致 | BibTeX entry 都在正文被引用 | 无孤立 entry |

#### Phase C: 数据一致性核查

| 检查项 | 方法 | PASS 标准 |
|--------|------|----------|
| Table 中数字一致 | 同一数据在不同 table/text 中一致 | 无矛盾数字 |
| Abstract 中数字 | 与正文 table 匹配 | 100% 匹配 |
| Baseline 数字 | 与原论文报告一致 | 偏差 < 0.5%（允许舍入） |
| 统计量一致 | mean ± std 格式和有效数字统一 | 格式一致 |

#### Phase D: 断言来源核查

| 检查项 | 方法 | PASS 标准 |
|--------|------|----------|
| 核心 claim 有来源 | 每个 factual claim 追溯到 citation 或本文实验 | 无无来源断言 |
| 比较性声明 | "优于/超过 SOTA" 须有具体数字和来源 | 有量化支撑 |
| 方法学声明 | "首次提出" 须排查 prior work | 已验证首创性或修正措辞 |

#### Phase E: 方法-内容一致性核查

| 检查项 | PASS 标准 |
|--------|----------|
| Method 描述与实际实验一致 | 描述的方法就是实际跑的方法 |
| Notation 全文一致 | 同一符号始终代表同一含义 |
| 术语全文一致 | 不在不同位置用不同术语指同一概念 |
| Algorithm 伪代码与文字描述一致 | 如有 algorithm block |

#### Phase F: 图表核查（可选 VLM 核查）

| 检查项 | PASS 标准 |
|--------|----------|
| 所有图表有 caption | 无缺失 caption |
| 所有图表在正文被引用 | 无孤立 figure/table |
| 图表分辨率足够 | ≥ 300 DPI |
| 图表标签清晰可读 | 无重叠文字，字号足够 |
| 颜色方案色盲友好 | 不依赖红绿区分 |
| **VLM 10 点核查**（可选） | 使用视觉 LLM 进行 10 点核查清单 |

### 领域特化核查重点

#### LLM 论文

| 额外检查 | 说明 |
|---------|------|
| 模型参数量一致性 | Abstract → Method → Experiments 中的参数量一致 |
| 训练超参完整性 | learning rate, batch size, optimizer, schedule 齐全 |
| Compute 报告 | GPU hours / FLOPs 已报告 |
| Safety 讨论存在 | Broader Impact / Limitations 包含安全性 |

#### VLM 论文

| 额外检查 | 说明 |
|---------|------|
| Hallucination 评估存在 | 至少一种评估方法 |
| 多模态 benchmark 覆盖 | ≥ 2 个标准 benchmark |
| 可视化样例存在 | 多模态推理的定性展示 |

#### CV 论文

| 额外检查 | 说明 |
|---------|------|
| 可视化含失败案例 | 不是只展示好的结果 |
| 效率报告存在 | FPS / FLOPs / Params |
| 标准 benchmark 使用 | COCO / ImageNet / ADE20K 等 |

### 引用可发布性硬门控（Cite-Time Provenance）

Stage 8 / 11 的完整性报告必须包含引用可发布性扫描，且遵循以下硬门控：

1. 所有引用都必须具备可定位锚点（quote/page/section/paragraph 之一）。
2. 若发现 NO-LOCATOR（包括以下任一形态），直接判定为不可放行：
  - `[UNVERIFIED CITATION — NO QUOTE OR PAGE LOCATOR]`
  - `<!--anchor:none:-->`
3. NO-LOCATOR 不可通过确认阅读或人工 acknowledge 清除；唯一修复路径是重发该引用并提供有效 locator。
4. `contamination_signals` 仅作 advisory 标注，不改变 gate 结论；但 NO-LOCATOR、MED/HIGH 级风险依旧阻断放行。

> 解释：该规则与 Stage 8/11 的 100% gate 一致，属于结构完整性缺陷而非可忽略 warning。

### 输入/输出

| 项目 | Stage 8 | Stage 11 |
|------|---------|---------|
| **输入** | `paper/main.tex` + `paper/references.bib` | 最终修改版 `paper/main.tex` + `.bib` |
| **输出** | `docs/integrity_report_pre.md` + 修正版草稿 | `docs/integrity_report_final.md` |
| **放行条件** | ✅ 所有 Phase A-F **100% 通过** | ✅ 所有 Phase A-F **100% 通过** |
| **FAIL 处理** | 标记具体失败项 → 修复 → 重新核查 | 同左 |

---

## Stage 12 — 格式转换 & 最终定稿

### 加载规则

```
agents/pipeline/academic-paper/SKILL.md             # format-convert 模式
agents/pipeline/academic-paper/agents/formatter_agent.md
agents/pipeline/academic-paper/references/latex_template_reference.md
```

### 领域特化格式要求

> **以下表格为缓存值**。执行 Stage 12 时，必须按 `domain-venues.md` 的 **Venue 官网规格抓取协议** 从官网抓取最新规范，以官网为准。

| Venue | 模板 | 正文页数 | 编译 | 特殊事项 |
|-------|------|---------|------|---------|
| NeurIPS | `neurips_2026.sty` | 9 页 | pdflatex/xelatex | Checklist 必填 |
| ICML | `icml2026.sty` | 8 页 | pdflatex | — |
| ICLR | `iclr2026_conference.sty` | 9 页 | pdflatex | OpenReview supplementary |
| CVPR | `cvpr.sty` | 8 页 | pdflatex | 匿名性严格检查 |
| ICCV | 同 CVPR | 8 页 | pdflatex | 双年会 |
| ECCV | 同 CVPR | 14 页（含引用） | pdflatex | 页数含引用 |
| ACL | `acl.sty` (ARR) | 8 页(long) | pdflatex | Responsible NLP Checklist |
| TPAMI | `IEEEtran.cls` | 14 页 + ref | pdflatex | 已有模板在 `paper/build/template/` |
| IJCV | `svjour3` | 无硬性限制 | pdflatex | — |

### 编译流程

```
使用 paper/build.bat（如存在）或 tectonic/pdflatex
    ↓
中间文件 → paper/build/
    ↓
最终 PDF → paper/main.pdf + paper/appendix.pdf
```

### 最终检查清单

- [ ] **Venue 规格已从官网核实**（`domain-venues.md` 中标注 `<!-- verified: YYYY-MM-DD -->`）
- [ ] LaTeX 模板与 venue 官方指定的版本一致
- [ ] 页数符合 venue 限制（区分正文/含引用/含附录的不同计算方式）
- [ ] 匿名性正确（投稿双盲会议时无作者身份泄露）
- [ ] 所有图表清晰可读（zoom 到 100% 检查）
- [ ] 参考文献格式正确（符合 venue 引用风格）
- [ ] 无编译 warning（overfull hbox 等）
- [ ] Checklist 填写完整（NeurIPS/ACL 等，按 venue 要求）
- [ ] Supplementary material 格式和大小符合 venue 限制
- [ ] 代码提交准备好（如 venue 要求）
- [ ] AI 使用声明已按 venue 要求填写

### 输入/输出

| 项目 | 内容 |
|------|------|
| **输入** | 最终 `paper/main.tex` + `paper/appendix.tex` + `paper/references.bib` + `paper/figs/` |
| **输出** | `paper/main.pdf` + `paper/appendix.pdf` |
| **人工确认** | ✅ 确认最终版本 |

---

## Stage 13 — 过程记录报告

### 加载规则

```
agents/pipeline/academic-pipeline/references/process_summary_protocol.md
```

### 记录内容

| 维度 | 记录项 |
|------|--------|
| **Pipeline 概览** | 启动日期、完成日期、经历的 Stage、每 Stage 用时 |
| **关键决策点** | Stage 0 的 RQ 选择、Stage 3 的方向选择、Stage 6 的 venue 选择 |
| **迭代历史** | Stage 4-5 loop 次数、Stage 9-10 修改轮次 |
| **完整性核查** | Stage 8 和 Stage 11 的核查结果摘要 |
| **评审摘要** | 总评分、主要优缺点、修改响应摘要 |
| **6 维协作质量评分** | Research Depth(1-100)、Writing Quality(1-100)、Technical Rigor(1-100)、Novelty(1-100)、Reproducibility(1-100)、Presentation(1-100) |

### 输入/输出

| 项目 | 内容 |
|------|------|
| **输入** | 全流程状态文件 |
| **输出** | `docs/process_summary.md` |

---

## 流程编排规则

### Collaboration Depth Observer（仅建议，永不阻断）

`collaboration_depth_agent` 在 FULL/SLIM 检查点触发，用于评估协作深度与认知分工；该输出仅用于提示，不得成为 stage 转移阻断条件。

硬约束：
- MANDATORY gate（完整性核查、关键决策）不以 observer 结论作为放行条件
- 不允许出现基于 observer 的阻断状态（例如 `blocked_by: collaboration_depth_agent`）
- observer 输出可进入 Stage 13 过程总结，但不得覆盖技术核查结论

### Passport Reset Boundary 与 Resume 模式

当启用 `ARS_PASSPORT_RESET=1` 时，FULL 检查点提升为 context reset boundary，并在 Material Passport 的 `reset_boundary[]` 追加 `kind: boundary` 记录。

恢复命令：
```
resume_from_passport=<hash> [stage=<n>] [mode=<m>]
```

恢复规则：
1. 用 `<hash>` 在 `reset_boundary[]` 中定位唯一 boundary；若不存在或已被后续 `kind: resume` 消费则报错。
2. 若 boundary 含 `pending_decision`，必须先重提分支问题并记录 `chosen_branch`，再决定 next stage。
3. CLI 覆盖优先级：`stage=<n>`、`mode=<m>` 高于默认 next 路由。
4. 成功恢复后，必须追加 `kind: resume` 且 `consumes_hash=<hash>`，保持 append-only 审计轨迹。

### Material Passport `literature_corpus[]` 协议接入

Stage 8/11 在审查手稿可追溯性时，默认将 Material Passport 的 `literature_corpus[]` 作为引用来源侧证据输入；其读取遵循 consumer protocol：

1. Presence-based：仅在 `literature_corpus[]` 非空且可解析时启用 corpus-first 流程。
2. Parse failure graceful fallback：解析失败时显式标注 `[CORPUS PARSE FAILURE: <cause>]`，回退 external-DB-only 流程。
3. No corpus mutation：完整性阶段不得改写或回填 `literature_corpus[]` 条目。
4. 与 Stage 8/11 的引用核查联动：`citation_key`、source-acquired/verified 信号用于 finalizer 判定与报告展示。

### Pipeline 状态管理

```json
{
  "pipeline_state": "running",
  "current_stage": "Stage 7",
  "stage_states": {
    "stage_0": "completed",
    "stage_1": "completed",
    "stage_2": "completed",
    "stage_3": "completed",
    "stage_4": "completed",
    "stage_5": "completed",
    "stage_6": "completed",
    "stage_7": "in_progress",
    "stage_8": "pending",
    "stage_9": "pending",
    "stage_10": "pending",
    "stage_11": "pending",
    "stage_12": "pending",
    "stage_13": "pending"
  },
  "loop_count": {"stage_4_5": 2, "stage_9_10": 0},
  "target_venue": "NeurIPS 2026",
  "last_updated": "2026-04-14"
}
```

### 中途入场（Mid-Entry）

| 用户情况 | 检测方法 | 起始 Stage |
|---------|---------|-----------|
| 已有论文草稿 | `paper/main.tex` 存在且有内容 | Stage 8（完整性核查）|
| 已有论文 + 审稿意见 | `docs/revision_suggestions.tex` 存在 | Stage 10（修改）|
| 已有研究但未成文 | `docs/deep_reads/` 存在 | Stage 6（论文规划）|
| 从零开始 | 无材料 | Stage 0（方向探索）|

### ARS 子模块同步检查

每次 Pipeline 启动前：

```bash
cd docs/academic-research-skills
git fetch origin
# 检查是否有更新
git log HEAD..origin/main --oneline
# 如有更新，提示用户是否同步
```

同步后检查：
1. `MODE_REGISTRY.md` 版本号是否变化
2. `shared/handoff_schemas.md` 数据契约是否变化
3. 各 `SKILL.md` 的 `depends_on` 是否变化
4. 本目录规则文件是否需要对应调整

### 检查点（Checkpoint）策略

| Stage 完成后 | 检查点内容 | 阻塞? |
|-------------|-----------|-------|
| Stage 0 | RQ + venue 确认 | ✅ 阻塞 |
| Stage 1 | 文献覆盖范围确认 | ✅ 阻塞 |
| Stage 3 | 方向选择确认 | ✅ 阻塞 |
| Stage 5 每轮 | 是否继续 loop 确认 | ✅ 阻塞 |
| Stage 6 | 大纲 + venue 确认 | ✅ 阻塞 |
| Stage 8 | 100% 通过才进入 Stage 9 | ✅ 硬性阻塞 |
| Stage 9 | 修改策略确认 | ✅ 阻塞 |
| Stage 9' | 是否需要 Stage 10' | ✅ 阻塞 |
| Stage 11 | 100% 通过才进入 Stage 12 | ✅ 硬性阻塞 |
| Stage 12 | 最终版本确认 | ✅ 阻塞 |

### 与 Bodhi 已有修订循环的衔接

当 Pipeline 走到 Stage 9 生成 `docs/revision_suggestions.tex` 后，或论文投稿后收到真实审稿意见后：

1. 审稿意见写入 `docs/revision_suggestions.tex`（英文 LaTeX）
2. 每个修改项标注 `% STAGE:` 和 `% RULES:`
3. 触发 Bodhi 已有的**自动修订循环**：
   - 读 `revision_suggestions.tex` → 按 Stage 分组 → 加载对应规则 → 逐项修改
   - 同步 `docs/progress.md`（三段式）
   - 迭代直到无可执行项
4. 修改完成后进入 Stage 9'（复核评审）
5. 如需 Stage 10' → 回到自动修订循环
6. 最终进入 Stage 11 → 12 → 13

### 独立评审重置的 Pipeline 语义

触发 `进入 Pipeline Stage 9` 时：
- 相当于**强制重新执行 Stage 9**（含 Venue 规格核实 + 5-Reviewer 评审）
- 首先按 `domain-venues.md` 的 Venue 官网规格抓取协议核实 venue 最新投稿规范
- 在正式评审前，必须先确保生成 `paper/main.pdf` 与 `paper/appendix.pdf`；优先使用仓库现有 LaTeX 构建入口，若不存在则按当前论文工程的标准方式分别编译 `paper/main.tex` 与 `paper/appendix.tex`
- 必须将 `paper/main.tex` + `paper/main.pdf` 作为同一篇论文的正文，将 `paper/appendix.tex` + `paper/appendix.pdf` 作为该论文的附录，按单篇论文整体联合评审，不得拆分为两份独立稿件
- 评审维度包括 Venue 合规性（LaTeX 模板、页数限制、双盲要求、Checklist）
- 生成的新 `revision_suggestions.tex` 自动添加 `% STAGE:` 标注
- 然后回到 Stage 10 的自动修订循环

---

## 反模式

| # | 反模式 | 正确行为 |
|---|--------|---------|
| 1 | 跳过完整性核查直接评审 | Stage 8 是硬性门控，必须 100% 通过 |
| 2 | 编译时忽略 warning | overfull hbox 等 warning 须修复 |
| 3 | 超过 venue 页数限制 | 严格按限制，多余内容放附录 |
| 4 | ARS 更新后不检查兼容性 | 每次 git pull 后检查本目录规则 |
| 5 | Pipeline 没有状态文件 | 每次 Stage 转换都更新状态，确保可恢复 |
| 6 | 中途入场不做 material audit | 必须检查已有材料的完整性和质量 |
