# AGENTS.md

## Mission

Upgrade the manuscript in `paper/` toward publication quality by following
`docs/revision_suggestions.tex`, or by running an independent venue-driven
review reset when explicitly requested by the user, modifying the manuscript,
adding experiments when needed, generating figures or tables, integrating them
into the paper, and updating `docs/progress.md`.

Alternatively, when the user triggers Pipeline Mode, execute the 13-stage
research pipeline defined in `docs/Bodhi_科研Pipeline总览.md`, using
stage-specific rules from `agents/pipeline/`. The pipeline covers the full
research lifecycle from topic exploration to final archival, with domain
specialization for LLM, VLM, ML, and CV research targeting top venues.

This repository may also be used as a Codex rule template that is copied into
another repository. In the template repo itself, canonical destination-repo
files such as `docs/revision_suggestions.tex`, `docs/progress.md`,
`paper/main.tex`, `paper/appendix.tex`, and `paper/references.bib` may be
absent. Treat those paths as the expected layout of the destination repo rather
than as a template error.

The repository-wide process may use multiple agents in parallel when helpful,
and it should keep iterating automatically across revision cycles until the
current `docs/revision_suggestions.tex` has no remaining actionable items.

The agent should work autonomously and iteratively until all actionable
revision items are either:
1. fully completed, or
2. explicitly marked as blocked or partially completed with reasons and next
   steps.

---

## Repository layout

- Shared agent entry file: `USAGE.md`
- Target venue configuration: `USAGE.md`
- Revision guidance: `docs/revision_suggestions.tex`
- Progress tracking: `docs/progress.md`

- Main manuscript: `paper/main.tex`
- Appendix: `paper/appendix.tex`
- Bibliography: `paper/references.bib`
- Figures: `paper/figs/`
- Build script: `paper/build.bat`
- Build outputs: `paper/build/`

- Experiment and implementation code: `src/`

- Pipeline architecture overview: `docs/Bodhi_科研Pipeline总览.md`
- Pipeline stage rules index: `agents/pipeline/PIPELINE_RULES.md`
- Pipeline stage-specific rules: `agents/pipeline/*.md`
- ARS skill rules (local copies): `agents/pipeline/{deep-research,academic-paper,academic-paper-reviewer,academic-pipeline,shared}/`

---

## Dual-mode architecture

### Revision Mode (default)

The original flat revision workflow. Active by default.

Behavior: read `docs/revision_suggestions.tex` → revise paper → run experiments
→ update progress → iterate → fresh independent review if exhausted.

### Pipeline Mode

A 13-stage research pipeline. Triggered by `启动科研 Pipeline` or
`进入 Pipeline Stage N`.

When active:
1. Read `agents/pipeline/PIPELINE_RULES.md` for stage index.
2. Load only the current stage's rules:
   - Stage 0-5: `agents/pipeline/deep-research.md`
   - Stage 6-7, 10/10': `agents/pipeline/academic-paper.md`
   - Stage 8, 11: `agents/pipeline/academic-pipeline.md`
   - Stage 9, 9': `agents/pipeline/academic-paper-reviewer.md`
   - Stage 12-13: `agents/pipeline/academic-pipeline.md`
3. Load the ARS sub-agent files referenced in the stage rule's "加载规则" section.
4. For cross-stage handoff, load `agents/pipeline/shared/handoff_schemas.md`.
5. See `docs/Bodhi_科研Pipeline总览.md` §9 for the complete routing table.
6. Pipeline Phase G (自动修订循环) maps to Revision Mode.

### Mode commands

| Command | Action |
|---------|--------|
| `启动科研 Pipeline` | Enter Pipeline Mode from Stage 0 |
| `进入 Pipeline Stage N` | Enter Pipeline Mode at Stage N |
| `切换到修订模式` | Return to Revision Mode |
| `重新开始评审并生成评审修改意见` | Independent review reset (either mode) |

### Minimal trigger templates

Prefer short prompts that contain only the action and any required parameter. Do not repeat fixed workflow details that are already enforced by the rules.

Recommended templates:
- `继续当前 revision cycle`
- `消费遗留问题回答并继续推进`
- `巡检运行中任务并继续推进`
- `启动科研 Pipeline`
- `进入 Pipeline Stage N`
- `进入 Pipeline Stage 9`
- `切换到修订模式`
- `按 <XXX目标期刊> 要求评审当前论文，并输出可直接编译的 LaTeX 评审文档`
- `执行图片重绘任务：` followed by image paths
- `重新开始评审并生成评审修改意见`

Special handling for `进入 Pipeline Stage 9`:
- first ensure `paper/main.pdf` and `paper/appendix.pdf` are generated, using the repository's existing LaTeX build entrypoint when available; otherwise compile `paper/main.tex` and `paper/appendix.tex` separately using the project's standard build method
- treat `paper/main.{tex,pdf}` as the main body and `paper/appendix.{tex,pdf}` as the appendix of the same manuscript
- run Stage 9 as one joint review over the combined main-manuscript-plus-appendix package, not as two separate papers

## Remote Debugging Rule

All remote debugging, SSH/SCP/rsync work, screen/tmux inspection, remote script execution, and GPU/training status checks must be WSL-first. Prefer `wsl bash ...` or repository `.sh` scripts for remote operations. Do not compose complex remote commands directly in PowerShell. PowerShell is allowed only when the user explicitly requests PowerShell/`.ps1`, or when the task is specifically to test a Windows PowerShell wrapper. Any remote command involving pipes, redirection, here-docs, `$()` command substitution, regular expressions, nested quoting, or multiline scripts must be written as a bash script and invoked through WSL.

## Language rules

### English-only locations
The following must be written in English only:
- `docs/revision_suggestions.tex`
- all files under `src/`
- all code
- all comments
- all docstrings
- all logs
- all config descriptions
- all file names created under `src/`
- all generated experiment summaries saved under `src/`
- all manuscript content under `paper/`
- all captions, table notes, titles, and scientific analysis
- all BibTeX entries in `paper/references.bib`

### Chinese-language exceptions
`docs/progress.md` may contain Chinese.
`USAGE.md` may contain Chinese.

No Chinese is allowed anywhere else unless the user explicitly requests it.

---

## Reader-first manuscript boundary

The manuscript must be understandable to reviewers and readers without any
knowledge of the local repository layout or implementation file organization.

Do not mention in `paper/`:
- local code paths
- directory names such as `src/experiments/`, `src/figures/`, or similar repo-internal folders
- script names such as `src/run_all.py`
- concrete code filenames used only for local implementation
- instructions about where files are stored in the repository

When experiments or methods are described in the manuscript, rewrite them in
reader-facing scientific prose. Describe the method, motivation, setup,
metrics, evidence, and conclusions, not the local file layout used to produce
them.

---

## Venue Target

The authoritative target venue should be read from the `## 目标会议和期刊`
section in `USAGE.md`, specifically from the line
`目标会议或期刊：...`.

If that line is filled in:
- use it as the primary venue for review standards, scope checks, formatting
  expectations, and submission-readiness judgments
- align manuscript revisions and experiment expectations to that venue
- verify current official venue requirements when they may be time-sensitive
- if the line is updated later, automatically use the new venue for subsequent
   reviews and revision cycles

If that line is blank or unavailable, infer the strongest reasonable top-tier
venue standard from the manuscript and repository context.

---

## Global workflow

1. Read `docs/revision_suggestions.tex`, unless the user explicitly triggers the
   independent review reset command described below.
2. Audit the current manuscript from source and rendered artifacts:
   - `paper/main.tex`
   - `paper/appendix.tex`
   - `paper/main.pdf` when available
   - `paper/appendix.pdf` when available
   - `paper/references.bib`
3. Build an actionable revision plan mapped to concrete files and sections.
4. Use one agent or multiple agents with clear ownership, depending on the
   workload.
5. Revise the paper section by section.
6. If a revision item requires experiments:
   - implement or extend code in `src/`
   - run experiments
   - save final paper-ready figures to `paper/figs/`
   - insert figures or tables into the manuscript
   - add corresponding result description and analysis in the paper
   - ensure the manuscript describes scientific setup and findings without exposing local code paths, folder names, or filenames
7. Re-check `docs/revision_suggestions.tex` after each substantial batch of
   edits.
8. Continue iterating until all actionable items are resolved or explicitly
   documented as blocked.
9. If only non-actionable or genuinely blocked items remain after best effort,
   start a new independent review cycle:
   - ignore prior review history and prior completion judgments
   - review the current paper directly from `.tex` and `.pdf` content
   - assess it against the target venue from `USAGE.md` when available,
     otherwise use the strongest reasonable top-tier venue standard
   - overwrite `docs/revision_suggestions.tex` completely with the new
     English-only LaTeX review
   - begin a fresh autonomous revision cycle against that rewritten file
10. Update `docs/progress.md` in Chinese to reflect the actual repository
    state.

---

## Multi-agent execution policy

Multi-agent execution is allowed and encouraged when it materially reduces the
time needed for a revision cycle.

When using multiple agents:
- assign disjoint ownership whenever possible, such as manuscript sections,
  experiment pipelines, figures, references, or reproducibility checks
- keep the critical path local if the next decision depends on it immediately
- do not let one agent silently overwrite or revert another agent's useful work
- integrate results back into one coherent manuscript state
- re-run the repository-wide checks after parallel work is merged

---

## Automatic revision loop

The default behavior is not a single pass.

The repository process must repeatedly:
- read the current `docs/revision_suggestions.tex`
- implement all actionable manuscript, experiment, figure, and citation changes
- re-audit the updated paper
- continue until the current review file has been exhausted as far as the
  repository can support

If an item remains because of missing data, impossible verification, external
resource limits, or a real scientific block, treat it as non-actionable for the
current cycle and move to the fresh review protocol below rather than stopping
permanently.

---

## Fresh independent review protocol

When the current `docs/revision_suggestions.tex` has no remaining actionable
items and only blocked or non-actionable issues remain:

1. Start a new paper review from scratch.
2. Do not rely on previous review notes, prior completion status, or earlier
   revision judgments.
3. Review the current manuscript directly from:
   - `paper/main.tex`
   - `paper/appendix.tex`
   - `paper/main.pdf` when available
   - `paper/appendix.pdf` when available
4. Evaluate the paper against the target venue declared in `USAGE.md`
   when available. If no target venue is declared, use the strongest reasonable
   top-tier venue standard that can be inferred from the manuscript and
   repository.
5. Rewrite `docs/revision_suggestions.tex` by deleting the old review content
   and replacing it completely with a new English-only LaTeX review.
6. Make the new review self-contained and independent of earlier review rounds.
7. Start the next autonomous revision cycle using only the newly written
   `docs/revision_suggestions.tex`.

---

## Independent Review Reset Command

If the user says `重新开始评审并生成评审修改意见`, interpret it as a full
independent review reset command.

When this command is triggered:
1. Do not use the current `docs/revision_suggestions.tex` as review input.
2. Read the target venue from the `## 目标会议和期刊` section in
   `USAGE.md`, specifically the line `目标会议或期刊：...`.
3. Review the manuscript directly from:
   - `paper/main.tex`
   - `paper/appendix.tex`
   - `paper/main.pdf` when available
   - `paper/appendix.pdf` when available
4. Evaluate the paper against the declared target venue. If no target venue is
   declared, infer the strongest reasonable top-tier venue standard from the
   repository context.
5. Check contribution quality, scope fit, formatting expectations, evaluation
   strength, and submission readiness against that venue.
6. Rewrite `docs/revision_suggestions.tex` completely in English-only LaTeX.
7. Ensure the rewritten file contains both review findings and concrete
   revision actions.
8. After rewriting the file, begin the next autonomous revision cycle against
   the new review unless the user explicitly asked to stop after the review
   rewrite.

For entrypoint examples, prefer the minimal trigger templates above instead of
long prompts that restate built-in workflow steps.

---

## Autonomy rule

The agent should act autonomously and should not ask for trivial confirmation.

Only ask the user when a decision materially affects scientific direction and
cannot be resolved from the repository.

Examples of valid questions:
- choosing between incompatible experiment designs
- selecting one of two conflicting paper narratives
- missing data or credentials
- an extremely expensive experiment that should not be run without confirmation

When asking, provide:
1. the exact decision point
2. the options
3. the recommended option
4. why it matters

---

## Scientific quality target

Target standard: the venue named in `USAGE.md` when available, otherwise
the strongest reasonable top-tier journal or conference standard that can be
inferred from `docs/revision_suggestions.tex`, the manuscript, and repository
context.

The final manuscript should aim for:
- one consistent problem formulation
- coherent notation and method description
- fair and strong experiments
- sufficient baselines and ablations
- privacy-utility evidence where relevant
- reproducibility details
- publication-ready figures and tables
- polished academic English

---

## Revision priorities

Unless the revision guidance explicitly suggests another order, prioritize in
this sequence:

1. unify problem formulation and terminology
2. fix method clarity and notation consistency
3. strengthen experiments
4. improve figure or table quality and interpretation
5. refine related work and positioning
6. polish language, structure, and cross-references

---

## Progress Tracking and Update Rules

After each modification task is completed, update `docs/progress.md` with the following discipline:

0. **Progress file structure**:
   - Maintain three synchronized sections in `docs/progress.md`: `# 已全部修改`, `# 未修改或部分修改`, and `# 遗留问题`.
   - Use `# 遗留问题` for issues that still require the author's decision, confirmation, missing data, external resource, or other newly provided information.

1. **Recording completions**:
   - Add each completed task to the `# 已全部修改` section with a clear task number, brief description, and detailed modification notes.
   - Document what was changed and why it improves the paper.

2. **Moving completed items**:
   - If a task was previously listed in `# 未修改或部分修改`, remove it from that section and add it to `# 已全部修改` after completion.
   - Never leave completed tasks in the "未修改或部分修改" section.

3. **Progress markers**:
   - Mark in-progress tasks with `【进行中】`.
   - Mark blocked tasks with `【已阻挡】` followed by a concise reason and next steps.

4. **Inline user questions for incomplete items**:
   - For every item that remains under `# 未修改或部分修改`, add a short sub-list directly below that item describing what still requires the user's decision, answer, approval, or data.
   - Write these prompts so the user can respond directly inside `docs/progress.md` without needing a separate chat message.
   - If no user input is needed for a still-open item, state that no user decision is currently required and continue autonomous work.

5. **Legacy issue synchronization**:
   - If an incomplete or blocked item still requires author input, also record it in `# 遗留问题`.
   - In `# 遗留问题`, keep the question block explicit so the user can reply inline, for example with `需要你提供/决策：` followed by numbered prompts and `A:` answers.
   - When the issue is resolved and its corresponding work is moved into `# 已全部修改`, remove the matching entry from `# 遗留问题` in the same update.
   - If a new blocker, unanswered question, or missing dataset appears during execution, add a new entry to `# 遗留问题` immediately.

6. **Consistency across agents**:
   - All three agent rule files (Claude, OpenAI Codex, Copilot) must follow the same progress-tracking conventions.
   - When rule changes are made, update all three files to maintain consistency.

7. **Workflow closure**:
   - Continue iterating until all actionable items in `docs/revision_suggestions.tex` are either completed or explicitly marked as blocked.
   - A revision cycle is complete only when no unmarked actionable items remain.

---

## Experiment policy

If experiments are needed to support a claim, the agent must add them
proactively.

Typical acceptable experiment types:
- component ablations
- baseline comparisons
- robustness analysis
- sensitivity analysis
- privacy-utility trade-off curves
- temporal consistency analysis
- failure-case analysis
- reproducibility summaries

Every added experiment must satisfy all of the following:
- implemented under `src/`
- actually run if possible
- final figures exported to `paper/figs/`
- discussed in the paper
- clearly tied to one or more paper claims

Do not add decorative figures with no analytical purpose.

---

## fal.ai image redrawing rules

When using fal.ai to redraw or regenerate images — especially flowcharts,
framework diagrams, architectural illustrations, and other schematic figures —
the following rules apply:

1. **Model**: Always use the **Nano Banana** model on fal.ai. Do not use other
   fal.ai models for image redrawing tasks.
2. **Preserve all core elements**: The redrawn image must retain every core
   element from the original — all boxes, arrows, labels, layers, modules, data
   flows, and annotations. Nothing may be omitted or merged without explicit
   user approval.
3. **No font overlap**: Text labels must never overlap each other or overlap
   other visual elements. Ensure sufficient spacing between all text elements so
   every label is fully legible.
4. **Clean layout**: The redrawn image must have clean, well-organized
   formatting — tidy alignment, consistent spacing, uniform font sizes, and a
   clear visual hierarchy. The result should look publication-ready.
5. **File naming**: Before saving the redrawn image, rename the original file
   by appending an `_old` suffix before the extension (e.g.
   `framework.png` → `framework_old.png`). Then save the new image using the
   original filename. This ensures the old image is preserved for comparison
   while the new image is automatically used by the manuscript.

---

## Local resources

### Local datasets
If local experimental data or images are needed, first inspect:
- `F:\\work\\datasets`

### Local secrets
If `fal.ai` Nano Banana is needed, load credentials from:
- `C:\\source\\phdthesis\\.env`

Never expose secret values in manuscript text, code comments, logs, or saved
artifacts.

---

## Progress tracking rules

At the end of each substantial iteration, update `docs/progress.md` in Chinese
only.

It must:
- preserve the existing two main Chinese sections already used in the file
- summarize each item in one sentence
- include a concrete change note for every item
- include a reason and next step for every incomplete or blocked item

The progress file must reflect the actual repository state, not a plan
disguised as completion.

If a fresh independent review cycle is triggered, record that
`docs/revision_suggestions.tex` was fully rewritten in English-only LaTeX for
the new cycle.

---

## Consistency checks before stopping

Before stopping, verify all of the following:

- `docs/revision_suggestions.tex` has been checked against the current
  repository state
- the target venue from `USAGE.md` has been considered when it is set
- manuscript changes are reflected in `paper/main.tex`
- appendix remains consistent in `paper/appendix.tex`
- references are updated in `paper/references.bib`
- final generated figures are in `paper/figs/`
- if `paper/build.bat` is used, intermediate build files are under `paper/build/`
- if `paper/build.bat` is used, final PDFs are copied back to `paper/`
- all inserted figures or tables are cited and discussed in the paper
- experiment code is under `src/`
- everything in `src/` remains English only
- `docs/progress.md` is updated in Chinese using its existing structure
- unresolved items are explicitly documented
- if the prior review cycle was exhausted, a fresh independent review has been
  written into `docs/revision_suggestions.tex` from current `.tex` and `.pdf`
  content only
- `docs/revision_suggestions.tex` is English-only

---

## Default execution behavior for short user prompts

If the user gives a short instruction asking to start or continue the current
rule-driven revision process, interpret it as:

"Read the repository rules, follow `docs/revision_suggestions.tex`, use
multiple agents when helpful, audit the current manuscript and code, perform
all actionable manuscript and experiment updates, run experiments if needed,
integrate results into the paper, and update `docs/progress.md`. Keep repeating
this process until the current `docs/revision_suggestions.tex` has been
exhausted. If only blocked or non-actionable items remain, perform a fresh
independent review from the current manuscript `.tex` and `.pdf` files,
overwrite `docs/revision_suggestions.tex` completely with the new review, and
start the next revision cycle."

If the user gives the exact command `重新开始评审并生成评审修改意见`, interpret
it using the Independent Review Reset Command section above rather than as a
normal continuation prompt.
