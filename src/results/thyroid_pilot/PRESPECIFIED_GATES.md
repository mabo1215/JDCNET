# Pilot gates, fixed before any model result was seen (2026-11-04)

Question: can a lesion be located automatically in this surgically confirmed thyroid cancer
ultrasound batch, well enough to justify requesting pathology and CT/MR records?
Reference standard: caliper-derived weak lesion boxes. Calipers are erased from model inputs.

| Gate | Definition | Pass |
|---|---|---|
| G1 weak labels | Auto extraction yields a usable box, and sampled overlays are visually correct | >= 60% of images and >= 80% of at least 50 sampled overlays |
| G2 localisation | External model on erased images: pointing hit rate and median box IoU, versus a centre-prior baseline | hit >= 70%, IoU >= 0.40, hit gain >= 15 points with patient-bootstrap 95% CI excluding 0 |
| G3 cross-scanner | Hit rate per scanner series with >= 30 usable images | at least 75% of those series >= 60% |
| G4 caliper reliance | Hit rate on raw images minus hit rate on erased images | <= 10 points |

Verdict: GO needs all four. Malignancy-classifier sensitivity is descriptive only and not a gate,
because this batch has no benign cases and specificity cannot be measured here.
A GO means lesions can be found. It does not show that cancer can be diagnosed or outcomes predicted.

## Metric definitions, added before any model result was seen

- Pointing hit: the centroid of the largest predicted component falls inside the reference region.
  A missing prediction counts as a miss.
- Reference region: the weak box. If only one axis was measured, the short side is widened
  symmetrically to 60% of the long side.
- Box IoU is computed only on truly 2D boxes (short side >= 30% of long side).
- Centre prior: cohort mean centre and median size. This baseline is given cohort knowledge,
  so the comparison is conservative.
- Patient-level bootstrap with 2000 resamples for every confidence interval.
- Occlusion control for the classifier: replace the weak lesion box with inpainted surrounding
  tissue. A classifier that reads the lesion should lower its malignant call rate.
