# Bodhi Paper Agent - Claude Code Rules

Claude Code 规则链，具有模板运行所需的基础目录。

## 已包含内容

- `.claude/rules/main.md` - 主工作流程规则（含双模式架构：修订模式 + Pipeline 模式）
- `.claude/rules/paper.md` - 论文修改规则（含 Pipeline Stage 6-7/10 集成）
- `.claude/rules/src.md` - 代码和实验规则（含 Pipeline 实验阶段集成）
- `.claude/settings.json` - 配置和说明
- `../USAGE.md` - 共享目标会议配置 + Pipeline 触发词
- `pipeline/` - 13 阶段科研 Pipeline 规则（ARS v3.3 领域特化，LLM/VLM/ML/CV）
- `paper/`、`paper/figs/`、`src/` 的基础骨架

## 目标仓库约定

- 目标仓库中应存在 `docs/revision_suggestions.tex`
- 目标仓库中应存在 `docs/progress.md`
- 目标仓库中通常应存在 `paper/main.tex`、`paper/appendix.tex`、`paper/references.bib`

## 目标会议和期刊

- 规则会读取仓库根目录的 `USAGE.md`，并使用其中 `## 目标会议和期刊` 这一节里的 `目标会议或期刊：...` 一行作为评审标准、scope 检查、格式调整、投稿要求核对和论文修改的目标依据
- 如果你后续修改这一行，后续评审与修改应自动按新的目标会议或期刊执行
- 如果这一行为空或缺失，则按论文内容和仓库上下文推断最合理的高水平目标 venue 标准继续工作

## 使用方法

1. 用 Claude 打开这个仓库。
2. 将这些规则文件整体复制到你的目标仓库中。
3. 在目标仓库里补齐或复用 `docs/revision_suggestions.tex`、`docs/progress.md`、`paper/main.tex`、`paper/appendix.tex` 与 `paper/references.bib`。
4. 把论文正文、附录、参考文献和实验代码放到目标仓库原有的 `paper/` 与 `src/` 结构中。
5. 先填写仓库根目录 `USAGE.md` 里的 `目标会议或期刊：...` 一行。
6. 再给 Claude 发送下面的提示词，让它按规则开始工作。

## 论文编译

- 运行 `paper/build.bat`
- 中间生成文件会放在 `paper/build/`
- `main.tex` 与 `appendix.tex` 会独立编译
- 生成后的 `main.pdf` 与 `appendix.pdf` 会自动复制到 `paper/`

## 提示词

- 推荐优先使用“动作 + 必要参数”的最小触发词；`读取仓库规则`、固定文件路径、并行 agent、自动迭代到完成等内容已由规则固化，无需在每次输入中重复。

### 推荐最小模板

- `继续当前 revision cycle。`
- `消费遗留问题回答并继续推进。`
- `巡检运行中任务并继续推进。`
- `启动科研 Pipeline。`
- `进入 Pipeline Stage N。`
- `进入 Pipeline Stage 9。`
- `切换到修订模式。`
- `按 <XXX目标期刊> 要求评审当前论文，并输出可直接编译的 LaTeX 评审文档。`
- `执行图片重绘任务：` 后附图片路径列表。
- `重新开始评审并生成评审修改意见。`

### 常规推进

`继续当前 revision cycle。`

- 每次常规推进完成一个修改任务后，都要同步更新 `docs/progress.md`
- 已经完成的条目如果原先位于 `## 未修改或部分修改`，必须移到 `## 已全部修改`
- 不得把已经完成的条目继续留在 `## 未修改或部分修改` 中
- 对于仍在 `## 未修改或部分修改` 中的每一条，需在该条下面补充“需要你决策/回答/提供的数据”列表，方便用户直接在文件中答复
- 如果某条问题仍阻挡推进且需要作者提供新信息或做决策，应同步记录到 `## 遗留问题`
- 一旦该问题已经解决并移入 `## 已全部修改`，`## 遗留问题` 中对应项也要同步删除

### 重新开始独立评审

`重新开始评审并生成评审修改意见。`

- 触发后会忽略当前 `docs/revision_suggestions.tex` 的已有内容
- 若用户触发 `进入 Pipeline Stage 9` 或独立评审重置，会先确保生成 `paper/main.pdf` 与 `paper/appendix.pdf`；优先使用仓库已有 LaTeX 构建入口，否则分别按当前工程标准编译 `paper/main.tex` 与 `paper/appendix.tex`
- 会基于 `paper/main.pdf`、`paper/main.tex`、`paper/appendix.pdf`、`paper/appendix.tex` 开始独立评审，并将 main 视为正文、appendix 视为同一篇论文的附录联合评审
- 评审标准会优先读取 `USAGE.md` 中的 `目标会议或期刊：...` 一行
- 评审结果和修改意见会以英文 LaTeX 格式整段重写进 `docs/revision_suggestions.tex`

## 规则文件说明

### `.claude/rules/main.md`
主工作流程，包含：
- **双模式架构**：修订模式（默认）+ Pipeline 模式（13 阶段科研管线）
- 任务使命和目标
- 仓库布局和文件约定
- 语言规则（中英文约束）
- 全局工作流程
- 多智能体执行策略
- 自动修订循环
- 独立评审重置协议
- Pipeline 模式下的技能路由、模式感知和阶段间交接协议

### `.claude/rules/paper.md`
论文修改规则，包含：
- 论文修改方向（清晰性、结构、叙述）
- 多智能体协作方式
- 实验集成流程
- 被阻止项目处理
- Pipeline Stage 6-7/10/10' 集成（论文规划/起草/修改）

### `.claude/rules/src.md`
代码和实验规则，包含：
- 会议标准应用
- 可复现性和代码质量
- 图表管理
- 语言标准
- Pipeline Stage 4-5/7/8/10/11 实验集成

### `.claude/settings.json`
配置说明和执行流程指南（含 Pipeline 模式执行流程）。

### `pipeline/` 目录
13 阶段科研 Pipeline 规则，基于 ARS v3.3 领域特化：
- `PIPELINE_RULES.md` — 总索引
- `deep-research.md` — Stage 0-5（研究与文献）
- `academic-paper.md` — Stage 6-7/10/10'（论文撰写与修改）
- `academic-paper-reviewer.md` — Stage 9/9'（同行评审）
- `academic-pipeline.md` — Stage 8/11/12/13（核查、定稿、归档）
- `domain-venues.md` — 领域 venue 数据库
- 各子目录含完整 ARS agent 和 reference 文件

## progress.md 维护要求

- `docs/progress.md` 默认保持中文记录
- `docs/progress.md` 默认维护 `## 已全部修改`、`## 未修改或部分修改`、`## 遗留问题` 三个部分
- 完成的任务统一写入 `## 已全部修改`
- 原先位于 `## 未修改或部分修改` 的任务一旦完成，必须从该部分删除并移入 `## 已全部修改`
- revision cycle 结束前，应检查 `## 未修改或部分修改` 中是否仍残留已完成事项；若有，必须清理后再结束
- `## 未修改或部分修改` 中每个条目下都应列出待用户决策的问题、待回答的问题或待补充的数据，便于用户直接在该文件中回复
- `## 遗留问题` 中应集中列出仍需作者提供信息或决策的阻挡项，用户可直接在这些条目下填写 `A:` 回答
- 若 `## 遗留问题` 中的某项已解决，必须同步从该部分删除，并将对应完成项写入 `## 已全部修改`

## 论文内容边界要求

- 论文正文、附录、caption 和表格说明不得出现本地代码路径、目录名、脚本名或具体代码文件名
- 不得把 `src/experiments/`、`src/figures/`、`src/run_all.py` 等仓库内部路径直接写进论文
- 论文应以审稿人和读者为中心，独立说明方法、动机、意义、实验设计、结果与结论，而不是说明文件放在哪里或脚本如何命名
