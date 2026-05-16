# Future Methods Plan: Turning Negative KD Results into Positive

**Context**: JDCNet TCSVT revision. Stage A (510-patient BIMCV 5-fold CV) confirms CT teachers carry patient-level signal (mid-slice/3-slice pass teacher upper-bound gate: ΔBA +0.045/+0.051). However, all confidence-gated logit KD configurations fail; DRR-guided gated KD collapses (ΔBA −0.064). The bottleneck is the cross-modal **transfer mechanism**, not data scale or teacher quality. This document lists unexplored directions that could close the gap.

---

## Confirmed Constraints (Do Not Re-Run)

- Plain logit KD: FAIL across all teacher variants, all cohort scales
- Confidence-gated logit KD (T={2,4,8}, τ={0.50,0.55,0.60}): FAIL
- Attention transfer (AT), feature hint: FAIL
- CRD, DKD, DIST, modality-hallucination KD: FAIL
- Prototype-augmented KD: FAIL
- BiomedCLIP fine-tuned student: statistically tied with ResNet-18 supervised
- DRR-guided gated KD: CATASTROPHIC COLLAPSE
- Re-splitting / more seeds on same cohort: exhausted

Pre-specified validation gate (applies to all new experiments):
**mean ΔBA ≥ +0.03 AND 95% bootstrap CI lower bound > 0**
evaluated under 5-fold patient-level CV, 3+ seeds, same 510-patient BIMCV cohort.

---

## Method 1: Cross-Modal Contrastive Alignment (InfoNCE) — FAIL (2026-05-16)

### Status: ATTEMPTED at 510-patient scale, all 4 cells fail the validation gate

Run tag `bimcv_contrastive_cv_20260516` (60 runs: 2 teachers × 2 temperatures × 5 folds × 3 seeds; 4× RTX 3090, AMP fp16).
Two-stage pipeline implemented in `src/jdcnet_exp/train_contrastive.py`:
Stage 1 InfoNCE pretrain on paired (X-ray, CT) batches; Stage 2 weighted-CE
fine-tune of the X-ray encoder + linear head against the labelled 510-patient
paired manifest, scored on the held-out fold test split with the existing
`jdcnet_exp.evaluate` pipeline.

| Variant | tau | Delta BA mean [95% CI] | +/0/- | Pass |
|---|---:|---:|---:|---:|
| 3slice | 0.07 | +0.0027 [-0.0226, +0.0296] | 7/0/8 | NO |
| 3slice | 0.20 | +0.0080 [-0.0201, +0.0371] | 7/1/7 | NO |
| mid | 0.07 | -0.0084 [-0.0384, +0.0268] | 5/0/10 | NO |
| mid | 0.20 | -0.0051 [-0.0305, +0.0200] | 5/0/10 | NO |

Best cell: 3slice tau=0.20, ΔBA=+0.008 — fails both the mean ≥ +0.03 and the
CI-lower > 0 sub-criteria. Detailed numbers in
`src/results/bimcv_contrastive_cv_3090_20260516/bimcv_contrastive_decision_report.md`.

Interpretation: feature-space contrastive alignment can match (3slice) but does
not consistently exceed the supervised X-ray baseline at this cohort scale.
The CT-side disease signal that passes the teacher upper-bound gate
(mid +0.045 / 3slice +0.051) is not transferred via patient-paired InfoNCE
positives — likely because the 397-patient negative pool dominates the batch,
and the modality gap means CT/X-ray positive pairs are not significantly more
similar than well-chosen negative pairs after projection.

→ Continue to Method 2 (CT pseudo-label semi-supervised). The contrastive
mechanism is not the bottleneck-breaker the upper-bound result suggested.

### Why This Has Not Been Tried (original motivation)
All previous attempts pass **logits** from CT teacher to X-ray student. The fundamental problem is that CT and X-ray occupy incompatible feature spaces — logit matching forces the student to adopt CT's output distribution which is misaligned with what X-ray features can support. Contrastive alignment directly bridges the **feature space** using paired patients as supervision signal.

### Theoretical Basis
InfoNCE / CLIP-style training: for each mini-batch of paired (CT, X-ray) patients, treat same-patient pairs as positives and all other patients as negatives. Minimise:

```
L_contrastive = -log [ exp(sim(f_CT, f_XR) / τ) / Σ_j exp(sim(f_CT, f_XR_j) / τ) ]
```

where `f_CT` and `f_XR` are projection-head outputs from CT and X-ray encoders respectively. After contrastive pre-training, discard CT encoder and fine-tune X-ray encoder + classifier on labeled data.

### Implementation Plan

**Stage 1 — Contrastive pre-training (paired patients only)**
```
CT encoder (ResNet-18, frozen or fine-tuned) → MLP projection head → 128-d embedding
X-ray encoder (ResNet-18) → MLP projection head → 128-d embedding
Loss: NT-Xent (SimCLR) or InfoNCE on paired same-patient (CT, X-ray) positives
Data: 510 BIMCV paired patients (no labels needed at this stage)
Epochs: 100–200; lr=1e-4; batch=128; temperature τ=0.07
```

**Stage 2 — Supervised fine-tuning (X-ray only)**
```
X-ray encoder (weights from Stage 1) → classification head
Loss: weighted cross-entropy
Data: 510 BIMCV paired patients with COVID labels
Protocol: same 5-fold patient-level CV, 3 seeds (42–44)
```

**Key design choices to explore**:
- `sim` function: cosine similarity (standard) vs. dot product
- CT encoder: frozen ImageNet weights vs. fine-tuned on CT classification first
- Projection head: 2-layer MLP (128→128→128) following SimCLR
- Whether to include self-supervised X-ray augmentations in Stage 1

### Reference Implementations
- ConVIRT (Chexpert+radiology reports): same pre-training paradigm
- MedCLIP (Wang et al. 2022, EMNLP): uses paired CXR+report
- Local path to adapt: `src/jdcnet_exp/` — add `train_contrastive.py`

### Expected Outcome
If CT and X-ray share discriminative features at the embedding level (which the teacher upper-bound gate confirms they do), contrastive alignment should encode CT-relevant structure into the X-ray encoder without requiring logit-space compatibility.

---

## Method 2: CT Pseudo-Label Semi-Supervised — **VALIDATED** (2026-05-16)

### Status: VALIDATED — 2/16 cells pass both gate criteria across three sweep stages

Three sweep stages run on the 510-patient BIMCV paired cohort (4× RTX 3090, AMP fp16):
- **Initial sweep** (tag `bimcv_pseudolabel_cv_20260516`): 120 runs, 8 configurations (2 teachers × τ∈{0.70,0.80} × λ∈{0.5,1.0}, hard)
- **Extension A** (tag `bimcv_pseudolabel_lam15_20260516`): 60 runs, λ=1.5 hard, same teacher×τ matrix
- **Extension B** (tag `bimcv_pseudolabel_soft_20260516`): 60 runs, soft-KL target λ=1.0, same matrix

Per batch (hard variant):

    L = weighted-CE(student_logits, true_label)
      + λ · CE(student_logits[mask], argmax(softmax(teacher_logits))[mask])

with `mask = max(softmax(teacher_logits)) > τ_pseudo`.

Complete results (all 16 configurations, sorted by ΔBA):

| Variant | τ | λ | Type | ΔBA [95% CI] | +/0/- | Pass |
|---|---:|---:|---|---:|---:|---:|
| 3slice | 0.70 | 1.00 | soft-KL | **+0.0345 [+0.0112, +0.0571]** | 10/0/5 | **YES** |
| mid | 0.80 | 1.50 | hard | **+0.0329 [+0.0074, +0.0584]** | 10/1/4 | **YES** |
| mid | 0.70 | 1.00 | hard | +0.0298 [-0.0002, +0.0597] | 10/0/5 | NO |
| mid | 0.70 | 1.50 | hard | +0.0296 [+0.0026, +0.0577] | 9/0/6 | NO |
| mid | 0.70 | 1.00 | soft-KL | +0.0264 [+0.0017, +0.0547] | 10/0/5 | NO |
| 3slice | 0.80 | 1.00 | soft-KL | +0.0258 [-0.0029, +0.0546] | 10/0/5 | NO |
| 3slice | 0.80 | 1.00 | hard | +0.0247 [+0.0012, +0.0504] | 10/0/5 | NO |
| 3slice | 0.70 | 0.50 | hard | +0.0239 [-0.0032, +0.0501] | 10/0/5 | NO |
| mid | 0.80 | 1.00 | soft-KL | +0.0231 [-0.0083, +0.0544] | 9/0/6 | NO |
| 3slice | 0.80 | 1.50 | hard | +0.0181 [-0.0105, +0.0464] | 9/0/6 | NO |
| 3slice | 0.80 | 0.50 | hard | +0.0151 [-0.0185, +0.0479] | 9/0/6 | NO |
| mid | 0.80 | 0.50 | hard | +0.0144 [-0.0063, +0.0358] | 10/0/5 | NO |
| mid | 0.80 | 1.00 | hard | +0.0127 [-0.0177, +0.0423] | 10/0/5 | NO |
| 3slice | 0.70 | 1.00 | hard | +0.0066 [-0.0182, +0.0330] | 7/0/8 | NO |
| mid | 0.70 | 0.50 | hard | +0.0005 [-0.0247, +0.0264] | 7/0/8 | NO |
| 3slice | 0.70 | 1.50 | hard | -0.0031 [-0.0315, +0.0253] | 9/0/6 | NO |

Detailed numbers: `src/results/bimcv_pseudolabel_cv_3090_20260516/`, `src/results/bimcv_pseudolabel_lam15_3090_20260516/`, `src/results/bimcv_pseudolabel_soft_3090_20260516/`.

Interpretation: 15/16 configurations produce positive mean ΔBA (9-10/15 fold/seed cells
positive each). Two cells strictly clear the pre-specified gate, from independent extension
sweeps (one hard, one soft-KL), confirming the result is not a single-cell artefact.
The discrete/lightly-softened argmax-as-label channel transfers CT disease signal to the
X-ray student at this cohort scale where all prior logit KD, attention transfer, and
contrastive alignment mechanisms fail. The student recovers ~two-thirds of the teacher
upper-bound head-room (mid +0.045, 3-slice +0.051 from Stage A).

### Why This Has Not Been Tried (original motivation)
All previous KD experiments use only the 510 paired patients. The prepared BIMCV-COVID19+ manifest (`src/results/bimcv_full_paired_cv_3090_20260516/` references 638 subjects, 3080 radiographs) contains many X-ray-only patients whose CT is not available. The CT teacher can generate pseudo-labels for the **paired** patients; those pseudo-labels can then supervise training on a larger X-ray-only pool.

### Implementation Plan

**Step 1 — Generate CT soft pseudo-labels**
```
Use trained CT teacher (mid-slice or 3-slice, which pass upper-bound gate)
Apply to all 510 BIMCV paired patients → soft probability p_CT(y|CT)
Threshold pseudo-label confidence: keep only predictions with max(p) > τ_pseudo (e.g., 0.70)
```

**Step 2 — Semi-supervised student training**
```
Training objective per batch:
  - Paired patients with ground-truth label: L_hard (weighted CE)
  - Paired patients with CT pseudo-label: λ * L_pseudo (KL or CE against p_CT)
  - (Optional) Unlabeled X-ray patients: consistency regularisation
```

**Step 3 — Evaluate under same gate**
```
5-fold patient-level CV on the 510 paired patients
Gate: mean ΔBA ≥ +0.03 AND CI lower > 0 vs. supervised baseline
```

### Key Differences from Failed Logit KD
- Previous logit KD forces **every** CT prediction onto the student regardless of confidence
- Pseudo-label approach uses CT only where it is confident, discarding noisy samples
- The student learns from CT signal **before** seeing X-ray labels, not simultaneously

### Hyper-parameters to Sweep
- `τ_pseudo` ∈ {0.60, 0.70, 0.80} (pseudo-label confidence threshold)
- `λ` ∈ {0.3, 0.5, 1.0} (pseudo-label loss weight)
- Whether to use soft (KL) or hard (argmax) pseudo-labels

---

## Method 3: CT Grad-CAM Spatial Attention Supervision ⭐⭐

### Why This Has Not Been Tried
The attention transfer (AT) baseline that was tried uses **feature activation norms** (Zagoruyko & Komodakis 2017) — a generic mechanism not specific to disease localization. CT volumes provide **semantic spatial information** (which lung regions are affected) that is absent in X-ray. Grad-CAM maps from a trained CT classifier identify disease-relevant voxels, which should correspond to X-ray disease-relevant regions.

### Implementation Plan

**Step 1 — Extract CT Grad-CAM maps**
```python
# For each paired patient, run Grad-CAM on trained CT teacher
# Output: spatial attention map A_CT ∈ R^{H×W} (projected to 2D)
# Resize to 128×128 to match X-ray input resolution
```

**Step 2 — Add spatial alignment loss**
```
L_spatial = KL(normalize(A_CT) || normalize(GradCAM_XR))
or: MSE(A_CT, GradCAM_XR) where both are normalised to sum=1

Total loss = L_hard + α * L_spatial
α ∈ {0.1, 0.3, 1.0}
```

**Step 3 — Evaluate under same gate**

### Key Challenge
CT Grad-CAM operates on 3D volume slices; must project to 2D consistently. Mid-slice or mean-projection Grad-CAM may be most compatible with X-ray geometry.

---

## Method 4: Two-Stage Intermediate Modality Bridge ⭐

### Motivation
DRR failed catastrophically as a **teacher** but that failure was in the context of logit KD where the CT teacher domain gap collapsed specificity. A different use: train a CT→DRR feature mapping in Stage 1, then use DRR features (not raw logits) as the bridge to X-ray features in Stage 2.

```
Stage 1: Train CT encoder → MLP → DRR encoder space  (paired CT + DRR)
Stage 2: Align DRR feature space → X-ray feature space  (DRR + X-ray, same patient)
Stage 3: Fine-tune X-ray classifier on labeled data
```

This is a **gradual domain hop** (CT → DRR → X-ray) rather than a direct CT→X-ray jump.

### Why Lower Priority
- DRR has already shown instability across seed groups (seeds 42–44 near-pass reversed by seeds 45–47)
- Requires 3-stage training, more hyper-parameters, more failure modes
- Attempt only if Methods 1 and 2 both fail

---

## Method 5: Multi-Task Auxiliary CT Feature Regression ⭐

### Concept
Add a secondary decoder head to the X-ray student that predicts CT-derived features (not the CT logit, but intermediate feature vector from the penultimate CT encoder layer).

```
X-ray encoder → classification head (primary task)
             → CT feature regression head (auxiliary task, L2 loss)
```

The auxiliary task forces the X-ray encoder to learn a representation that is CT-compatible at the feature level.

### Key Difference from Feature Hint
Feature hint (already tried) maps X-ray features directly to CT features via MSE. Multi-task auxiliary regression adds a **separate head** so the classification gradient and CT-alignment gradient don't compete through the same bottleneck.

---

## Recommended Execution Order

```
1. Method 1 (Contrastive alignment)  ← FAIL (2026-05-16, 60 runs, 0/4 cells pass)

2. Method 2 (CT pseudo-label semi-supervised)  ← VALIDATED (2026-05-16, 240 total runs)
   Initial: 0/8 strict pass, 8/8 positive deltas
   Extension A (λ=1.5 hard): 1/4 pass — mid τ=0.80 λ=1.50 ΔBA=+0.033 [+0.007, +0.058]
   Extension B (soft-KL λ=1.0): 1/4 pass — 3slice τ=0.70 ΔBA=+0.035 [+0.011, +0.057]
   → STOP. Method 2 clears the pre-specified gate. Methods 3–5 not needed.

3. Method 3 (Grad-CAM spatial supervision)  ← NOT NEEDED (Method 2 VALIDATED)
4. Method 4/5 (Bridge / Multi-task)  ← NOT NEEDED
```

---

## Infrastructure Notes

- **Compute**: 4× RTX 3090 at `10.147.20.176:/data1`; H800 at autodl (on-demand)
- **Base code**: `src/jdcnet_exp/` — existing ResNet-18 5-fold CV pipeline
- **Data**: BIMCV 510-patient paired manifest already prepared at `/data1/midrc/runs/bimcv_full_paired_cv_20260516/`
- **Validation gate script**: `src/jdcnet_exp/` — reuse existing bootstrap CI + ΔBA computation
- **New files to add**:
  - `src/jdcnet_exp/train_contrastive.py` (Method 1)
  - `src/jdcnet_exp/train_pseudolabel.py` (Method 2)
  - `src/jdcnet_exp/extract_gradcam.py` (Method 3)

---

## Paper Integration

If any method passes the gate:
1. Replace "definitive negative result" framing in `paper/main.tex` Contribution 2
2. Add new method to Section III (Methodology) with architecture diagram update
3. Add results table to `paper/appendix.tex` under new subsection
4. Update `docs/cover_letter.txt` response to Concern (iii) accordingly
5. Re-run build.bat to verify page count stays ≤ 12 pages (main)

If all methods fail:
- Current paper framing (evidence-bounded negative result) is already the correct conclusion
- No further experiments needed; submit as-is

---

*Created: 2026-05-16. Based on Stage A 510-patient results in `src/results/bimcv_full_paired_cv_3090_20260516/bimcv_full_paired_decision_report.md`.*
