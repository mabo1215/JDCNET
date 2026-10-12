# Round-3 supplementary experiments: analysis plan (written before any run)

Date: 2026-10-13. This plan is committed to the repository before the runs below
are launched. Hardware: 4x RTX 3090 host, GPUs 0 and 1 only.

## Context

The 510-patient JDCNet sweep (16 configurations, batch size 128) was compared with
a supervised baseline trained with batch size 512 (Stage A). Configurations were
explored adaptively on the same cohort. Reviewer 6 asked about selection optimism
and the external test. This plan addresses (i) the training-budget confound,
(ii) selection by a validation-based nested procedure with a matched control,
(iii) patient-level uncertainty, and (iv) the external test with the actual
510-patient models.

## Fixed elements (unchanged from the original sweep)

- Splits: the five patient-level folds of the 510-patient cohort
  (`/data1/midrc/bimcv_full_paired_cv_20260516`), fold k = test, fold k+1 =
  validation, remaining folds = training; cells = 5 folds x seeds {42, 43, 44}.
- Code: the original training/evaluation code (`/data/JDCNET_git/src`), used read-only.
- Supervised configuration identical to Stage A except where stated.
- Existing JDCNet checkpoints and per-run metrics are not retrained.

## Experiment A: batch-matched supervised restarts

- 16 supervised runs per cell at batch size 128, training seeds
  `cell_seed + 1000 * r`, r = 0..15 (240 runs). Run r = 0 is the batch-matched
  baseline. Everything else as in Stage A (AdamW 3e-4, wd 1e-4, 50 epochs, AMP,
  weighted sampler, class-weighted CE, checkpoint by validation BA).

## Experiment B: per-image predictions

- Test-partition probabilities for: Stage A supervised (batch 512), the new
  supervised runs, all 240 JDCNet runs, and the Stage A logit-KD runs.
- External MIDRC locked-validation set (126 radiographs, 63/63): probabilities
  for the same checkpoints.

## Experiment C: teacher calibration (CPU)

- Re-render the CT teacher views from the NIfTI volumes with the original
  rendering script; accept only if the re-run Stage A teacher test metrics match
  the recorded ones. If they match: per fold/seed coverage of the gate at
  tau in {0.60, 0.70, 0.80, 0.85}, retained-vs-rejected teacher accuracy, ECE,
  and a validation-fitted temperature.

## Pre-specified analyses

1. Batch-matched comparison: paired test-BA difference of each of the 16 JDCNet
   configurations against the r = 0 batch-128 baseline (bootstrap CI, paired t,
   Holm over 16).
2. Nested selection with matched control (primary): in each cell, choose the
   JDCNet configuration with the highest validation BA, and choose the supervised
   restart with the highest validation BA among r = 0..15; compare their test BA.
   Report mean difference, bootstrap CI over cells, paired t-test.
   Reading: if the CI excludes zero, the JDCNet advantage is not explained by
   best-of-16 selection or the batch size; otherwise it is not supported.
3. Patient-level bootstrap (10,000 resamples of patients, pooling the three seeds
   per patient) for analyses 1-2 using per-image predictions.
4. External test: BA/AUC with CIs for the 510-patient supervised and JDCNet
   models; paired DeLong test for AUC and McNemar-type comparison per checkpoint
   pair, aggregated over checkpoints.
5. All results are reported whatever their direction.
