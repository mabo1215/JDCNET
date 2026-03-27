You are operating inside my local research repository.

Project structure:
- paper/main.tex              # main manuscript
- paper/appendix.tex          # appendix
- paper/references.bib        # bibliography
- paper/build.sh              # build PDF
- src/                        # experiment and figure generation code
- docs/progress.md            # progress tracker that must be kept updated

Mission:
Transform this repository into a submission-grade medical imaging paper package through iterative, evidence-driven improvement. Your goal is NOT to cosmetically polish the paper. Your goal is to make the manuscript, experiments, figures, and claims internally consistent, reproducible, and as close as possible to a strong submission for a top medical imaging venue.

Critical rule:
Do not fabricate results, citations, datasets, baselines, or implementation details. Every claim in the manuscript must be backed by executable code, generated results, or clearly labeled limitation/future work. If evidence is insufficient, weaken the claim and add the missing experiment/task to progress tracking instead of overstating.

Current repository context you must respect:
- The current manuscript is a preprint under revision for a medical imaging venue.
- The current paired validation split is extremely small.
- Existing results do NOT yet show stable improvement for late fusion or cross-modality distillation over the student-only baseline.
- The current MHRA module is not yet robustly validated.
- The paper already has executable experiment scaffolding and generated figures/results.
- docs/progress.md records completed, in-progress, and next tasks; keep it synchronized with actual code, generated assets, and manuscript changes.

Primary objectives:
1. Audit the full paper and codebase for submission blockers.
2. Improve the scientific positioning, novelty articulation, experimental rigor, reproducibility, figure quality, and writing quality.
3. Automatically run or extend experiments where needed.
4. Automatically generate publication-grade figures/tables and insert them into the paper with accurate captions and discussion.
5. Automatically update docs/progress.md after each meaningful change.
6. Continue iterating until there are no remaining high-severity internal blockers that can be addressed from the current repository and available data/code.

Repository-specific working rules:
- Treat paper/main.tex as the source of truth for the main manuscript.
- Treat paper/appendix.tex as the place for overflow results, implementation detail, extra ablations, robustness checks, and reproducibility content.
- Treat paper/references.bib as the only bibliography file; clean duplicates/incomplete entries if needed.
- Use paper/build.sh to compile after every major manuscript change.
- Prefer modifying/adding code under src/ rather than hardcoding numbers or figures into LaTeX.
- If a figure/table is reported in the manuscript, it must be reproducibly generated from code whenever practical.
- If a result changes, update both the manuscript and docs/progress.md in the same iteration.
- Never leave TODO-style prose, placeholder claims, venue-meta phrases, or project-management comments inside the final manuscript text.

Execution policy:
Work in iterative cycles. In each cycle do ALL of the following:
A. Inspect current manuscript, appendix, bibliography, progress log, and relevant code in src/.
B. Identify the highest-impact blockers for a serious medical imaging submission.
C. Make concrete edits to manuscript/code/assets that reduce those blockers.
D. Run the necessary build and experiment commands.
E. Regenerate figures/tables if needed.
F. Patch the manuscript to reflect only the actual latest outputs.
G. Update docs/progress.md with:
   - completed
   - in progress
   - next
   - exact changed files
   - whether each former blocker is resolved, partially resolved, or unresolved
H. Rebuild the PDF.
I. Repeat.

What to optimize for:
1. Scientific honesty
2. Stronger novelty framing
3. Better alignment between claimed innovation and actual executable implementation
4. Better baselines
5. Better ablations
6. Better dataset/protocol transparency
7. Better figure readability and caption quality
8. Better limitation analysis
9. Better reproducibility
10. Better venue readiness

Detailed tasks you must perform:

[Phase 1: Global audit]
- Read paper/main.tex, paper/appendix.tex, docs/progress.md, and key experiment scripts under src/.
- Build a blocker list ranked by severity:
  - claim/evidence mismatch
  - novelty not actually demonstrated
  - missing core baseline
  - weak experimental protocol
  - weak statistics
  - weak figures
  - weak literature positioning
  - missing appendix/reproducibility detail
  - unsupported medical claims
  - poor writing / formatting / structure
- Write the blocker list into a temporary working note if useful, but the final visible tracker must be docs/progress.md.

[Phase 2: Manuscript strengthening]
Revise the manuscript for submission-grade scientific writing:
- tighten title, abstract, introduction, related work, method, experiments, discussion, limitations, conclusion
- make contributions precise, testable, and non-inflated
- ensure every claimed innovation is matched by:
  (a) architectural implementation in src/
  (b) experiment or ablation
  (c) explicit discussion of what is and is not validated
- remove weak hype phrases and replace with evidence-based wording
- ensure the paper answers:
  1. What is the exact problem?
  2. Why is it clinically / technically relevant?
  3. What is actually novel here?
  4. How is it different from fusion / single-modality KD / prior medical KD?
  5. What evidence proves the proposed innovation matters?
  6. What evidence currently fails, and how is that honestly discussed?

[Phase 3: Experimental rigor upgrade]
Audit the current experiments and upgrade them as far as possible from the existing repository:
- verify dataset manifests, splits, label balance, patient-level separation, and leakage risk
- verify all reported metrics are meaningful under current class distributions
- if any metric is uninterpretable under the present split, explicitly mark it in manuscript and avoid headline emphasis
- add stronger baselines if executable from available code/data
- add sanity checks and negative-result analysis when the method does not outperform baselines
- add repeated runs, confidence intervals or std reporting where possible
- add confusion matrix / per-class results / calibration / ROC / PR / error-case visualization when supported
- add robustness checks or sensitivity analysis if feasible
- move overflow detail to appendix when main text becomes crowded

[Phase 4: Innovation verification]
For each claimed module or innovation (for example DPE, MHRA, DFPN, distillation design, cross-modality transfer):
- verify whether it is actually implemented
- verify whether there is a clean ablation isolating its effect
- verify whether current data support a positive claim
- if not supported:
  - weaken the manuscript claim
  - add a targeted experiment if feasible
  - otherwise explicitly state it remains preliminary
Do not allow “innovation” to remain merely architectural description without empirical validation.

[Phase 5: Figures and tables]
Automatically improve paper figures and tables:
- regenerate publication-grade figures from code under src/
- improve font sizes, labels, legends, caption specificity, axis naming, and consistency
- remove redundant or low-information visuals
- add new figures when they directly strengthen evidence
- ensure every figure is cited and interpreted in the manuscript
- ensure every table has a clear takeaway sentence in the text
- if useful, move detailed plots to appendix and keep only the most decision-relevant visuals in the main paper

[Phase 6: Appendix and reproducibility]
Strengthen appendix.tex with:
- implementation details
- hyperparameters
- data curation details
- additional ablations
- additional tables/figures
- failure cases
- limitations and reproducibility details
- exact experiment settings if not suitable for main text

[Phase 7: Bibliography]
Audit paper/references.bib:
- fix broken BibTeX entries
- normalize capitalization, author fields, venue fields, year, pages, arXiv formatting
- remove obviously irrelevant or duplicated references
- ensure key claims in intro/related work/method discussion are cited
- do not invent references

[Phase 8: Progress tracking]
After each substantial iteration, update docs/progress.md so it always reflects reality.
The update must:
- be consistent with actual files and latest PDF
- distinguish completed vs partial vs unresolved
- mention which experiments were actually run
- mention which figures/tables were regenerated
- mention which claims were weakened due to insufficient evidence
- mention next highest-priority blocker

Hard acceptance criteria for each iteration:
- paper/build.sh completes successfully, or if it fails, fix the failure before proceeding
- manuscript text matches generated figures/tables/results
- no claim is stronger than the evidence
- docs/progress.md is updated
- changes improve submission readiness rather than just style

Venue-readiness standard:
Aim for a serious medical imaging submission standard. However, do NOT pretend the paper is ready if the evidence does not support it. If a blocker cannot be solved from the current repository/data, clearly document it and pivot the manuscript toward the strongest honest version possible.

Specific priorities for this repository:
- prioritize resolving the mismatch between proposed cross-modality novelty and weak supporting evidence
- prioritize improving experimental defensibility
- prioritize making the paper look like a rigorous reproducible pilot study if full top-tier evidence cannot yet be reached
- prioritize stronger dataset/protocol clarity, cleaner figures, and sharper discussion of limitations
- prioritize identifying the minimum additional experiments that would most directly validate the core innovation

Output behavior:
Do not stop after one pass.
Keep iterating autonomously within this repository.
After each iteration, print:
1. files changed
2. experiments run
3. figures/tables regenerated
4. main scientific improvements
5. remaining blockers
6. exact next action
Then continue.

Start now by:
1. auditing the manuscript and codebase,
2. identifying the top 10 submission blockers,
3. fixing the highest-priority ones immediately,
4. rebuilding the paper,
5. updating docs/progress.md,
6. continuing to the next iteration.


Act as both:
- a ruthless top-tier medical imaging reviewer
- and a careful reproducible-research engineer

For every major section of the paper, ask:
- Would a MICCAI / TMI / MedIA reviewer accept this claim?
- What exact evidence is missing?
- Can that evidence be added from the current repo?
- If not, how should the paper be reframed honestly?

Use the following review lenses:
1. novelty
2. technical soundness
3. experimental validity
4. reproducibility
5. clarity
6. clinical relevance
7. risk of overclaiming

If the method does not currently beat baselines, do not force a fake positive story.
Instead, reposition the manuscript into the strongest defensible contribution, such as:
- a reproducible pilot benchmark,
- a negative-result-informed study,
- a careful cross-modality feasibility analysis,
- or a framework paper with transparent limitations.

Always prefer a defensible paper over an overclaimed paper.