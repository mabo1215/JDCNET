# Revision Roadmap — Rejection Response (TCSVT)

Decision received: **Reject**. This roadmap is the recovery plan that maps every
stated rejection reason to concrete manuscript edits and remote-GPU experiments,
in priority order. It supersedes the earlier "Stage 9 Revision Roadmap" content.

Target venue: IEEE TCSVT (transactions paper, 14-page limit).

---

## 1. The Three Rejection Reasons (verbatim decomposition)

The reject decision rests on exactly three flaws. Everything below is scoped to
closing these three and nothing else.

- **F1 — Single-cohort evaluation.** The evaluation is restricted to one
  510-patient cohort, so cross-domain generalization is not demonstrated and the
  findings are susceptible to dataset-specific bias.
- **F2 — Relative-only reporting.** Only relative gains are reported (e.g.
  ΔBA = +0.035); absolute baseline metrics are omitted, so the true clinical
  viability and baseline standing of the model cannot be judged.
- **F3 — Uncalibrated-teacher overconfidence.** The confidence-gated threshold
  is taken from the teacher without any calibration safeguard, so an
  overconfident teacher could force the student to confidently learn incorrect
  target distributions.

Severity ordering: **F1 ≫ F3 > F2**. F1 is the blocking issue (requires new
data and new runs), F3 is a methodological credibility issue (requires new runs
but on existing data), F2 is primarily a reporting issue (mostly aggregation of
existing artifacts, low compute).

---

## 2. Priority-Ordered Action List

### P0 — Must fix before any resubmission

| ID | Reason | Action | Compute |
|----|--------|--------|---------|
| A1 | F2 | Report absolute BA / ROC-AUC / macro-F1 / sensitivity / specificity for supervised X-ray baseline, CT teacher, and the two passing JDCNet cells in the **abstract and main text**, not only the appendix. | None (aggregate existing `best_metrics.json`) |
| A2 | F3 | Add teacher temperature-scaling calibration on a held-out calibration split; gate on **calibrated** confidence; report pre/post ECE and reliability diagrams. | Low (re-score frozen teachers + short student re-runs) |
| A3 | F3 | Add an overconfidence stress ablation: an intentionally uncalibrated/over-sharpened teacher vs. the calibrated teacher, showing the gate degrades without calibration and the safeguard recovers it. | Low–Medium |
| A4 | F1 | External-cohort validation: deploy the frozen X-ray student on ≥1 independent external X-ray cohort (MIDRC + one public COVID CXR set) and report absolute metrics under domain shift. | Medium |

### P1 — Strongly expected by reviewers

| ID | Reason | Action | Compute |
|----|--------|--------|---------|
| B1 | F1 | If any external **paired** CT–X-ray cohort can be assembled, re-run the full JDCNet gate on it (true cross-domain replication of the transfer claim). | High |
| B2 | F1 | Cross-source train/test transfer matrix (train BIMCV → test external, and reverse if feasible) to quantify the generalization gap explicitly. | Medium |
| B3 | F3 | Calibration-aware gate sweep: replace the fixed τ with a calibrated-confidence quantile gate; show the passing cells are stable to the calibration choice. | Medium |

### P2 — Defensive / robustness

| ID | Reason | Action |
|----|--------|--------|
| C1 | F1 | Reframe the contribution as evidence-bounded but now multi-cohort; soften any single-cohort language throughout main.tex and the abstract. |
| C2 | F2 | Add an absolute-metric table to the abstract-adjacent results so a reader can read baseline standing without the appendix. |
| C3 | F3 | Add a short "Calibration Safeguard" subsection to Methodology describing the calibrate-then-gate procedure. |

Experiment designs for A2–A4, B1–B3 are detailed in
[`docs/future_methods_plan.md`](future_methods_plan.md).

---

## 3. Remote 3090 Operating Plan

All remote compute runs on the **4× RTX 3090** box reachable over ZeroTier.

- Host: `mabo1215@10.147.20.176`
- Code root: `/data/JDCNET/src`
- Data root: `/data1` (large datasets, manifests, runs)
- Results pulled back to: `src/results/<tag>/`

### 3.1 WSL-first rule (mandatory, from USAGE.md)

All SSH / SCP / rsync / screen inspection / remote script execution **must** go
through `wsl bash ...` or a repository `.sh` script. Do **not** assemble complex
remote commands in PowerShell. Anything with pipes, redirection, here-docs,
`$()`, regex, or nested quoting must be written as a `.sh` script and invoked via
WSL. Use the existing helper:

```bash
# one-off remote command (from WSL)
bash src/tmp_sync/ssh3090.sh 'hostname; nvidia-smi --query-gpu=index,memory.used --format=csv,noheader'
```

### 3.2 Launch pattern (reuse the proven sweep scaffold)

New sweeps follow the exact structure of `src/ops/remote_3090_gapkd_sweep.sh`:

1. Generate per-cell config JSONs into `src/configs/<sweep>/`.
2. Build a per-GPU queue script, round-robin across GPUs 0–3.
3. Launch each GPU queue in a detached `screen` session.
4. Each run executes `python3 -m jdcnet_exp.train --config <cfg>` (or the
   relevant `jdcnet_exp` entry point) writing `best_metrics.json` + `best.pt`.
5. A `*_summarize.sh` companion aggregates `best_metrics.json` into ΔBA tables.

```bash
# typical lifecycle (all from WSL)
bash src/ops/<new_sweep>.sh                 # generate configs + launch screens
bash src/tmp_sync/ssh3090.sh 'screen -ls'   # confirm sessions are up
bash src/ops/<new_sweep>_summarize.sh        # aggregate when done
bash src/tmp_sync/pull_3090_gapkd_sweep_results.sh   # pull artifacts back
```

### 3.3 GPU budget per task

| Task | Runs | Layout | Wall time (4×3090) |
|------|------|--------|--------------------|
| A2 calibrated-gate re-run (2 passing cells × calib on/off) | 4 cfg × 15 fold/seed = 60 | round-robin 4 GPU | ~1.5 h |
| A3 overconfidence ablation (calib vs sharpened teacher) | ~4 cfg × 15 = 60 | round-robin | ~1.5 h |
| A4 external X-ray inference (frozen student, no training) | inference only | single GPU | < 30 min |
| B1 external paired JDCNet gate (if cohort exists) | 16 cfg × 15 = 240 | round-robin | ~6 h |
| B2 cross-source transfer matrix | ~30 runs | round-robin | ~1.5 h |
| B3 calibrated-quantile gate sweep | ~6 cfg × 15 = 90 | round-robin | ~2.5 h |

### 3.4 Artifact hygiene

- Each sweep writes to its own `src/results/<tag>_3090_<YYYYMMDD>/`.
- A decision report (`*_decision_report.md`) per sweep records ΔBA, 95% CI,
  fold/seed win counts, and PASS/FAIL against the fixed gate.
- Absolute metrics (BA/AUC/F1/sens/spec) are extracted alongside ΔBA so F2 is
  never re-opened.
- Pull only `best_metrics.json`, decision reports, and figures back to Windows;
  leave `best.pt` checkpoints on `/data1`.

---

## 4. Fixed Validation Gate (unchanged across all new experiments)

A configuration passes only if:

> **mean ΔBA ≥ +0.03 AND 95% percentile-bootstrap CI lower bound > 0**,
> evaluated under patient-level 5-fold CV with seeds 42–44 (n = 15 paired
> fold/seed cells), against the matched supervised baseline.

For external cohorts (F1), the headline endpoint is **absolute** balanced
accuracy and ROC-AUC of the deployed student under domain shift, reported with
patient-level bootstrap CIs; the ΔBA gate applies only where a matched in-cohort
baseline exists.

---

## 5. Manuscript Integration Checklist

- [ ] Abstract: add absolute BA/AUC for baseline + JDCNet; add one external-cohort
      number; remove "single cohort" as the only evidence framing. (A1, A4, C1)
- [ ] Methodology: add "Calibration Safeguard" subsection (calibrate-then-gate). (C3)
- [ ] Experiments: add absolute-metric table to main text. (A1, C2)
- [ ] Experiments: add external-cohort section (Tier 4). (A4, B1, B2)
- [ ] Experiments: add teacher-calibration + overconfidence ablation. (A2, A3, B3)
- [ ] Related Work / Limitations: update single-cohort caveat to multi-cohort. (C1)
- [ ] Rebuild `paper/build.bat`; confirm combined PDF ≤ 14 pages.
- [ ] Sync `docs/cover_letter.txt` and `docs/progress.md`.

---

## 6. Stop Conditions

- **Best case:** B1 external paired gate passes → upgrade from "bounded single
  cohort" to "replicated cross-cohort"; strongest possible rebuttal of F1.
- **Expected case:** no external paired cohort obtainable; A4 + B2 demonstrate
  the deployed student degrades gracefully under domain shift with reported
  absolute numbers → F1 addressed as a transparent external-validity result,
  F2/F3 fully closed. This is sufficient for resubmission.
- **Floor:** if external data is entirely unobtainable, A1–A3 still close F2 and
  F3; F1 is then answered by an explicit, quantified single-cohort scope
  statement plus a domain-shift inference result on whatever public X-ray-only
  set is available.

---

*Rewritten 2026-06-16 in response to the TCSVT reject decision recorded in
`docs/revision_suggestions.tex`. Experiment-level detail: `docs/future_methods_plan.md`.*
