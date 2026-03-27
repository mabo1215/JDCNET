# Progress Log

## 2026-03-27

### Completed

- confirmed that `paper/` is a nested project directory and added a PDF build workflow
- built a reproducible experiment scaffold in `src/` for teacher/student training, distillation, evaluation, manifest preparation, and paper asset export
- connected the local dataset at `D:\source\covid-chestxray-dataset` to the experiment pipeline and generated executable manifests for `xray_all`, `ct_all`, and the paired `CT -> X-ray` cohort
- ran the real-data experiment matrix with repeated seeds, late-fusion, temperature/alpha ablation, and module ablations (`w/o DPE`, `w/o MHRA`, `w/o DFPN`)
- added configurable DPE/MHRA/DFPN switches and paired-input late-fusion support in the executable code
- added `src/jdcnet_exp/download_kaggle_datasets.py` and downloaded curated Kaggle CT/MRI and COVID imaging datasets into `src/data/kaggle/`
- reframed the paper into an honest reproducible pilot study after the repeated runs showed that late fusion and cross-modality distillation do not stably beat the student-only paired-cohort baseline
- created `paper/build.sh` and verified that the submission package can now build separate `main.pdf` and `appendix.pdf` outputs from the shell entrypoint
- created `paper/appendix.tex` as a standalone supplementary document
- added `src/jdcnet_exp/generate_submission_assets.py` so the submission tables and appendix assets are generated from code instead of being hardcoded in LaTeX
- replaced the hardcoded main-text cohort table and main results table with generated LaTeX inputs under `paper/tables/generated/`
- generated and inserted appendix-ready reproducibility assets:
  - patient-level split audit table
  - per-seed paired-cohort results table
  - module ablation summary table
  - per-seed instability figure
- cleaned `paper/references.bib` to keep only cited, relevant medical-imaging references plus the dataset citation
- added explicit dataset citations and a dataset-curator caution in the experiments section
- strengthened the method text so the DPE, MHRA, and DFPN descriptions now map more directly to the current executable implementation
- regenerated the key paper figures with per-seed overlays to make result instability visually explicit
- added a qualitative appendix-level error-analysis table for the four paired validation cases using representative seed-42 checkpoints
- replaced the earlier conceptual architecture panel with a code-generated implementation-faithful schematic and added an appendix implementation-details table generated from the executable scaffold
- removed unstable secondary metrics from the main-text headline table so the manuscript now emphasizes only the more defensible repeated-run comparisons under the tiny paired split
- added seed-aggregated paired confusion summaries that make the dominant false-positive bias explicit without treating repeated predictions as a larger independent test set
- split `main.tex` and `appendix.tex` into separately compiled PDFs and removed cross-file numbered appendix references from the main paper so standalone appendix builds do not produce `??` references
- rebuilt the PDF successfully after the manuscript/package changes

### In Progress

- assessing whether any additional negative-result analysis can still be extracted from the current tiny validation split without turning repeated predictions into pseudo-samples

### Next

- identify the minimum additional experiment that would most directly test the core novelty once more paired data become available
- if no stronger evidence can be added from the current repository, keep tightening the framing toward a rigorous negative-result-informed feasibility paper rather than a performance-claim paper

### Exact Changed Files

- `paper/main.tex`
- `paper/appendix.tex`
- `paper/references.bib`
- `paper/build.sh`
- `paper/build.ps1`
- `paper/tables/generated/dataset_protocol.tex`
- `paper/tables/generated/main_results.tex`
- `paper/tables/generated/split_audit.tex`
- `paper/tables/generated/module_ablation.tex`
- `paper/tables/generated/paired_seed_results.tex`
- `paper/tables/generated/failure_cases.tex`
- `paper/tables/generated/implementation_details.tex`
- `paper/tables/generated/paired_confusion_summary.tex`
- `paper/images/generated/covid_matrix_main.png`
- `paper/images/generated/covid_matrix_module_ablation.png`
- `paper/images/generated/covid_paired_seed_instability.png`
- `paper/images/generated/jdcnet_executable_architecture.png`
- `paper/images/generated/paired_confusion_summary.png`
- `src/jdcnet_exp/models.py`
- `src/jdcnet_exp/data.py`
- `src/jdcnet_exp/train.py`
- `src/jdcnet_exp/evaluate.py`
- `src/jdcnet_exp/run_covid_matrix.py`
- `src/jdcnet_exp/download_kaggle_datasets.py`
- `src/jdcnet_exp/generate_submission_assets.py`
- `src/jdcnet_exp/generate_error_analysis.py`
- `src/results/covid_matrix_summary.csv`
- `src/results/covid_matrix_per_run.csv`
- `src/results/covid_matrix_module_ablation.csv`
- `src/results/covid_dataset_summary.json`
- `src/results/kaggle_download_report.json`
- `src/results/submission_assets_report.json`
- `src/results/failure_analysis_report.json`
- `paper/results/paired_failure_analysis.csv`
- `paper/results/paired_confusion_summary.csv`

### Experiments Run

- `python -m jdcnet_exp.run_covid_matrix --force`
- `python -m jdcnet_exp.download_kaggle_datasets`
- `python -m jdcnet_exp.generate_submission_assets`
- `python -m jdcnet_exp.generate_error_analysis`

### Figures and Tables Regenerated

- `paper/images/generated/covid_matrix_main.png`
- `paper/images/generated/covid_matrix_ablation.png`
- `paper/images/generated/covid_matrix_module_ablation.png`
- `paper/images/generated/covid_paired_seed_instability.png`
- `paper/images/generated/jdcnet_executable_architecture.png`
- `paper/images/generated/paired_confusion_summary.png`
- `paper/tables/generated/dataset_protocol.tex`
- `paper/tables/generated/main_results.tex`
- `paper/tables/generated/split_audit.tex`
- `paper/tables/generated/module_ablation.tex`
- `paper/tables/generated/paired_seed_results.tex`
- `paper/tables/generated/failure_cases.tex`
- `paper/tables/generated/implementation_details.tex`
- `paper/tables/generated/paired_confusion_summary.tex`

### Top 10 Submission Blockers

1. `Cross-modality novelty is not supported by a stable gain over the strongest paired-cohort baseline`
   - status: `partially resolved`
   - action taken: reframed the manuscript into a reproducible pilot study and removed the earlier positive-overclaim wording
   - remaining gap: no amount of writing can replace the missing empirical gain

2. `Validation protocol is too weak because the paired validation split has only four X-ray images`
   - status: `unresolved`
   - action taken: surfaced the exact split sizes in the main text and appendix, added per-seed instability reporting, and avoided stronger claims
   - remaining gap: requires more paired data

3. `MHRA is described as an innovation but is not positively validated`
   - status: `partially resolved`
   - action taken: added executable module ablations and weakened the claim
   - remaining gap: current ablations show that removing MHRA slightly improves the mean result

4. `Main-text tables were manually hardcoded instead of being generated from executable outputs`
   - status: `resolved`
   - action taken: added `generate_submission_assets.py` and replaced the main tables with generated LaTeX inputs

5. `The submission package was incomplete because `paper/build.sh` and `paper/appendix.tex` were missing`
   - status: `resolved`
   - action taken: created both files and verified `bash paper/build.sh`

6. `The bibliography contained a large number of irrelevant / duplicate / non-medical-imaging entries`
   - status: `resolved`
   - action taken: replaced `paper/references.bib` with a clean, cited-only bibliography

7. `Dataset protocol and leakage defense were not explicit enough`
   - status: `partially resolved`
   - action taken: added dataset citations, dataset-curator caution, split audit table, explicit train/val patient counts, and reduced the main-text headline table to accuracy, macro-F1, and balanced accuracy
   - remaining gap: the current split is still too small for a submission-grade benchmark protocol

8. `Figure evidence did not clearly communicate run-to-run instability`
   - status: `resolved`
   - action taken: regenerated the main and module-ablation figures with per-seed overlays, added an appendix instability figure, and added seed-aggregated paired confusion summaries to make the dominant false-positive pattern explicit

9. `Appendix-level reproducibility detail and implementation-faithful packaging were missing`
  - status: `resolved`
  - action taken: added appendix sections for split audit, per-seed results, module ablations, representative failure cases, implementation details, and implementation-faithful manuscript assets

10. `The current executable architecture/backbones are still lightweight research scaffolds rather than submission-grade final models`
   - status: `unresolved`
   - action taken: aligned the manuscript wording with the actual implementation and explicitly described the scaffold nature
   - remaining gap: requires substantial modeling work or stronger data to justify it

### Former Revision-Suggestion Items

- `Revised abstract`: `resolved`
- `Introduction restructuring`: `resolved`
- `Related work restructuring`: `resolved`
- `Method top-down rewrite`: `resolved`
- `Late-fusion baseline`: `resolved`
- `Temperature / alpha ablation`: `resolved`
- `Module ablations (w/o DPE / MHRA / DFPN)`: `resolved`
- `Implementation and reproducibility section`: `resolved`
- `Discussion and limitation framing`: `resolved`
- `Target venue positioning text inside the main paper`: `intentionally unresolved`
  - reason: this belongs in internal notes, not in the manuscript
