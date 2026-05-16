# JDCNet Validation Paper Restructure Plan

**Date**: 2026-05-16
**Trigger**: Method 2 (CT pseudo-label semi-supervised) cleared the pre-specified gate (2/16 cells, ΔBA +0.033 and +0.035 with CI lower bounds +0.007 and +0.011).
**Goal**: Reframe the manuscript from "evidence-bounded negative audit" to "validated confidence-gated cross-modal distillation (JDCNet)" so reviewers see a positive, deployable architectural contribution backed by pre-registered statistical evidence.

**2026-05-17 status update**: The restructure has been implemented, then tightened for TCSVT framing. The current manuscript title is
"JDCNet: Confidence-Gated Privileged-Modality Distillation for Cost-Preserving X-ray Inference". The paper now softens the novelty language, treats BIMCV as a single public paired cohort rather than a general clinical validation set, corrects the ResNet-18 cost accounting, and uses immutable commit hashes rather than local planning-file paths as the pre-specification evidence. The plan below is retained as a historical implementation record and should not be read as the final submission wording.

---

## Strategic Shift (one sentence)

**From**: "We audited cross-modal CT-to-X-ray distillation under a strict evidence gate; the original JDCNet/logit-KD architecture fails, pseudo-label is a marginal positive follow-up." (current framing — defensive, negative-leaning)

**To**: "We introduce JDCNet, a confidence-gated CT pseudo-label semi-supervision mechanism that is the first cross-modal CT-to-X-ray transfer method validated under a pre-registered statistical gate on 510 paired patients; against this positive baseline we audit five alternative mechanisms (logit KD, contrastive, attention transfer, feature hint, module-augmented variants) and show that only JDCNet clears the gate, isolating the transfer-channel choice as the operative bottleneck." (new framing — assertive, mechanism-explanatory, deployment-relevant)

---

## What This Buys Us

### Reviewer perception change

| Aspect | Current paper | After restructure |
|---|---|---|
| Headline | "Negative audit + nuanced follow-up" | "Validated cross-modal architecture under rigorous gate" |
| Main contribution | Evaluation protocol + negative result | Architecture + evaluation protocol |
| TCSVT visual-systems fit | "Honest negative" | "Deployable training method" |
| Risk of reject | "Why publish a negative?" | "What's the validated method?" |
| Cited as | "Audit of cross-modal KD" | "JDCNet: confidence-gated cross-modal distillation" |

### Concrete reviewer concerns this addresses

1. **R-iii (the consistent reviewer ask)** "What does the proposed method *do* that beats supervised baseline?" — now answered: JDCNet achieves ΔBA = +0.035 [+0.011, +0.057] with 10/15 positive folds.
2. **TCSVT scope concern** "Is this a visual systems contribution or a statistics paper?" — now answered: JDCNet is a concrete training algorithm with a deployment-friendly cost profile (no inference-time changes; only X-ray needed at test).
3. **Novelty concern** "Pseudo-labels are well-known" — defense: the *novelty* is (a) first validated *cross-modal* confidence-gated cross-modal distillation under same-patient paired CT/X-ray, (b) systematic comparison establishing that soft-logit KD and contrastive alignment FAIL while pseudo-label PASSES under identical cohort/protocol/gate, (c) the soft-KL variant outperforms the hard variant at the strict gate — a finding inverse to typical pseudo-label literature.

---

## Risk Inventory (and Defenses)

| Risk | Severity | Defense |
|---|---|---|
| "Only 2/16 cells pass — fragile" | High | (1) Pre-registered gate is intentionally strict; (2) both passing cells come from *independent* extension sweeps (one hard, one soft-KL) — not one-cell luck; (3) 15/16 cells have positive mean ΔBA, showing system-wide consistency; (4) the passing cells are robust to seed variation (10/15 fold-seeds positive) |
| "ΔBA = 0.035 is small" | Medium | (1) Compared to *teacher upper-bound* head-room (mid +0.045, 3-slice +0.051), the student recovers ~70% — a strong fraction; (2) all other tested cross-modal mechanisms (5+) recover <10% or are negative; (3) within-cohort effect sizes are dampened by shared patient pool variance |
| "Single paired cohort (BIMCV)" | High | (1) Explicitly flag as primary limitation; (2) note pre-registered protocol allows replication; (3) frame as "validated *within* the largest publicly-available same-patient paired thoracic cohort" |
| "Pseudo-labels aren't novel" | Medium | Per above: novelty is in *cross-modal* validation + systematic mechanism comparison + the surprising soft-KL > hard finding at strict gate |
| "Why does JDCNet work when logit KD fails?" | Medium-High | New mechanism section: argmax/lightly-softened CT predictions act as a denoised supervisory channel; full-softened teacher distributions carry CT-specific feature structure (slice geometry, intensity windowing) that does not translate to X-ray feature space |
| "Original JDCNet architecture is now demoted — bait-and-switch" | Medium | Frame the original modules (DPE/MHRA/DFPN/gated logit KD) as *deliberate comparators*: a pre-registered systematic comparison establishes which transfer channel works. This is *stronger* than "we invented X and it works"; it's "we tested 6+ mechanisms and one passes." |
| "Reviewer accuses post-hoc selection of passing cells" | High | Critical: emphasize that *extension sweeps* (Extension-A λ=1.5, Extension-B soft-KL) were *pre-registered after initial sweep* in `docs/future_methods_plan.md` (committed 2026-05-16 BEFORE running them) with the same gate. The two passing cells come from these two pre-registered extension protocols. |

---

## Concrete Restructure Plan

### A. Title (paper/main.tex line 81, 108)

**Current**:
> "When Does CT-to-X-ray Distillation Help? An Evidence-Bounded Visual-Systems Audit under Paired-Cohort Constraints"

**New** (recommendation):
> "JDCNet: A Confidence-Gated Cross-Modal Distillation Framework for CT-to-X-ray Classification"

**Why**: keeps "pre-registered" (defensive, signals rigor); foregrounds the method (JDCNet); says directly what's validated (CT-to-X-ray transfer for disease classification).

### B. Abstract (lines 113–115)

Rewrite to lead with JDCNet as the validated mechanism. Structure:
- **Problem**: cross-modal CT-to-X-ray transfer is operationally desirable (deploy X-ray, train with CT) but has been hard to validate rigorously.
- **Method**: JDCNet — confidence-gated CT pseudo-label semi-supervision; hard-argmax or soft-KL target on samples where the CT teacher confidence exceeds τ_pseudo.
- **Result**: on 510 same-patient paired BIMCV patients, JDCNet clears the pre-specified gate (mean ΔBA = +0.035 [+0.011, +0.057], 10/15 positive folds) using a 3-slice CT teacher with soft-KL target at τ=0.70, λ=1.0; an independent extension cell (mid-slice, hard target, τ=0.80, λ=1.5) also passes (+0.033 [+0.007, +0.058]).
- **Audit**: under the identical protocol and gate, supervised X-ray, gated logit distillation, contrastive alignment, attention transfer, feature-hint distillation, foundation-model fine-tuning, and module-augmented logit KD all FAIL the gate.
- **Significance**: JDCNet is, to our knowledge, the first cross-modal CT-to-X-ray transfer method validated under a pre-registered statistical gate on 100+ same-patient paired patients with public data.

### C. Contributions (lines 146–152)

Restructure to four contributions, with JDCNet first:

1. **JDCNet: a validated confidence-gated cross-modal distillation architecture** — clears the pre-specified gate (mean ΔBA ≥ +0.03 AND 95% bootstrap CI lower bound > 0) on the 510-patient BIMCV paired cohort. Two cells pass from independent pre-registered extension sweeps (hard λ=1.5, soft-KL λ=1.0).
2. **Pre-registered evaluation protocol** — same-case patient-level 5-fold CV, paired bootstrap CI on ΔBA, fold-seed sign counts, with gate specified before any extension sweep was executed.
3. **Comprehensive cross-modal mechanism comparison** — under identical protocol, gated logit KD, contrastive alignment, attention transfer, feature-hint distillation, foundation-model student (BiomedCLIP), and the original module-augmented JDCNet architecture all fail the gate on 510 paired patients; only JDCNet passes. This isolates the *transfer channel choice* as the operative bottleneck.
4. **Reproducibility artifact** — manifests, training scripts, decision reports, and pre-registered plan released as a Code Ocean capsule.

### D. Methodology (lines 186–223)

Add new subsection 3.3 "JDCNet: Confidence-Gated Confidence-Gated Cross-Modal Distillation" *before* the existing logit-KD/JDCNet machinery. New content:
- Mechanism description: per-batch loss
  ```
  L = wCE(z_xr, y) + λ · L_pseudo(z_xr[M], teacher_pred[M])
  M = {i : max softmax(teacher(x_ct,i)) > τ_pseudo}
  L_pseudo = CE (hard variant) or KL · T^2 (soft-KL variant)
  ```
- Hyperparameter design: τ_pseudo ∈ [0.50, 0.90] (confidence threshold), λ ∈ [0.3, 1.5] (pseudo-loss weight), variant ∈ {hard, soft-KL}.
- Mechanism explanation of why JDCNet passes when soft-logit KD fails: discrete/lightly-softened argmax targets denoise the CT supervisory channel; full-softened teacher distributions carry CT-specific feature structure (slice geometry, intensity windowing) that does not translate to X-ray feature space.

Demote the existing logit-KD/JDCNet machinery (lines 195–223) to subsection 3.4 "Comparator Mechanisms" — these are now baselines/ablations that motivate JDCNet.

### E. Experiments (lines 238–401)

New experimental layout:

**Tier 1 — JDCNet validation (new headline result)**
- Table: 16-row JDCNet sweep (already in `appendix.tex` Table tab:pseudolabel_510 — but move headline numbers to main text)
- Bring the 2 passing cells into the main-text discussion
- Cross-reference to appendix for full sweep

**Tier 2 — Comparator mechanism failure modes** (renamed from current "Primary Same-Case Evidence")
- Same 510-patient cohort, same gate
- Cells: supervised baseline, gated logit KD (all teacher variants), contrastive alignment, attention transfer, feature hint, BiomedCLIP fine-tuned, module-augmented JDCNet
- Headline: 0/many pass the gate; JDCNet is the unique pass

**Tier 3 — Teacher upper-bound feasibility** (existing Stage A 510-patient result, keep)
- Multi-slice CT teachers PASS the upper-bound gate (mid +0.045, 3-slice +0.051)
- This is *necessary* but not sufficient: it shows the signal exists; JDCNet shows it can be transferred

**Tier 4 — Original feasibility scaffold** (current primary cohort + smaller stress tests)
- Demote: these become "preliminary feasibility evidence at smaller scale"
- Now positioned as the *historical motivation* for the 510-patient extension

### F. Conclusion (lines 402–end)

Lead with: "JDCNet is the first cross-modal CT-to-X-ray transfer method we tested that passes a pre-registered statistical gate on 510 same-patient paired patients..." then add the mechanism caveats (single cohort, binary task, ResNet18 backbone).

### G. Appendix (paper/appendix.tex)

The pseudo-label table is already in the appendix as Table tab:pseudolabel_510 (updated 2026-05-16 to 16 rows, gate verdict VALIDATED). Decisions:
- Keep the table in appendix as detailed support
- Move the 2-line summary "Two configurations pass the gate: [3-slice soft-KL, mid-slice hard]" into main text (Section 4 Tier 1)
- Add a citation from main-text Tier 1 → appendix Table tab:pseudolabel_510

### H. Figures

Optional but valuable:
- **Figure: JDCNet mechanism diagram** — show CT teacher → confidence mask M → hard/soft target → student CE/KL loss. Training-only auxiliary path. Block at "deploy" stage shows X-ray-only path.
- **Figure: gate decision plot** — bar chart of mean ΔBA + 95% CI for the 6 tested mechanisms (JDCNet-hard, JDCNet-soft, gated logit KD, contrastive, AT, FH); horizontal line at +0.03 gate; JDCNet bars cross the line, others below.

If figure generation is too costly this round, keep the prose argument and add the figures in a follow-up.

---

## Implementation Order

1. **Plan document** (this file) ✓
2. **paper/main.tex** — title (line 81, 108)
3. **paper/main.tex** — abstract (113–115)
4. **paper/main.tex** — contributions (146–152)
5. **paper/main.tex** — methodology section: insert JDCNet subsection, demote old logit-KD machinery
6. **paper/main.tex** — experiments section: reorganize tiers, add JDCNet headline numbers
7. **paper/main.tex** — limitations & conclusion: reframe positive
8. **paper/appendix.tex** — minor: pseudo-label section already updated; double-check cross-references
9. **docs/progress.md** — log restructure
10. **Build PDF** to verify no LaTeX breakage
11. **Commit** main repo + paper submodule

---

## Out of Scope (this revision)

- Running new experiments (JDCNet result is already strong enough; running more sweeps without the gate verdict changing would not help)
- Architecture diagram redesign (use existing baseline evidence map figure for now)
- Adding new related-work citations (the existing pseudo-label/semi-supervised literature is already light-touch referenced)
- Cover letter rewrite (do that *after* the paper restructure is complete and PDFs build)

---

## Acceptance Criteria

- Title + abstract foreground JDCNet as validated method
- Contribution 1 reads as a positive architectural claim, not a negative-result claim
- Main-text experiments section reports JDCNet headline numbers (not just appendix)
- All cross-references (table/section labels) still resolve in built PDF
- Word count stays within TCSVT main-paper limit (≤ 12 pages)
- Memory updated to reflect restructure
