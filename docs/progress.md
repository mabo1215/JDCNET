# Progress Log

## 2026-03-27

### Completed

- confirmed that `paper/` is a nested project directory and added a build workflow that generates PDF into `paper/build/`
- reviewed the current manuscript structure and identified major submission blockers for TMI/MICCAI
- created a written submission gap analysis in `docs/submission_gap_analysis.md`
- built a reproducible experiment code skeleton in `src/`, including config loading, dataset manifests, teacher/student models, distillation loss, training, and evaluation entrypoints
- completed a first paper revision pass focused on title, abstract, keywords, contributions, section naming, conclusion, and journal-style author formatting
- recompiled the manuscript successfully and regenerated `paper/build/main.pdf`
- added a paper-asset generation script in `src/` that exports summary figures and CSV results into `paper/images/generated/` and `paper/results/`
- updated the experiments section so the paper now references the generated figures, corrected repeated-run summary statistics, and aligns the experimental explanation with the available results
- added MICCAI readiness tracking in `docs/miccai_readiness.md`
- expanded the experiment scaffold with patient-level split generation, ablation config generation, run aggregation, learning-curve export, and confusion-matrix export
- rewrote the most problematic part of the method section to reduce theorem/proof style claims and replace them with implementation-oriented explanations
- added explicit experiment configs for teacher-only, student-only, same-modality distillation, and cross-modality distillation settings
- connected the local real dataset at `D:\source\covid-chestxray-dataset` to the experiment pipeline
- generated executable manifests for `xray_all`, `ct_all`, and the paired `CT -> X-ray` distillation cohort under `src/data/covid_real/`
- upgraded the training code to support separate teacher and student inputs for real cross-modality distillation
- ran the full real-data experiment matrix: teacher-only, student-only, same-modality distillation, cross-modality distillation, repeated runs across four seeds, and temperature/alpha ablation
- exported the new real-data CSV summaries and figures into `paper/results/` and `paper/images/generated/`
- replaced the old placeholder experiment narrative in `paper/main.tex` with a real-data protocol, quantitative results, ablation discussion, and an explicit limitations section

### In Progress

- tightening the method section so that every architectural claim maps cleanly to the current executable implementation
- assessing what additional paired data and stronger backbones are needed before the paper can approach MICCAI quality

### Next

- expand the paired cohort or add an external held-out cohort because the current paired validation set has only four X-ray images
- replace the current lightweight teacher/student scaffold with a stronger and more defensible JDCNET implementation
- add a submission-grade dataset protocol section covering inclusion criteria, preprocessing, runtime, and failure cases
