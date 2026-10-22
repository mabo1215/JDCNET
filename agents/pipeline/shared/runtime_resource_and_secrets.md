# Runtime Resource and Secret Access Protocol

> Scope: Pipeline tasks that involve `src/` experiments, model inference runs, dataset/model fetching, and image redraw workflows.

---

## 1) Remote 4x RTX 3090 Resource (ZeroTier)

When a task requires multi-GPU inference/benchmarking (especially 4-card runs), use the remote host reachable over ZeroTier:

- Host: `10.147.20.176`
- GPU resource: 4 x RTX 3090
- Login identity source: `src/.env` line 1 (`username@10.147.20.176` format)
- Login password source: `src/.env` line 2

### Required behavior

1. Treat remote login info as secret material. Do not print credentials in logs, reports, or chat output.
2. Read only what is needed from `src/.env`; do not copy full file contents into generated documents.
3. For long-running experiments, record only non-sensitive status fields in `docs/progress.md`:
   - run status (`running/succeeded/failed`)
   - latest log path
   - latest output directory
   - next action
4. If remote execution fails due to connectivity/auth/environment issues, mark task status in `docs/progress.md` and continue with available local tasks; only escalate to `## 遗留问题` when author input is required.

---

## 2) FAL Image Redraw Key Usage

For image-redraw tasks (flowcharts/figures) triggered by the image redraw template, use fal.ai Nano Banana.

- Key source: `src/.env` variable prefixed by `FAL_KEY=`

### Required behavior

1. Never expose `FAL_KEY` in terminal output, markdown, paper text, or logs.
2. Keep redraw outputs publication-grade and consistent with `USAGE.md` image redraw constraints.
3. Preserve original file by renaming with `_old` suffix before saving the regenerated file using the original name.

---

## 3) Hugging Face Key Usage

When pulling models or datasets from Hugging Face:

- Key source: `src/.env` variable prefixed by `HuggingFACE_KEY=`

### Required behavior

1. Read and use the token without exposing it.
2. Prefer environment-variable injection at runtime rather than hardcoding in scripts.
3. If token is missing/invalid, continue with non-blocking tasks first and only add an item to `## 遗留问题` when author action is required.

---

## 4) Progress Tracking Requirement for Running Experiments

For each in-progress subtask under `## 未修改或部分修改`, add a single dedicated status line immediately below the subtask using this format:

- `推进状态：进行中 | 已完成 | 失败待修复 | 等待作者输入`

Optional extension:

- `推进状态：进行中（最近动作：...；证据：...；下步：...）`

This line must be updated on each run/check cycle.

---

## 5) Stage Binding

This protocol applies primarily to:

- Stage 7 (draft + experiments/figures support)
- Stage 10 / 10' (revision-driven experiments and evidence updates)

It does not override the Stage 9 trigger gate. Stage 9 remains controlled by the Stage 9 gate checklist in `USAGE.md`.
