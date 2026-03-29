# Bodhi Agent Codex Template

Codex 规则链，具有模板运行所需的基础目录。

## 已包含内容

- `.codex/config.toml`
- `AGENTS.md`
- `paper/AGENTS.md`
- `src/AGENTS.md`
- `paper/`、`paper/figs/`、`src/` 的基础骨架

## 目标仓库约定

- 目标仓库中应存在 `docs/revision_suggestions.tex`
- 目标仓库中应存在 `docs/progress.md`
- 目标仓库中通常应存在 `paper/main.tex`、`paper/appendix.tex`、`paper/references.bib`

## 目标会议和期刊

目标会议：<International Conference on Medical Image Computing and Computer-Assisted Intervention(MICCAI)>

- 规则会读取这一行，作为评审标准、scope 检查、格式调整、投稿要求核对和论文修改的目标依据
- 如果你后续修改这一行，后续评审与修改应自动按新的目标会议或期刊执行

## 使用方法

1. 用 Codex 打开这个仓库。
2. 将这些规则文件整体复制到你的目标仓库中。
3. 在目标仓库里补齐或复用 `docs/revision_suggestions.tex`、`docs/progress.md`、`paper/main.tex`、`paper/appendix.tex` 与 `paper/references.bib`。
4. 把论文正文、附录、参考文献和实验代码放到目标仓库原有的 `paper/` 与 `src/` 结构中。
5. 先填写上面的“目标会议和期刊”一行。
6. 再给 Codex 发送下面的提示词，让它按规则开始工作。

## 论文编译

- 运行 `paper/build.bat`
- 中间生成文件会放在 `paper/build/`
- `main.tex` 与 `appendix.tex` 会独立编译
- 生成后的 `main.pdf` 与 `appendix.pdf` 会自动复制到 `paper/`

## 提示词

### 常规推进

`读取仓库规则并按 docs/revision_suggestions.tex 自动推进当前任务，必要时并行使用多个 agent，持续迭代直到当前 revision cycle 完成。`

### 重新开始独立评审

`重新开始评审并生成评审修改意见。`

- 触发后会忽略当前 `docs/revision_suggestions.tex` 的已有内容
- 会直接基于 `paper/main.pdf`、`paper/main.tex`、`paper/appendix.pdf`、`paper/appendix.tex` 开始独立评审
- 评审标准会优先读取本文件中的“目标会议和期刊”一行
- 评审结果和修改意见会以英文 LaTeX 格式整段重写进 `docs/revision_suggestions.tex`
