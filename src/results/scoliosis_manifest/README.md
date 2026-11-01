# Scoliosis imaging: pseudonymized manifest

Entry point for experiments on the scoliosis imaging export received from a
collaborating hospital (site code `SC`).
This README holds aggregate counts only; the per-patient CSV files in this
folder are excluded from version control by the repository ignore rules.

Regenerate (from `src/`): `python -m scoliosis_exp.manifest`.
Resolve images: `scoliosis_exp.manifest.series_dir(series_uid)`.

## Cohort

- Patients: 25; studies: 59; series: 400; images: 11645.
- First-exam year distribution: 2022: 4, 2023: 10, 2024: 6, 2025: 5.
- Every patient in the export is a scoliosis patient; there are no negative controls.
- No diagnostic labels (Cobb angle, curve type, surgical status) are included.

| Modality | Series | Training-eligible series | Images |
|---|---:|---:|---:|
| DR | 32 | 32 | 193 |
| CT | 45 | 36 | 6813 |
| MR | 323 | 273 | 4639 |

## Same-patient pairing

- Radiograph (any) + CT axial: 11 patients; gap between nearest exams: median 0 d, range 0-14 d, same day 7, within 30 d 11.
- Whole-spine radiograph + CT axial: 5 patients.
- Radiograph + MR: 19 patients; gap: median 1 d, range 0-92 d, same day 4, within 30 d 17.
- Radiograph + CT axial + MR: 10 patients.
- Patients with a CT scout (AP/lateral topogram): 11.
- Patients with at least one stitched whole-spine radiograph: 11.

## Series roles

| Role | Series | Images | Burned-in identifiers | Training-eligible |
|---|---:|---:|---|---|
| `ct_axial` | 24 | 6069 | spot_checked | yes |
| `ct_dose_report` | 1 | 1 | confirmed | no |
| `ct_rendered_film_aw` | 6 | 540 | confirmed | no |
| `ct_rendered_film_display` | 2 | 180 | spot_checked | no |
| `ct_scout` | 12 | 23 | not_observed | yes |
| `dr_regional` | 20 | 71 | not_observed | yes |
| `dr_whole_spine` | 12 | 122 | not_observed | yes |
| `mr_localizer` | 45 | 376 | spot_checked | no |
| `mr_screen_save` | 5 | 15 | not_observed | no |
| `mr_sequence` | 273 | 4248 | spot_checked | yes |

Radiograph images (excluding 9 byte-identical duplicates): detector_segment 79, single_exposure 71, stitched_whole_spine 34.

## Data limitations

- The export is 8-bit JPEG after display windowing: no Hounsfield units, pixel spacing,
  slice thickness, patient orientation or acquisition parameters are available. CT window
  settings differ between series (bone, soft tissue, lung). DICOM originals should replace
  these images for quantitative work.
- CT coverage differs between patients (cervical, chest, thoracolumbar); the scout series
  shows the scanned range.
- Radiograph view (AP versus lateral) is known only when the series description states it;
  stitched whole-spine series contain both views without a per-image tag.

## Privacy

- Pseudonymous identifiers: patient `SCnnn`, study `SCnnn_stNN`, series `SCnnn_stNN_seNN`,
  radiograph image `<series>_imNNN`. Studies are numbered chronologically per patient at
  first assignment; identifiers never change once assigned.
- Exact dates are replaced by the exam year and the day offset from the patient's first exam.
- The linkage key (pseudonymous id to hospital id and raw path) is stored next to the raw
  data under `data/` and is not under version control. Do not copy it elsewhere.
- `ct_rendered_film_aw` and `ct_dose_report` series show the patient name, hospital id, birth
  date, exam date or study id in the pixels; never use them in training data or figures.
- `phi_burned_in` values come from a visual review on 2026-11-01: `not_observed` means one
  image of every series in that role was inspected; `spot_checked` means a sample of series
  was inspected. Re-check any image before it appears in a publication figure.
- Publication use requires documented ethics approval and a data use agreement.

## Files

- `patients.csv`: one row per patient (modality availability, image counts, minimum day gap
  between radiograph and CT/MR exams, follow-up span).
- `studies.csv`: one row per study (modality, exam year, day offset, series and image counts).
- `series.csv`: one row per series (role, description, series number, image count, dominant
  size, region/view for DR, kernel/slice thickness for CT, weighting/plane/contrast/fat
  suppression for MR, `derived_from` linking Philips `e`-prefixed derived series to their
  source acquisition, `phi_burned_in`, `use_for_training`).
- `dr_images.csv`: one row per radiograph image (detector segment, stitched whole-spine
  composite or single exposure; size; MD5; `duplicate_of` for byte-identical copies).
