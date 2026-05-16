# Validated Architecture Experiment Plan

## Purpose

This note turns the current evidence-bounded conclusion into an executable validation plan. The current GAP-KD/JDCNet-v2 variants have been implemented and stress-tested, but they have not been validated as a stable architecture-level improvement. The next experiment must therefore separate three roles:

1. **Mechanism selection**: already completed on BIMCV Path-C and MIDRC pilot.
2. **Locked candidate definition**: fixed before the next MIDRC validation run.
3. **Validation decision**: judged on a held-out paired MIDRC split without changing hyperparameters afterward.

## Current evidence boundary

- BIMCV Path-C plain CT logit KD is effectively tied with supervised X-ray: mean seed-paired \(\Delta\) is about `+0.002` balanced accuracy.
- The 27-run BIMCV threshold/projection sweep finds only one configuration that is positive against plain KD in all three seeds: `confidence_gate_threshold=0.55`, `projected_attention_weight=0.0`, with mean \(\Delta\) about `+0.0095` balanced accuracy.
- MIDRC short-proof confirms that the data pathway runs, but the candidate is seed-dependent: GAP-KD improves seeds 42 and 44 but loses seed 43.
- Projection-weighted variants are not consistently better than gating-only transfer.

Therefore, the next candidate should be deliberately conservative: **reliability-gated CT-to-X-ray logit KD without projection loss**.

## Locked candidate

Use this fixed candidate unless a new pre-registration note explicitly replaces it before running the final validation:

```json
{
  "distillation": {
    "enabled": true,
    "temperature": 4.0,
    "alpha": 0.6,
    "confidence_gate_enabled": true,
    "confidence_gate_threshold": 0.55,
    "confidence_gate_positive_threshold": -1.0,
    "confidence_gate_negative_threshold": -1.0,
    "confidence_gate_floor": 0.0,
    "confidence_gate_power": 1.0,
    "confidence_gate_requires_correct": true,
    "confidence_gate_min_margin": 0.0,
    "confidence_gate_max_entropy": -1.0,
    "projected_attention_weight": 0.0
  }
}
```

Rationale:

- `0.55` was the only threshold with stable positive BIMCV Path-C deltas when projection was disabled.
- `projected_attention_weight=0.0` avoids adding a loss that has not shown stable benefit.
- `confidence_gate_requires_correct=true` is allowed during training because labels are available; it blocks teacher soft targets when the teacher is wrong.
- Class-specific thresholds, margin, and entropy gates are implemented in code for future locked variants, but they should not be tuned on the final test set.

## Minimum validation matrix

Run only the decision-critical rows first:

| Row | Method | Purpose |
|---|---|---|
| 1 | CT teacher | Teacher feasibility on the same paired split |
| 2 | X-ray supervised | Main deployment baseline |
| 3 | Plain CT logit KD | Strong simple transfer baseline |
| 4 | Reliability-gated KD | Locked candidate architecture |

Do not add projection/anatomy variants until Row 4 passes the decision gate below.

## Dataset plan

### Preferred dataset

Use the largest available MIDRC same-patient CT--X-ray paired cohort after the 559-case download completes.

### Split requirements

- Patient-level split only; no image-level leakage.
- Use `train/val/test` splits, not a single validation split.
- Recommended fractions: `70/15/15`.
- Preserve class balance as much as possible; use `--negative-multiplier 1.0` during MIDRC preparation.
- The validation split is used for checkpoint selection; the test split is used for the validation decision.

### Minimum support before claiming validation

Do not claim validated architecture unless the held-out test split has enough positive and negative support to make balanced accuracy meaningful. A practical minimum is approximately:

- at least 50 positive and 50 negative test patients, or
- if the available cohort is smaller, explicitly retain the result as a pilot and do not use the word validated.

## Decision gate

The locked candidate can be upgraded to a validated architecture only if all conditions hold on the held-out test split:

1. Reliability-gated KD beats both X-ray supervised and plain KD in every seed.
2. Mean \(\Delta\) balanced accuracy versus both baselines is at least `+0.03`.
3. Macro-F1 moves in the same direction.
4. Specificity does not collapse relative to the supervised baseline.
5. No hyperparameter is changed after looking at test results.

If any condition fails, keep the paper's current evidence-bounded negative-result framing.

## Code changes now available

The implementation now supports a more explicit reliability gate:

- global confidence threshold
- optional positive-class and negative-class thresholds
- optional teacher top-1/top-2 margin threshold
- optional teacher entropy ceiling
- per-epoch gate diagnostics in `history.csv`:
  - `kd_gate_mean_weight`
  - `kd_gate_active_fraction`
  - `teacher_train_accuracy`
  - `teacher_train_mean_confidence`

These diagnostics help explain whether a failed run is caused by poor teacher reliability, excessive gate sparsity, or weak student transfer.

## Execution entrypoint

The locked validation script is:

```bash
bash src/ops/h800_midrc_locked_validation.sh
```

Important environment variables:

```bash
RAW_ROOT=/root/autodl-tmp/midrc/raw_559cases_combined
META=/root/autodl-tmp/JDCNET/src/data/midrc_manifests/MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.metadata.json
SEEDS="42 43 44"
EPOCHS=30
TRAIN_FRAC=0.70
VAL_FRAC=0.15
TEST_FRAC=0.15
GATE_THRESHOLD=0.55
AUTO_SHUTDOWN=0
```

The script prepares the MIDRC paired manifests if needed, trains the four locked rows, evaluates each best checkpoint on the test split, and writes:

- `$LOG_DIR/status.tsv`
- `$LOG_DIR/summary.csv`
- `$LOG_DIR/summary_stdout.txt`
- per-run `best_metrics.json`, `history.csv`, and `test_eval/metrics.json`

## What not to do

- Do not tune projection weights on the final MIDRC test set.
- Do not average post-hoc BIMCV and MIDRC results as if they were one confirmatory validation.
- Do not call the method validated if only mean performance improves but one seed fails.
- Do not use the mixed BIMCV+MIDRC positive-enriched screen as final validation.

## If the locked candidate fails

If reliability-gated KD fails the decision gate, the scientifically strongest conclusion remains:

> CT teachers are feasible, but the tested CT-to-X-ray transfer mechanisms do not provide a stable advantage over supervised X-ray learning under the available paired-cohort evidence.

That outcome still strengthens the paper as an evidence-bounded audit and negative-result benchmark.
