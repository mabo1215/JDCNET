# Pilot decision report

Cohort: 452 patients, 671 images. Usable weak boxes: 168 images from 113 patients. Overlay review was done by an AI model, not a clinician.

| Gate | Result | Threshold | Status |
|---|---|---|---|
| G1 coverage | 25.0% of images | >= 60% | FAIL |
| G1 overlay accuracy | 40/60 fully correct, 19 one axis only, 1 wrong | >= 80% fully correct | FAIL |
| G2 hit on erased images | 79.2% [73.2%, 85.2%] | >= 70% | PASS |
| G2 median box IoU, 2D boxes | 0.66 (centre prior 0.15) | >= 0.40 | PASS |
| G2 hit gain over centre prior | +34.5 [+26.4, +42.9] points | >= +15, CI excludes 0 | PASS |
| G3 series with >= 30 images at hit >= 60% | 2/2 series | >= 75% of series | PASS (only 2 series testable) |
| G4 raw minus erased hit | -3.0 [-9.3, +3.5] points | <= +10 | PASS |

Verdict under the pre-specified rule: NOT GO.

## Localisation detail

- Hit rate: erased 79.2%, raw 76.2%, centre prior 44.6%.
- Median box IoU on 2D boxes: erased 0.66, raw 0.50, centre prior 0.15.
- Negative control, lesion replaced by surrounding tissue: hit 53.0%, median IoU 0.13. Erased minus control: +26.2 [+18.8, +33.5] points.

| scanner         |   images |   patients |   hit_erased |   hit_prior |   boxes_2d |   iou_2d |
|:----------------|---------:|-----------:|-------------:|------------:|-----------:|---------:|
| ge_logiq        |      120 |         79 |        0.767 |       0.483 |        104 |    0.682 |
| siemens_sequoia |       45 |         34 |        0.867 |       0.378 |          7 |    0.355 |
| unidentified    |        3 |          2 |        0.667 |       0     |          3 |    0.401 |

## Classifier, descriptive only

This batch has no benign cases, so call rates are not diagnostic performance. Public labels come from radiologists according to the dataset description.

| operating_point      |   public_test_sensitivity |   public_test_specificity |   call_rate_erased |   call_rate_raw |   call_rate_lesion_removed | erased_minus_removed   | erased_minus_raw    |
|:---------------------|--------------------------:|--------------------------:|-------------------:|----------------:|---------------------------:|:-----------------------|:--------------------|
| spec80_on_public_val |                     0.699 |                     0.728 |              0.399 |           0.262 |                      0.286 | +11.3 [+5.1, +17.8]    | +13.7 [+7.3, +20.7] |
| sens90_on_public_val |                     0.881 |                     0.521 |              0.851 |           0.863 |                      0.792 | +6.0 [+0.0, +12.4]     | -1.2 [-6.7, +4.3]   |
