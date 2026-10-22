# Unified Agent Usage

本文件是仓库内三套模型规则共享的统一 usage 配置入口。

## 规则组织

- `USAGE.md` 是所有模型共享的唯一 usage 和 target venue 配置文件
- `agents/CLAUDE.md` 与 `agents/.claude/` 是 Claude 规则入口
- `agents/.github/agents/bodhi.agent.md` 是 GitHub Copilot 规则入口
- `agents/AGENTS.md` 与 `agents/.codex/` 是 OpenAI/ChatGPT/Codex 规则入口
- 模型入口文件格式可以不同，但对 venue、工作流和进度跟踪语义的理解必须保持一致

## 使用顺序

以后处理论文修改、实验实现、图表生成、独立评审重置等任务时，规则读取顺序应为：

1. 先读取本文件 `USAGE.md`
2. 再读取与当前模型对应的规则入口文件：
   - Claude: `agents/CLAUDE.md` 或 `agents/.claude/rules/`
   - Copilot: `agents/.github/agents/bodhi.agent.md`
   - OpenAI/ChatGPT/Codex: `agents/AGENTS.md` 与 `agents/.codex/config.toml`

## 仓库架构约定

- `docs/` 是论文修订说明、进度跟踪等文档模板目录
- `paper/` 是论文主体、附录、参考文献、图片和编译脚本目录
- `src/` 是实验代码、数据处理和图表生成脚本目录
- `agents/` 是三套大模型的规则目录，不存放论文主体内容
- 本目录结构设计的目标是便于将整个目录直接复制到有实际论文和工程的仓库中使用，而不依赖目标仓库原有的 `README.md`

## 目标会议和期刊

目标会议或期刊：<Discover Artificial Intelligence (Springer Nature)>

- 所有模型规则都应读取这一行，作为评审标准、scope 检查、格式调整、投稿要求核对和论文修改的目标依据
- 如果你后续修改这一行，后续评审与修改应自动按新的目标会议或期刊执行
- 如果这一行为空或缺失，则按论文内容和仓库上下文推断最合理的高水平 venue 标准继续工作

### Venue 规格驱动原则

`目标会议或期刊` 不仅决定评审标准，还驱动以下所有维度：

| 维度 | 说明 | 影响阶段 |
|------|------|----------|
| **评审标准** | scope、创新性、方法严谨性等评审维度的权重和期望 | Stage 9 / 9' |
| **LaTeX 模板** | 使用 venue 指定的 `.cls` / `.sty` 文件 | Stage 7 / 12 |
| **页数限制** | 正文页数、附录限制、引用是否计入页数 | Stage 8 / 12 |
| **双盲要求** | 是否需要匿名化、arXiv 公开限制 | Stage 8 / 12 |
| **Checklist** | NeurIPS Checklist、ACL Responsible NLP Checklist 等 | Stage 8 / 12 |
| **Supplementary** | 补充材料的格式、大小和内容要求 | Stage 12 |
| **代码提交** | 是否强制/鼓励提交代码和数据 | Stage 12 |

### Venue 官网规格抓取

当 `目标会议或期刊` 被设定后，Pipeline 的 Stage 8（完整性核查）、Stage 9（同行评审）、Stage 12（定稿）在首次执行时必须：

1. 抓取目标 venue 的**官方投稿页面**（CFP / Author Guidelines / Submission Instructions）
2. 核实并更新 `agents/pipeline/domain-venues.md` 中对应 venue 的以下字段：
   - LaTeX 模板名称和版本（如 `neurips_2026.sty`）
   - 正文页数限制和引用是否计入
   - 双盲 / 单盲 / 开放评审要求
   - Checklist 或 ethics review 要求
   - Supplementary 和代码提交要求
3. 如果 `domain-venues.md` 中的信息与官网不一致，以**官网为准**并更新规则文件
4. 如果目标 venue 不在 `domain-venues.md` 中，新增一条完整 entry

## 统一工作原则

- 优先在当前仓库根目录的 `docs/`、`paper/`、`src/` 上执行论文修改任务
- 只有规则、触发行为、模型入口配置相关内容才在 `agents/` 下维护
- 多模型规则必须保持对同一套论文工作流和同一目标 venue 的一致理解
- 规则更新后，应同步检查 Claude、Copilot、OpenAI 三套入口文件是否仍然一致
- **远程调试 WSL-first 规则**：所有远程调试、SSH、SCP、rsync、screen/tmux 巡检、远端脚本执行、GPU/训练状态查询，必须优先通过 `wsl bash ...` 或仓库内 `.sh` 脚本执行；不得直接用 PowerShell 拼接复杂远端命令。只有在用户明确要求 PowerShell/`.ps1`，或任务本身必须测试 Windows PowerShell 包装脚本时，才允许使用 PowerShell。涉及管道、重定向、here-doc、`$()`、正则、引号嵌套或远端多行脚本时，必须写成临时/正式 bash 脚本后通过 WSL 调用。
- 论文面向审稿人和读者，正文、附录、图表说明中不得出现本地代码路径、目录名、脚本名或具体代码文件名
- 类似 `src/algorithms/`、 `src/experiments/`、`src/figures/`、`src/run_all.py`、`paper/figs/` 这类仓库内部实现路径不得写入论文内容
- 论文必须作为独立科研叙述存在，不依赖仓库目录结构；应重点说明方法、动机、意义、实验设置、结果以及这些结果如何支撑论文结论
- 涉及 `docs/revision_suggestions.tex` 的自动修改类任务结束后，必须同步更新 `docs/progress.md`
- `docs/progress.md` 应维护 `## 已全部修改`、`## 未修改或部分修改`、`## 遗留问题` 三个部分，并保持三者内容同步
- `docs/progress.md` 中已完成的条目必须从 `## 未修改或部分修改` 移出，并移动到 `## 已全部修改`
- 不得把已经完成的任务继续保留在 `## 未修改或部分修改` 中
- 在处理 `docs/progress.md` 的 `## 未修改或部分修改` 时，每个未完成条目下方都应列出当前仍需用户决策、回答或提供的数据
- 这些问题应直接写在对应条目下面，便于用户在 `docs/progress.md` 中原地回答后继续推进下一步
- `## 遗留问题` 用于集中记录仍需作者提供新信息、补充数据或做决策的阻挡项；同一问题可以与 `## 未修改或部分修改` 联动，但不应脱节
- 当某个未完成问题已经解决并转入 `## 已全部修改` 时，`## 遗留问题` 中对应问题也必须同步删除
- 如果执行过程中出现新的作者决策点、缺失信息或缺失数据，应新增到 `## 遗留问题`
- 目标仓库通常会有自己独立的 `README.md`，因此规则系统不得依赖或要求目标仓库提供本模板自带的 `README.md`

## 常规触发词

### 触发词最小化原则

- 触发词应尽量只包含“动作 + 必要参数”，避免把规则里已经固定的执行步骤重复写进输入
- 以下内容默认由规则自动执行，通常**不需要**每次触发时重复写入：
   - `读取仓库规则`
   - 固定文件路径，如 `docs/progress.md`、`docs/revision_suggestions.tex`
   - `已解决项移入 ## 已全部修改，并同步清理 ## 遗留问题`
   - `必要时自动衔接 Pipeline Stage 10/9'/11`
   - `必要时并行使用多个 agent`
   - `持续迭代直到当前 revision cycle 完成`
   - 对 `进入 Pipeline Stage 9` 而言，5-Reviewer 配置、venue 规格核查、main+appendix 联合评审、覆盖重写 `docs/revision_suggestions.tex` 均已是规则内建行为
- 通常只有以下信息值得显式写入触发词：
   - 目标 venue 名称
   - Pipeline Stage 编号
   - 需要处理的图片或文件路径
   - 本轮新增的用户约束（如“不要改实验，只改文字”）

## 按目标期刊要求评审并输出 LaTeX 格式意见

> 用于快速触发一次针对特定期刊的独立评审，并将评审与修改意见以完整 LaTeX 文档格式输出，便于一键复制或直接写入 `docs/revision_suggestions.tex`。

### Copilot 使用下列触发词执行：

```text
@bodhi 按 <XXX目标期刊> 要求评审当前论文，并输出可直接编译的 LaTeX 评审文档。
```

### 其他使用下列触发词执行：

```text
按 <XXX目标期刊> 要求评审当前论文，并输出可直接编译的 LaTeX 评审文档。
```

触发后：
- 将 `<XXX目标期刊>` 替换为实际期刊名（如 `NeurIPS 2026`、`ACL 2026`、`TPAMI`）
- 抓取目标期刊官方投稿页面，获取最新评审标准和格式要求
- 以 EIC + 3 领域 Reviewer + Devil's Advocate 的 5-Reviewer 视角联合评审
- 输出为完整可编译的 LaTeX 文档，包含 `\documentclass`、`\begin{document}` 等完整结构
- 内容放入 ````latex` 代码块，支持右上角一键复制
- 若需写入文件，可将输出内容覆盖写入 `docs/revision_suggestions.tex`

## 科研 Pipeline 触发词

本仓库支持两种工作模式：**修订模式**（默认）和**Pipeline 模式**（13 阶段全流程科研管线）。

### 启动 Pipeline 模式

#### Copilot 使用下列触发词执行：

```text
@bodhi 启动科研 Pipeline
```

#### 其他使用下列触发词执行：

```text
启动科研 Pipeline
```

触发后：
- 进入 Pipeline 模式，从 Stage 0（方向探索）开始
- 加载 `agents/pipeline/PIPELINE_RULES.md` 了解阶段索引和加载策略
- 按 `docs/Bodhi_科研Pipeline总览.md` §9 路由表加载当前阶段规则
- 领域聚焦：LLM、VLM、ML、CV，目标顶会顶刊

### 进入特定 Pipeline 阶段

#### Copilot 使用下列触发词执行：

```text
@bodhi 进入 Pipeline Stage N
```

#### 其他使用下列触发词执行：

```text
进入 Pipeline Stage N
```

（将 N 替换为目标阶段编号 0-13）

### 切换回修订模式

```text
切换到修订模式
```

### Pipeline 图形化总览（精简版）

```text
┌──────────────────────────────────────────────────────────────────────┐
│                     Bodhi 科研 Pipeline（精简版）                    │
│                                                                      │
│ Stage 0-5   研究：方向探索 → 文献收集 → 深读 → 图谱 → 迭代扩展       │
│ Stage 6-7   写作：论文规划 → 全文起草                                │
│ Stage 8     完整性核查（预审门控，100%通过）                         │
│ Stage 9     同行评审（5-Reviewer）+ Venue 规格核查                   │
│ Stage 10    基于评审意见修改                                          │
│ Stage 9'    复核评审                                                  │
│ Stage 10'   二次修改（按需）                                          │
│ Stage 11    最终完整性核查（最终门控，100%通过）                      │
│ Stage 12-13 定稿与归档                                                │
│                                                                      │
│ Revision 主链（默认修订模式）                                        │
│  先读 docs/progress.md：优先消费 ##遗留问题 的 A: 回答               │
│  → 推进 ##未修改或部分修改                                            │
│  → 已完成项移入 ##已全部修改，并同步清理 ##遗留问题                  │
│  → 再读 docs/revision_suggestions.tex 逐项修改并迭代                 │
│                                                                      │
│ 阶段联动：Stage 10/10'（主）→ Stage 9'（复核）→ Stage 11（收口）      │
│ 独立评审重置：进入 Pipeline Stage 9（强制重评并重写 revision_suggestions）│
└──────────────────────────────────────────────────────────────────────┘
```

### Pipeline 阶段速览

| Stage | 阶段名 | 加载规则 |
|-------|--------|---------|
| 0-5 | 方向探索→创新图谱→迭代扩展 | `agents/pipeline/deep-research.md` |
| 6-7 | 论文规划→全文起草 | `agents/pipeline/academic-paper.md` |
| 8 | 完整性核查（硬性门控） | `agents/pipeline/academic-pipeline.md` |
| 9 | 同行评审（5-Reviewer）+ Venue 规格核查 | `agents/pipeline/academic-paper-reviewer.md` |
| 10 | 基于评审意见修改 | `agents/pipeline/academic-paper.md` |
| 9' | 复核评审 | `agents/pipeline/academic-paper-reviewer.md` |
| 11 | 最终核查 | `agents/pipeline/academic-pipeline.md` |
| 12-13 | 定稿→归档（Venue 格式硬性核对） | `agents/pipeline/academic-pipeline.md` |

## 独立评审触发词（Pipeline Stage 9）

> 独立评审由 Pipeline Stage 9（5-Reviewer 同行评审）承担。
> 但在默认修订循环中**不自动触发 Stage 9**；仅在满足条件并完成作者确认后才进入 Stage 9。

### Copilot 使用下列触发词执行：

```text
@bodhi 进入 Pipeline Stage 9
```

### 其他使用下列触发词执行：

```text
进入 Pipeline Stage 9
```

触发后：
- 加载 `agents/pipeline/academic-paper-reviewer.md` 规则，配置 EIC + 3 领域 Reviewer + Devil's Advocate 评审团
- 先确保生成 `paper/main.pdf` 与 `paper/appendix.pdf`：优先使用仓库现有的 LaTeX 构建入口；若仓库未提供统一构建入口，则按当前论文工程的标准方式分别编译 `paper/main.tex` 与 `paper/appendix.tex`
- 将 `paper/main.tex` + `paper/main.pdf` 视为同一篇论文的正文，将 `paper/appendix.tex` + `paper/appendix.pdf` 视为同一篇论文的附录，必须按“正文+附录”的单篇论文整体联合评审，不得拆成两篇稿件分别评审
- 忽略当前 `docs/revision_suggestions.tex` 的已有内容，从 `paper/main.pdf`、`paper/main.tex`、`paper/appendix.pdf`、`paper/appendix.tex` 重新独立评审
- 写入 `docs/revision_suggestions.tex` 时必须采用覆盖重写：先清空文件全部旧内容，再写入新的英文 LaTeX 评审结果
- 评审标准读取本文件中的 `目标会议或期刊：...` 一行，并抓取 venue 官网最新投稿要求
- 评审维度包括：创新性、方法严谨性、文献覆盖、写作质量、可重复性（0-100 多维评分）
- 同时核查 venue 特定要求：页数限制、双盲合规、Checklist 完整性、LaTeX 模板正确性
- 评审结果和修改意见以英文 LaTeX 格式写入 `docs/revision_suggestions.tex`（不得保留旧轮次内容）
- 完成后自动衔接 Stage 10（基于评审修改）→ Stage 9'（复核）→ Stage 11（最终门控）

> 仅当你明确发出 `进入 Pipeline Stage 9` 触发词时，才执行以上独立评审重置。

## 图片重绘统一规则

- 使用 fal.ai 的 **Nano Banana** 模型进行重绘
- 重绘后的图片必须保留原图所有核心要素，不得遗漏或合并
- 文字标签之间、文字与其他视觉元素之间不得重叠，确保完全清晰可读
- 排版必须干净整齐，达到出版级别
- 重绘前先将原文件加 `_old` 后缀重命名，再用原文件名保存新图

### 图片重绘模板触发词

### Copilot 使用下列触发词执行：

```text
@bodhi 读取仓库规则，并执行图片重绘任务。请根据 USAGE.md 中的图片重绘统一规则，重绘以下图片并保持所有核心元素不丢失、文字不重叠、版式达到出版级别；重绘前先将原文件重命名为带 _old 后缀的文件，再用原文件名保存新图。需要重绘的图片如下：

paper/figs/<image-file-1>
paper/figs/<image-file-2>
```

### 其他使用下列触发词执行：

```text
读取仓库规则，并执行图片重绘任务。请根据 USAGE.md 中的图片重绘统一规则，重绘以下图片并保持所有核心元素不丢失、文字不重叠、版式达到出版级别；重绘前先将原文件重命名为带 _old 后缀的文件，再用原文件名保存新图。需要重绘的图片如下：

paper/figs/<image-file-1>
paper/figs/<image-file-2>
```

## 循环修改触发词

### Copilot 使用下列触发词执行：

```text
@bodhi 继续当前 revision cycle
```

### 其他使用下列触发词执行：

```text
继续当前 revision cycle
```

该触发词与 Pipeline Stage 的重合关系：
- 主要重合：Stage 10 / 10'（基于评审意见修改）
- 通常联动：Stage 9'（复核评审）
- 收口联动：Stage 11（最终完整性核查）
- 定稿联动：Stage 12-13（仅当 Stage 11 通过后）

执行边界（关键）：
- 默认基线是 `docs/revision_suggestions.tex`，在 Stage 10-13 修改循环中**不重写该文件**。
- 默认不触发 Stage 9。
- Stage 9 是否可触发，统一按本文件下方的“Stage 9 触发门控清单（跨入口统一）”执行。

## Stage 9 触发门控清单（跨入口统一）

> 本清单是 Stage 9 升级触发的唯一门控规则，适用于：
> 1) 自动推进 `docs/revision_suggestions.tex` 触发词；
> 2) 遗留问题答案驱动推进触发词。
>
> 跨入口镜像说明：`docs/Bodhi_科研Pipeline总览.md` 中有同名小节用于总览阅读，两处内容需保持一致。
>
> 交叉引用：见 `docs/Bodhi_科研Pipeline总览.md` 的 “Stage 9 触发门控清单（跨入口统一）”。

### 默认规则（先执行）

1. Stage 10-13 循环的基线文件固定为 `docs/revision_suggestions.tex`。
2. 默认不进入 Stage 9，不重写 `docs/revision_suggestions.tex`。
3. 先执行 Stage 10 / 10'（修改）→ Stage 9'（复核）→ Stage 11（收口）。

### 仅在以下任一条件成立时，才可提议进入 Stage 9

1. 现有评审意见明显过时或与当前稿件不一致。
2. `目标会议或期刊` 已变化，需要按新 venue 重新评审。
3. 作者希望做一轮全新独立评审（重置评审视角）。
4. `docs/revision_suggestions.tex` 可执行项基本清空，且 `docs/progress.md` 的 `## 未修改或部分修改` 也清空，仍希望生成新一轮评审意见。

### 确认机制（必须）

1. 满足条件后，先在 `docs/progress.md` 的 `## 遗留问题` 中新增“是否进入 Pipeline Stage 9”的确认问题。
2. 仅当作者给出明确同意（如 `A: 是`）才进入 Stage 9。
3. 若未明确同意，则继续 Stage 10 / 10' → Stage 9' → Stage 11，不进入 Stage 9。

## 遗留问题答案驱动推进触发词

> 用于你已经在 `docs/progress.md` 的 `## 遗留问题` 下按 `A: xxx` 给出回答后，系统先消费这些答案，再继续推进 revision cycle。

### Copilot 使用下列触发词执行：

```text
@bodhi 消费遗留问题回答并继续推进
```

### 其他使用下列触发词执行：

```text
消费遗留问题回答并继续推进
```

触发后：
- 第一步读取 `docs/progress.md`，仅将 `## 遗留问题` 下形如 `A: ...` 的回答视为作者决策输入
- 用这些回答匹配并推进 `## 未修改或部分修改` 中对应条目
- 若某条目已完成：
   - 从 `## 未修改或部分修改` 移出
   - 移入 `## 已全部修改`
   - 同步删除 `## 遗留问题` 中与该条目对应的问题块
- 若仍未完成：保留在 `## 未修改或部分修改`，并在条目下继续列出当前仍需作者回答的问题
- 自动按需要衔接阶段：
   - 需要改文稿/代码：执行 Stage 10 / 10'
   - 需要复核是否改到位：执行 Stage 9'
   - 进入收口前：执行 Stage 11
   - 仅当 Stage 11 通过后才进入 Stage 12-13

Stage 9 触发保护（对本触发词同样生效）：
- 该触发词默认不进入 Stage 9，也不改写 `docs/revision_suggestions.tex`。
- 仅在上方“执行边界（关键）”四条件之一成立时，先把“是否进入 Stage 9”写入 `docs/progress.md` 的 `## 遗留问题`。
- 仅当作者在该问题下给出明确同意（如 `A: 是`）才进入 Stage 9 重新评审并重写 `docs/revision_suggestions.tex`。

## 运行状态巡检推进触发词

> 用于 `## 未修改或部分修改` 中存在“可继续推进但未阻塞”的任务，尤其是 `src/` 下实验正在运行、需要巡检日志、判断是否报错并持续推进的场景。

### Copilot 使用下列触发词执行：

```text
@bodhi 巡检运行中任务并继续推进
```

### 其他使用下列触发词执行：

```text
巡检运行中任务并继续推进
```

触发后：
- 优先读取 `docs/progress.md` 的 `## 未修改或部分修改`，逐条检查是否属于“可继续推进但未阻塞”。
- 对每个子问题必须在下一行新增或更新单独状态行，统一格式：
   - `推进状态：进行中 | 已完成 | 失败待修复 | 等待作者输入`
   - 可选补充：`（最近动作：...；证据：...；下步：...）`
- 如任务涉及 `src/` 实验：检查运行状态、日志输出、报错信息和最新产物路径；可自动修复则继续推进，不可自动修复再写入 `## 遗留问题`。
- 若子问题已解决：从 `## 未修改或部分修改` 移入 `## 已全部修改`，并同步清理 `## 遗留问题` 对应条目。

与 Pipeline Stage 的重合关系：
- 主要重合：Stage 10 / 10'（基于评审意见修改与实验推进）
- 可选联动：Stage 9'（当需要复核本轮修改质量时）
- 收口联动：Stage 11（进入最终核查前）

执行边界（关键）：
- 该触发词默认不触发 Stage 9，不改写 `docs/revision_suggestions.tex`。
- Stage 9 是否可触发，仍严格按“Stage 9 触发门控清单（跨入口统一）”执行。


### 一键复制 LaTeX 输出的提示词（直接输入 Claude 对话框）

若希望 Claude 在右栏生成**全 LaTeX 格式、可一键复制**的评审内容，在对话框中输入：

```text
请根据 <Eighteenth Asian Conference on Computer Vision(ACCV 2026)> 的投稿要求对这篇论文进行完整学术评审，并将所有评审意见和修改建议以完整的可以一键复制的 LaTeX 格式给出。
```

> **提示**：Claude 网页端（claude.ai）和 VS Code 插件的代码块右上角均有"Copy"按钮，上述提示词可确保内容以单个完整代码块输出，点击即可全文复制。
