# Claude Code Rules - Source Code and Experiments

## Venue-Driven Standards

When `USAGE.md` declares a target venue through the line
`目标会议或期刊：...`, use that venue as the canonical standard for scope,
formatting, and quality checks.

## Role and Responsibilities

This support role may run in parallel with other agents as part of a
broader paper revision process.

The source-facing agent should focus on:
- ensuring experiments are reproducible and properly documented
- keeping code structure consistent with the repository conventions
- preparing final figures for insertion into `paper/figs/`
- verifying that added code supports the paper claims
- cleaning up implementation details and comments

## Paper Integration

The source-facing agent should not modify the manuscript directly unless the
revision guidance explicitly asks it to update textual descriptions based on
new experimental results.

When providing material for the manuscript, convert implementation details into
paper-appropriate scientific descriptions. Do not ask the paper to mention
local folders, script names, or concrete code filenames from `src/`.

## Artifact Management

If new experiments are needed:
1. Implement them under `src/`
2. Save final analysis artifacts in `src/figures/` or `paper/figs/` as appropriate
3. Hand off only reader-facing summaries of setup, metrics, results, and conclusions to manuscript-facing rules

## Language Standards

Keep all code, comments, docstrings, and logs in English.

---

## Pipeline Mode Integration

When operating in Pipeline Mode (see `main.md` § Dual-Mode Architecture),
experiment work maps to the following Pipeline Stages:

| Stage | 阶段 | 实验角色 |
|-------|------|---------|
| 4-5 | 定向迭代扩展 | 文献复现验证、pilot experiments |
| 7 | 全文起草 | 支撑论文声明的实验实现 |
| 8/11 | 完整性核查 | 断言验证、结果可复现检查 |
| 10/10' | 修改 | reviewer 要求的 ablation / 补充实验 |

When in Pipeline Mode and these stages are active:
1. Load `agents/pipeline/academic-paper.md` or
   `agents/pipeline/academic-pipeline.md` for the stage-specific experiment
   requirements
2. Follow the claim verification protocol for Stage 8/11:
   `agents/pipeline/academic-pipeline/references/claim_verification_protocol.md`
3. Ensure experiments satisfy the domain-specific standards from
   `agents/pipeline/domain-venues.md` (e.g., GPU hours, dataset splits,
   statistical significance reporting per venue)

In Revision Mode (default), this file's existing rules apply without change.
