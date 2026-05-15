# H800 MIDRC 559 Readiness Audit (2026-05-13)

## Scope

This note records the H800 no-GPU/no-card readiness check for the locked MIDRC validation experiment described in `docs/VALIDATED_ARCHITECTURE_EXPERIMENT_PLAN.md`.

Raw command output is stored in:

- `src/tmp_sync/h800_midrc_readiness_audit_20260513.txt`
- `src/tmp_sync/h800_locked_code_smoke_20260513.txt`

## H800 compute mode

- Host: `autodl-container-092840bd03-905c7945`
- Audit time: `2026-05-13T14:45:27+08:00`
- GPU status: `nvidia-smi` returns `Permission denied`, consistent with no-card mode.
- Consequence: CPU code-path validation is possible; actual training for the locked validation matrix should wait for GPU/card mode.

## Code feasibility check

The updated GAP-KD/JDCNet-v2 code was synchronized to H800 and passed the CPU synthetic smoke test:

- model build: pass
- forward feature extraction: pass
- confidence gate: pass
- gated KD and projected attention losses: pass
- one-step student update: pass

Smoke status: `5/5` checks passed on CPU.

## MIDRC 559 data availability on H800

H800 has the expected MIDRC 559 raw download footprint:

- raw root: `/root/autodl-tmp/midrc/raw_559cases_combined`
- size: `138G`
- recursive ZIP count: `1118`
- metadata cases: `559`
- metadata label counts: `69` COVID-positive, `490` COVID-negative
- ZIP map entries: `1118`
- sampled ZIP central directories: readable

The raw ZIP count matches the expected two objects per case for 559 paired cases.

## Balanced chest subset for locked validation

Using the current `prepare_midrc_dataset` selection logic with:

- `--only-chest`
- `--negative-multiplier 1.0`
- seed `42`
- split fractions `0.70/0.15/0.15`

H800 can form a balanced chest subset:

| Split | Negative | Positive |
| --- | ---: | ---: |
| train | 44 | 44 |
| val | 9 | 9 |
| test | 10 | 10 |
| total | 63 | 63 |

Missing raw ZIPs for this selected subset: `0` cases.

## Existing data products on H800

- `pilot_balanced_126`: exists, 126 rows, 126 patients, 63/63 label balance, image paths sampled as present.
- `generated_559` manifest: exists, 612 rows, 557 patients, 122 positive rows and 490 negative rows; sampled paths point to existing raw ZIPs.
- `mixed_midrc_bimcv`: exists, 187 rows, positive-enriched (`124` positive / `63` negative); use only as a diagnostic screen, not as the final balanced validation cohort.
- `locked_validation`: not generated yet.

## Ratio-adjustment code paths

Two existing code paths can control class ratios:

1. `src/jdcnet_exp/prepare_midrc_dataset.py`
   - `--negative-multiplier` controls the negative-to-positive case selection ratio for MIDRC.
   - `assign_splits` applies stratified train/val/test assignment by label.
   - Recommended for locked validation: use `--negative-multiplier 1.0` and patient-level stratified splits.

2. `src/jdcnet_exp/prepare_mixed_bimcv_midrc_manifest.py`
   - `--target-train-positive-ratio`, `--target-val-positive-ratio`, `--target-test-positive-ratio`
   - `--sampling-mode upsample|downsample`
   - Recommended use: diagnostic mixed-cohort screens only. Do not upsample/duplicate the final validation test set.

## Readiness decision

Ready now:

- H800 has the raw MIDRC 559 paired ZIP footprint.
- H800 has the required metadata and prior manifests.
- The modified code passes CPU/no-card smoke validation.
- Class-ratio control exists in the data-preparation code.
- The locked 4-row validation script exists at `src/ops/h800_midrc_locked_validation.sh`.

Not ready yet:

- H800 is currently in no-card mode, so full training should not be launched yet.
- `/root/autodl-tmp/midrc/locked_validation` has not been generated yet.
- The final validated-architecture claim still requires the locked 4-row matrix to pass the predefined decision gate on the held-out test split.

Minimum next step before training:

```bash
cd /root/autodl-tmp/JDCNET/src
bash src/ops/h800_midrc_locked_validation.sh
```

Run this after switching H800 back to GPU/card mode. The script will prepare `locked_validation` if missing, then run CT teacher, supervised X-ray, plain CT-logit KD, and reliability-gated KD over three seeds.
