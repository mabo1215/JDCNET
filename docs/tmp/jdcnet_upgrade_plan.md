# JDCNet Upgrade Plan: Final Feasibility Status

Updated 2026-05-11 after the RTX 3090 Path C balanced-validation re-split.

## Executive decision

The attempted upgrade from **evidence-bounded protocol** to **validated
architecture** did not succeed on the available BIMCV cohort. The strongest
scientific conclusion is now:

> CT teachers are feasible and reproducible on a larger paired thoracic cohort,
> but cross-modal CT-to-X-ray KD remains unstable or effectively tied with an
> X-ray-only supervised student. The current paper should not claim validated
> positive transfer.

## Evidence summary

| Evidence layer | Result | Decision |
|---|---|---|
| Custom-CNN BIMCV executions A/B | CT teacher feasible; KD unstable, including one zero-recall collapse | Retain as instability evidence |
| ResNet-18 execution C | Capacity improves supervised and teacher rows; KD remains tied with supervised under resampling | Retain as capacity-control evidence |
| Prototype-KD execution D | No weight beats supervised; high weight becomes harmful under corrected evaluation | Do not extend before submission |
| DRR execution E | Initial gain was a small-holdout variance artifact; corrected protocol gives no benefit | Do not extend before submission |
| Path C re-split on RTX 3090 | CT teacher BA 0.729 ? 0.026; supervised BA 0.623 ? 0.012; KD BA 0.626 ? 0.010; mean paired delta +0.002 | Confirms no validated transfer |

The RTX 3090 Path C artifacts are stored in `src/results/bimcv_pathc_3090/`:

- `summary.csv` for per-run metrics;
- `aggregate_summary.csv` for paper-facing method aggregates;
- `paired_seed_delta.csv` for seed-paired KD-minus-supervised deltas;
- `runs/*/best_metrics.json` for per-run provenance.

## Why the previous upgrade routes are no longer feasible on the same cohort

### DRR geometric anchoring

DRR was the most plausible architecture-level fix because it addresses the
axial-CT versus coronal-X-ray geometry gap. The corrected evaluation shows that
its apparent benefit was caused by the noisy 5--10-patient holdout protocol.
With 33 validation patients per resample, DRR-KD is essentially null. This route
is removed for the current submission.

### Prototype alignment

Prototype-KD widened the information channel beyond binary logits, but the
best weight still failed against supervised learning and the high-weight variant
became significantly harmful under corrected evaluation. More weight sweeps are
not justified before submission.

### Path C re-splitting

Path C increased positive validation support by moving positive cases from
training into validation. This was useful as a split-sensitivity test, but it
lowered training positive support and did not improve KD over supervised.
More re-splits of the same 512 patients are not a credible path to validated
architecture claims.

### Lung masks, memory banks, and multi-slice teachers

These may be useful in a future larger-cohort study, but on the current cohort
they would add mechanism complexity without solving the demonstrated evidence
limit. They are removed from the current pre-submission plan.

## Manuscript framing to keep

Use the BIMCV series as a boundary check, not as a positive upgrade:

- CT teacher feasible at larger scale.
- Stronger ResNet-18 learners remove trivial collapse but do not create stable
  transfer gains.
- DRR and prototype mechanisms do not improve over plain CT logit KD when the
  evaluation protocol is corrected.
- A balanced-validation re-split on the same cohort still leaves KD tied with
  supervised learning.

Recommended wording: **"CT teacher feasible + cross-modal KD not yet validated"**.
Avoid wording such as **"validated architecture"**, **"confirmed positive
transfer"**, or **"DRR solves the modality gap"**.

## New algorithm route: GAP-KD / JDCNet-v2

The next architecture should not extend the failed DPE/MHRA/DFPN stack. The
new route is **GAP-KD: geometry-aware, anatomy-constrained, confidence-gated
CT-to-X-ray distillation**. Its central rule is:

> Transfer CT supervision only when the teacher is reliable and the CT evidence
> can be expressed in the deployed X-ray view.

Minimum components:

1. **Confidence-gated KD**: reweight the soft KD term per sample using teacher
   confidence and optional teacher-correctness filtering, while keeping the
   hard supervised X-ray loss active for every sample.
2. **Projection-compatible attention**: align the student X-ray attention to a
   projected CT evidence map, preferably DRR/MIP-derived rather than raw axial
   CT feature maps.
3. **Anatomy-constrained transfer**: when lung masks are available, suppress
   extra-thoracic attention and make shortcut transfer auditable.
4. **Source-bias controls**: retain cross-source non-COVID controls and
   source-stratified validation when a new dataset supports them.

The initial implementation now supports confidence-gated KD and
projection-compatible attention as code-level primitives. The local CPU smoke
test is stored under `src/results/gapkd_cpu_smoke_local/`.

## Only remaining high-value evidence route

A new paired thoracic cohort is required. It must add new patients rather than
re-splitting BIMCV. A reasonable next-cohort protocol should include:

1. patient-level paired CT and X-ray data;
2. enough positive and negative validation patients for corrected same-case
   resampling;
3. X-ray supervised, CT teacher, and plain CT-to-X-ray logit KD as mandatory
   rows;
4. confidence-gated KD and projection/anatomy-constrained KD only after the
   simple CT logit KD row is interpretable.

MIDRC or NLST may be useful only if the downloaded data can provide valid
same-patient CT/X-ray pairs with labels that match the binary thoracic target.
Until that audit is complete, the current paper should close with the
available negative-evidence stack rather than launching more BIMCV variants.

## Current status checklist

- [x] RTX 3090 Path C training complete.
- [x] RTX 3090 Path C numerical artifacts moved under `src/results/`.
- [x] Path C result backfilled into the manuscript.
- [x] DRR/prototype/re-split routes removed from the current experiment plan.
- [x] GAP-KD/JDCNet-v2 code primitives added and locally smoke-tested on CPU.
- [x] H800 CPU/no-card smoke test launched and result pulled back under
      `src/results/h800_gapkd_cpu_smoke/`.
- [ ] Optional only: audit a new paired data source if the authors want a future
      post-submission or next-paper experiment.
