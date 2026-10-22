# Bodhi 科研 Pipeline — 分阶段 Agent 规则索引

本目录下的 `pipeline/` 子目录包含基于 `docs/Bodhi_科研Pipeline总览.md` 分阶段架构的具体规则文件。

## 研究方向

大模型（LLM）、视觉语言模型（VLM）、机器学习（ML）、机器视觉（CV）

## 目标 Venue

- **顶会**：NeurIPS, ICML, ICLR, CVPR, ICCV, ECCV, ACL, EMNLP, AAAI, IJCAI, SIGGRAPH
- **顶刊**：TPAMI, IJCV, JMLR, MLJ, TIP, Neural Computation, Nature Machine Intelligence, AI Journal

## 规则文件结构

```
agents/pipeline/
├── PIPELINE_RULES.md              # 本文件：总索引
├── deep-research.md               # Stage 0-5：研究与文献阶段（领域特化）
├── academic-paper.md              # Stage 6-7：论文规划与起草阶段（领域特化）
├── academic-paper-reviewer.md     # Stage 9/9'：同行评审阶段（领域特化）
├── academic-pipeline.md           # Stage 8/11 + 编排：完整性核查与流程编排（领域特化）
├── domain-venues.md               # 领域 venue 数据库与评审标准
├── deep-research/                 # ARS deep-research 完整规则（从子模块复制）
│   ├── SKILL.md
│   ├── agents/                    # 13 个 agent 定义
│   └── references/                # 20 个参考协议
├── academic-paper/                # ARS academic-paper 完整规则（从子模块复制）
│   ├── SKILL.md
│   ├── agents/                    # 12 个 agent 定义
│   └── references/                # 23 个参考协议
├── academic-paper-reviewer/       # ARS academic-paper-reviewer 完整规则（从子模块复制）
│   ├── SKILL.md
│   ├── agents/                    # 7 个 agent 定义
│   └── references/                # 11 个参考协议
├── academic-pipeline/             # ARS academic-pipeline 完整规则（从子模块复制）
│   ├── SKILL.md
│   ├── agents/                    # 4 个 agent 定义（含 collaboration_depth_agent）
│   └── references/                # 关键参考协议（含 resume/corpus）
└── shared/                        # ARS 跨阶段共享协议（从子模块复制）
    ├── handoff_schemas.md
    ├── collaboration_depth_rubric.md
    ├── sprint_contract.schema.json
    ├── style_calibration_protocol.md
    ├── cross_model_verification.md
    ├── mode_spectrum.md
    └── runtime_resource_and_secrets.md  # src/实验远端资源与密钥读取协议
```

## 新增协议索引（第一轮最小同步）

以下为本仓库已接入或应优先接入的新增协议入口（仅索引，不改领域策略）：

- `agents/pipeline/academic-pipeline/agents/collaboration_depth_agent.md`
- `agents/pipeline/academic-pipeline/references/passport_as_reset_boundary.md`
- `agents/pipeline/academic-pipeline/references/literature_corpus_consumers.md`
- `agents/pipeline/academic-paper-reviewer/references/sprint_contract_protocol.md`
- `agents/pipeline/shared/sprint_contract.schema.json`
- `agents/pipeline/shared/collaboration_depth_rubric.md`

## 加载规则

1. 始终先读 `USAGE.md` → 当前模型规则入口
2. 按 `docs/Bodhi_科研Pipeline总览.md` 第九节路由表定位当前 Stage
3. 加载本目录中对应阶段的领域特化规则文件（如 `deep-research.md`）
4. 该文件中的"加载规则"章节列出需加载的子 Agent 文件，路径均指向本目录（如 `agents/pipeline/deep-research/agents/socratic_mentor_agent.md`）
5. 所有规则文件已复制到本目录，**不再需要跨到 `docs/academic-research-skills/` 加载**
6. 当任务涉及 `src/` 实验运行、远端多卡推理、图片重绘或 Hugging Face 拉取时，额外加载 `agents/pipeline/shared/runtime_resource_and_secrets.md`
7. 当使用 `resume_from_passport=<hash>` 恢复时，优先加载 `agents/pipeline/academic-pipeline/references/passport_as_reset_boundary.md`
8. 当任务涉及文献语料入口（Material Passport `literature_corpus[]`）时，额外加载 `agents/pipeline/academic-pipeline/references/literature_corpus_consumers.md`

## 与 ARS 子模块的关系

- 本目录包含从 `docs/academic-research-skills/` 复制的完整 ARS 规则文件
- 顶层的 `deep-research.md` 等文件是**领域特化覆盖层**（LLM/VLM/ML/CV）
- 子目录中的 `deep-research/`、`academic-paper/` 等是 **ARS 原始规则的本地副本**
- **同步流程**：当 ARS 子模块更新时（`git pull`），将更新的文件重新复制到本目录
- 领域特化文件（顶层 `.md`）需要人工审查是否需要同步调整
- 同步时优先保证新增协议索引文件与本文件保持一致，避免“规则已接入但索引缺失”

## 同步检查清单（git pull 后快速自查）

1. 版本头检查：确认四个本地副本 `SKILL.md` 的 `version`/`last_updated` 与子模块一致（`deep-research`、`academic-paper`、`academic-paper-reviewer`、`academic-pipeline`）。
2. 索引一致性检查：确认本文件“规则文件结构”和“新增协议索引”中的路径在仓库中均存在，无孤立索引项。
3. 新增 agent 检查：确认 `academic-pipeline/agents/collaboration_depth_agent.md` 存在，且 `academic-pipeline/SKILL.md` 的 Agent Team 条目包含该 agent。
4. Resume 协议检查：确认 `academic-pipeline/references/passport_as_reset_boundary.md` 存在，且入口规则 `AGENTS.md` 保留 `resume_from_passport=<hash>` 触发语义。
5. Corpus 协议检查：确认 `academic-pipeline/references/literature_corpus_consumers.md` 存在，且 Stage 8/11 规则文件保留 `literature_corpus[]` 的加载与 fallback 说明。
6. Reviewer 合约检查：确认 `academic-paper-reviewer/references/sprint_contract_protocol.md` 与 `shared/sprint_contract.schema.json` 同步存在，避免 reviewer hard-gate 只更新一半。
7. 领域覆盖层回归检查：逐项审阅顶层四个领域特化文件（`deep-research.md`、`academic-paper.md`、`academic-paper-reviewer.md`、`academic-pipeline.md`），只回填协议变化，不覆盖 LLM/VLM/ML/CV 专属策略。
