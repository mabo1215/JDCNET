# Future Methods Plan — Closing the TCSVT Rejection Reasons

**Context.** The TCSVT submission was **rejected** on three grounds (see
`docs/revision_suggestions.tex`): (F1) evaluation is confined to a single
510-patient cohort, so cross-domain generalization is undemonstrated and the
result is exposed to dataset-specific bias; (F2) only relative gains
(ΔBA ≈ +0.035) are reported while absolute baseline metrics are omitted, so
clinical viability and baseline standing cannot be judged; (F3) the
confidence-gated threshold is read off an uncalibrated teacher, which is
vulnerable to overconfidence bias and could push the student to confidently
learn wrong targets without any calibration safeguard.

The validated transfer mechanism (confidence-gated CT→X-ray distillation,
"JDCNet") is **not** in question — two cells already clear the fixed gate
(3-slice soft-KL ΔBA +0.0345; mid hard +0.0329). The rejection is about
**evaluation breadth, reporting completeness, and the calibration safeguard**.
This plan lists the concrete experiments that turn each rejection reason into a
defensible result, and how each runs on the remote 4× RTX 3090 box.

Validation gate (unchanged): **mean ΔBA ≥ +0.03 AND 95% bootstrap CI lower
bound > 0**, 5-fold patient-level CV, seeds 42–44, vs. matched supervised
baseline. For external cohorts the headline endpoint is absolute BA/ROC-AUC
under domain shift with patient-level bootstrap CIs.

Remote infrastructure (all access **WSL-first** per USAGE.md):
`mabo1215@10.147.20.176`, code `/data/JDCNET/src`, data `/data1`, helper
`src/tmp_sync/ssh3090.sh`. Launch scaffold pattern:
`src/ops/remote_3090_gapkd_sweep.sh`.

---

## Method A1 — Absolute-Metric Reporting (closes F2) ★ no new training

### Why
F2 is fundamentally a reporting gap, not a modelling gap. The absolute metrics
already exist in every run's `best_metrics.json`; they are currently buried in
the appendix. The fix is to surface them in the abstract and main text.

### Plan
1. For supervised X-ray baseline, CT teacher (mid + 3-slice), and the two
   passing JDCNet cells, aggregate from existing artifacts:
   absolute **balanced accuracy, ROC-AUC, macro-F1, sensitivity, specificity**,
   each with patient-level bootstrap 95% CI.
2. Emit a compact main-text table and 1–2 absolute numbers into the abstract
   (e.g. "supervised X-ray BA = 0.XX → JDCNet BA = 0.YY, ΔBA = +0.035").
3. Keep the relative ΔBA framing but never report it without the absolute pair.

### Remote / local execution
- Pure aggregation; no GPU training. Run the summarizer over existing
  `src/results/bimcv_pseudolabel_*` and `bimcv_full_paired_cv_*` artifacts.
- Reuse `jdcnet_exp.robust_stats_report` / `jdcnet_exp.summarize_runs` and the
  existing bootstrap-CI utility to dump an `absolute_metrics_table`.

```bash
# from WSL — aggregate absolute metrics from existing run artifacts
bash src/tmp_sync/ssh3090.sh 'cd /data/JDCNET/src && python3 -m jdcnet_exp.summarize_runs \
  --runs runs/bimcv_pseudolabel_cv runs/bimcv_pseudolabel_soft runs/bimcv_pseudolabel_lam15 \
  --metrics balanced_accuracy roc_auc macro_f1 sensitivity specificity --bootstrap 10000 \
  --out /data1/reports/absolute_metrics_table.json'
```

**Status:** NOT STARTED. **Compute:** none. **Blocks:** abstract + main-text edits.

---

## Method A2 — Calibrate-Then-Gate Teacher (closes F3, primary) ★★★

### Why
The reviewer's sharpest methodological point: the gate trusts raw teacher
softmax confidence. If the teacher is overconfident, the mask admits confidently
wrong pseudo-targets. The fix is to **calibrate the teacher before gating** and
gate on calibrated confidence.

### Plan
1. **Held-out calibration split.** Within each training fold, hold out a small
   calibration subset (or use out-of-fold teacher predictions) never seen by the
   teacher fit.
2. **Temperature scaling.** Fit a single scalar temperature `T_cal` on the
   calibration split by minimizing NLL (standard post-hoc calibration). Optional:
   vector/Platt scaling as a secondary check.
3. **Calibrated gate.** Replace `mask = max(softmax(z)) > τ` with
   `mask = max(softmax(z / T_cal)) > τ`. Re-run the two passing JDCNet cells.
4. **Report.** ECE / MCE and reliability diagrams **before vs. after**
   calibration, on retained vs. rejected subsets. We already observe ECE drops
   from 0.14–0.16 (rejected) to 0.07–0.08 (retained) under the raw gate; show the
   calibrated gate makes this separation principled rather than incidental.
5. **Pass criterion.** The two passing cells must still clear the fixed gate
   under calibrated confidence (expected: equal or stronger, with lower ECE).

### Implementation
- Extend `jdcnet_exp.calibration_report` (already computes ECE + reliability)
  to fit and persist `T_cal` per fold/teacher.
- Add a `teacher_temperature` field consumed by `train_pseudolabel.py` /
  `distillation.py` when forming the confidence mask.

### Remote execution
```bash
# 1) fit per-fold teacher temperature, write T_cal table
bash src/tmp_sync/ssh3090.sh 'cd /data/JDCNET/src && python3 -m jdcnet_exp.calibration_report \
  --teachers mid 3slice --fit-temperature --out /data1/reports/teacher_tcal.json'
# 2) re-run the 2 passing cells with calibrated gate (sweep scaffold)
bash src/ops/remote_3090_calibrated_gate.sh        # new script, mirrors remote_3090_gapkd_sweep.sh
bash src/ops/remote_3090_calibrated_gate_summarize.sh
```

**Status:** NOT STARTED. **Compute:** ~60 runs, ~1.5 h on 4×3090.
**New files:** `src/ops/remote_3090_calibrated_gate.sh` (+ summarize),
`teacher_temperature` plumbing in `train_pseudolabel.py`.

---

## Method A3 — Overconfidence Stress Ablation (closes F3, evidence) ★★★

### Why
To *prove* the calibration safeguard matters, show the failure mode the reviewer
fears and then show the safeguard prevents it.

### Plan
Three teacher confidence regimes feeding the identical gate + student:
1. **Sharpened (overconfident) teacher:** apply `T < 1` (e.g. 0.5) so softmax is
   artificially peaked → simulates an uncalibrated overconfident teacher.
2. **Raw teacher:** current paper setting (`T = 1`).
3. **Calibrated teacher:** `T = T_cal` from A2.

Report, for each regime: teacher ECE, gate coverage, fraction of admitted
pseudo-labels that are *wrong*, and student ΔBA. Expected narrative: the
sharpened teacher admits more wrong targets and degrades or destabilizes the
student; the calibrated teacher admits fewer wrong targets and preserves the
gate pass. This directly answers "an uncalibrated teacher could force the student
to confidently learn incorrect distributions."

### Remote execution
- Same sweep scaffold, varying only the teacher temperature applied before
  masking (`{0.5, 1.0, T_cal}`) for the two passing cells.

**Status:** NOT STARTED. **Compute:** ~60 runs, ~1.5 h. Shares scaffold with A2.

---

## Method A4 — External X-ray-Only Validation (closes F1, baseline) ★★★

### Why
F1's minimum viable answer: take the **frozen deployed X-ray student** trained on
BIMCV and evaluate it, with no retraining, on independent external X-ray cohorts.
This is a true out-of-distribution test of the deployed artifact and produces the
absolute, cross-domain numbers the reviewer demands.

### Plan
1. **External cohorts.** Use the MIDRC pipeline already in the repo
   (`prepare_midrc_dataset.py`) plus at least one additional public COVID CXR
   set (preparation scaffolds exist: `download_noncovid_datasets.py`,
   `prepare_covid_dataset.py`). Build patient-level external manifests on `/data1`.
2. **Inference only.** Run the frozen BIMCV-trained student (supervised baseline
   AND the two passing JDCNet cells) on each external manifest via
   `jdcnet_exp.evaluate`.
3. **Report absolute** BA / ROC-AUC / macro-F1 / sensitivity / specificity with
   patient-level bootstrap CIs, per external cohort. The key comparison is
   JDCNet-student vs. supervised-student **under domain shift** — does the
   training-time CT signal still help when the test distribution moves?

### Remote execution
```bash
# build external manifests
bash src/tmp_sync/ssh3090.sh 'cd /data/JDCNET/src && python3 -m jdcnet_exp.prepare_midrc_dataset --out /data1/external/midrc'
# frozen-student external inference (no training)
bash src/ops/remote_3090_external_eval.sh   # iterates checkpoints × external manifests via jdcnet_exp.evaluate
```

**Status:** NOT STARTED. **Compute:** inference only, < 30 min single GPU.
**Risk:** MIDRC is largely X-ray/CT but not necessarily same-patient paired; for
A4 that is fine because A4 tests only the deployed X-ray student. Paired-cohort
replication is B1.

---

## Method B1 — External Paired-Cohort JDCNet Gate (closes F1, strongest) ★★

### Why
The decisive rebuttal to F1: replicate the *entire transfer claim* (teacher
upper bound + JDCNet gate + comparator audit) on a second same-patient paired
CT–X-ray cohort. If JDCNet passes the gate on a second cohort, the single-cohort
criticism collapses.

### Plan
1. Assemble a second same-patient paired CT–X-ray cohort. Candidate sources: the
   BIMCV-COVID19**−** negative release (`download_bimcv_neg_paired.py`,
   `prepare_bimcv_neg_dataset.py` already exist) to build an independent paired
   split, and/or MIDRC paired subjects where CT+CXR co-exist
   (`prepare_midrc_teacher_variants.py`, `prepare_mixed_bimcv_midrc_cv.py`).
2. Re-run the full pipeline on the new cohort: CT teacher pre-train → teacher
   upper-bound gate → JDCNet 16-cell grid → comparator audit, all under the same
   fixed gate and patient-level 5-fold CV.
3. Report whether the two BIMCV-passing configurations also pass externally.

### Remote execution
- Largest job: mirror the 240-run sweep used for the BIMCV headline. Reuse the
  config-gen + round-robin + screen scaffold; new tag e.g.
  `paired_external_cv_3090_<date>`.

**Status:** BLOCKED on data feasibility — needs confirmation that a genuinely
**same-patient paired** external CT–X-ray cohort can be assembled at usable
scale. **Compute (if unblocked):** ~240 runs, ~6 h on 4×3090.

> **Author decision needed:** is an external same-patient paired CT–X-ray cohort
> obtainable (BIMCV-neg paired build, MIDRC paired subjects, or other)? If yes,
> B1 becomes the headline F1 rebuttal. If no, F1 is answered by A4 + B2.

---

## Method B2 — Cross-Source Transfer Matrix (closes F1, quantifies gap) ★★

### Why
Make the generalization gap explicit and honest: train on BIMCV, test on
external (and reverse where data allows), reporting the absolute drop. This
converts F1 from a fatal flaw into a transparent, quantified external-validity
result.

### Plan
- 2×2 (or as data allows) train/test source matrix for the supervised baseline
  and the JDCNet student; report absolute BA/AUC in every cell and the
  same-source minus cross-source gap.
- Reuse `prepare_mixed_bimcv_midrc_manifest.py` for the mixed/cross manifests.

### Remote execution
- ~30 runs, round-robin 4 GPU, ~1.5 h. New script
  `src/ops/remote_3090_cross_source_matrix.sh`.

**Status:** NOT STARTED. **Depends on** A4 manifests.

---

## Method B3 — Calibrated-Quantile Gate Sweep (closes F3, robustness) ★

### Why
Show the gate decision is not a fragile fixed-τ artifact once calibration is in
place: replace the absolute threshold τ with a **calibrated-confidence quantile**
(e.g. keep top-q most-confident calibrated predictions) and confirm the passing
cells survive across q.

### Plan
- Sweep `q ∈ {0.5, 0.6, 0.7, 0.8}` on calibrated confidence for the two passing
  cells; confirm ΔBA stays positive and smooth (no sharp-threshold cliff).

### Remote execution
- ~90 runs, ~2.5 h. Extends the A2 calibrated-gate scaffold with a quantile mask
  mode.

**Status:** NOT STARTED. **Depends on** A2.

---

## Recommended Execution Order

```
1. A1  Absolute metrics (no GPU)              → closes F2 immediately
2. A2  Calibrate-then-gate (~1.5 h)           → closes F3 (mechanism)
3. A3  Overconfidence ablation (~1.5 h)       → closes F3 (evidence)
4. A4  External X-ray-only inference (<0.5 h) → closes F1 (baseline)
5. B2  Cross-source matrix (~1.5 h)           → closes F1 (quantified gap)
6. B3  Calibrated-quantile sweep (~2.5 h)     → F3 robustness
7. B1  External paired gate (~6 h) IF DATA    → strongest F1 rebuttal
```

A1–A4 are the minimum set that makes the paper resubmittable. B1 is the upgrade
path that, if data permits, removes F1 entirely.

---

## Infrastructure Notes

- **Compute:** 4× RTX 3090 at `mabo1215@10.147.20.176`, code `/data/JDCNET/src`,
  data `/data1`. All remote access **WSL-first** (`src/tmp_sync/ssh3090.sh`);
  never assemble complex remote commands in PowerShell.
- **Launch scaffold:** copy `src/ops/remote_3090_gapkd_sweep.sh` (config-gen →
  per-GPU queue → detached `screen` → `jdcnet_exp.train`/`evaluate`) for each new
  sweep; add a matching `*_summarize.sh`.
- **Calibration:** `jdcnet_exp.calibration_report` (ECE + reliability) extended to
  fit/persist per-fold teacher temperature.
- **Pseudo-label trainer:** `jdcnet_exp.train_pseudolabel` gains a
  `teacher_temperature` knob feeding the confidence mask.
- **External data:** `prepare_midrc_dataset.py`, `download_bimcv_neg_paired.py`,
  `prepare_bimcv_neg_dataset.py`, `prepare_mixed_bimcv_midrc_*` already present.
- **New scripts to add:** `src/ops/remote_3090_calibrated_gate.sh` (+summarize),
  `src/ops/remote_3090_external_eval.sh`, `src/ops/remote_3090_cross_source_matrix.sh`.
- **Artifacts:** each sweep → `src/results/<tag>_3090_<date>/` with a
  `*_decision_report.md` carrying ΔBA, 95% CI, win counts, PASS/FAIL, **and
  absolute metrics**.

---

## Paper Integration

For each completed method:
1. A1 → absolute-metric table in main text + abstract numbers (F2).
2. A2/A3/B3 → "Calibration Safeguard" Methodology subsection + calibration
   ablation table; update the gate-coverage/reliability paragraph (F3).
3. A4/B1/B2 → new "External Validation" experiments tier with absolute
   cross-domain numbers; soften single-cohort language in abstract, Introduction,
   and Limitations (F1).
4. Re-run `paper/build.bat`; confirm combined PDF ≤ 14 pages.
5. Update `docs/cover_letter.txt` to a point-by-point response to F1/F2/F3.
6. Update `docs/progress.md` (`## 已全部修改` / `## 未修改或部分修改` /
   `## 遗留问题`).

---

*Rewritten 2026-06-16 in response to the TCSVT reject decision in
`docs/revision_suggestions.tex`. Roadmap + priorities: `docs/revision_roadmap.md`.*
