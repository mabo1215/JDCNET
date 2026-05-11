# Experiment Plan

Updated 2026-05-11 after the RTX 3090 Path C re-split completed.

## Current decision

The current submission should stay evidence-bounded. The available experiments
support CT-teacher feasibility, but they do not validate a stable positive
cross-modal KD effect over an X-ray-only supervised student.

## Completed and retained evidence

- Patient-level paired manifests and split audits are implemented.
- Teacher-only, student-only, same-modality KD, plain cross-modal logit KD,
  attention-transfer, feature-hint, full JDCNet, and generic KD baselines have
  been evaluated under the primary same-case resampling protocol.
- BIMCV 512-patient stress tests have evaluated:
  - custom-CNN capacity limits across two execution environments;
  - ResNet-18 teacher/student capacity;
  - prototype-augmented KD at three weights;
  - DRR-based geometric anchoring;
  - corrected larger-holdout evaluation;
  - the final Path C balanced-validation re-split on the RTX 3090 execution environment.
- The RTX 3090 Path C numerical artifacts have been moved to
  `src/results/bimcv_pathc_3090/`.

## Removed from the pre-submission experiment plan

These items are no longer planned for the current submission because the
completed experiments show that they do not rescue a validated transfer claim on
this cohort:

- More DRR-anchor variants on the same BIMCV split.
- More prototype-KD weights on the same BIMCV split.
- DRR+attention+prototype kitchen-sink variants.
- More re-splits of the same 512-patient BIMCV cohort.
- Memory-bank or contrastive extensions on the same cohort.
- Lung-mask attention as a current-submission requirement.

## New code path opened for the next algorithm

GAP-KD/JDCNet-v2 replaces the failed DPE/MHRA/DFPN upgrade path with a
geometry-aware, anatomy-constrained, confidence-gated distillation route. The
current repository now includes CPU-testable primitives for:

- confidence-gated soft KD;
- projection-compatible attention alignment;
- one-step synthetic GAP-KD training smoke tests.

The local smoke test passed and wrote its report to
`src/results/gapkd_cpu_smoke_local/smoke_gapkd.json`. The H800 no-card CPU
smoke test also passed and wrote its report to
`src/results/h800_gapkd_cpu_smoke/smoke_gapkd.json`.

This is an implementation readiness step, not paper evidence. No manuscript
result should claim GAP-KD effectiveness until it is evaluated on a valid
paired cohort.

## Conditional next experiment only if a new paired cohort is available

A new experiment is worth starting only if it adds genuinely new same-patient
paired support rather than rearranging the existing BIMCV cohort. The minimum
useful cohort should preserve both training and validation positive support and
should include enough negative validation patients for the corrected holdout
protocol.

Minimum comparison set:

1. X-ray supervised student.
2. CT teacher feasibility row.
3. Plain CT-to-X-ray logit KD.
4. Confidence-gated KD.
5. Confidence-gated projection/anatomy-constrained KD, only if the cohort is
   large enough to support interpretable paired statistics.

Primary metrics:

- balanced accuracy;
- sensitivity and specificity;
- macro-F1;
- ROC-AUC and PR-AUC;
- paired Wilcoxon or sign-test analysis over same-case resamples.

## Current manuscript action

No additional result-bearing experiment is required before the current
paper-facing revision. The manuscript should present Path C as a negative
split-sensitivity check: CT teacher remains feasible, but cross-modal logit KD
remains effectively tied with supervised learning. GAP-KD is a new
pre-specified next-framework route and must remain separate from the current
paper's validated evidence claims until run on a suitable cohort.
