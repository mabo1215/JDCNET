# JDCNet Upgrade Plan: Evidence-Bounded → Validated Architecture

Author working notes — created 2026-05-09, **updated 2026-05-10 after Tier-B-lite sweep failed**

This document captures (1) the structural reasons the current paper cannot
validate DPE/MHRA/DFPN, (2) the staged upgrade plan, (3) the Phase-1 +
Tier-B-lite sweep results, and (4) the **revised next-step plan** after
prototype-only Tier-B-lite failed to reach `p<0.05` against supervised at
any of three weight values.

## 0. TL;DR (post-2026-05-10)

The bandwidth hypothesis (binary logit KD has only 1-scalar dark knowledge,
so DPE/MHRA can't reach the student) is **partially confirmed but not
sufficient to explain the negative result**. We added a multi-dimensional
prototype channel (class centroids in the embedding space, swept over three
weights), and *still* no weight reaches `p<0.05` against supervised.

This means the bottleneck is not just bandwidth. The two remaining levers
that have **not yet been pulled** are:

1. **Geometric/anatomical alignment** between CT and X-ray. Both logits and
   prototypes operate in feature space; neither resolves the fact that CT
   axial slices and X-ray coronal projections see different anatomy in
   different coordinate frames.
2. **Cohort scale**. n=40 paired observations gives ~80% power to detect
   `Δ ≥ 0.07` BA at `α=0.05` two-sided. The observed Δ (~0.025-0.045) is
   below that floor, so even if the directional advantage is real, it is
   undetectable at this scale.

The revised plan is **DRR (Digitally Reconstructed Radiograph) anchor**
combined with **multi-slice CT teacher** at Tier-B Full level, aimed
specifically at lever (1). Lever (2) is deferred because no larger paired
COVID CT/X-ray cohort is currently available to us.

## 1. Diagnosis: why DPE/MHRA/DFPN do not improve over plain logit KD

These five issues are derived from reading `src/jdcnet_exp/{models,distillation,
train,data}.py`, `paper/main.tex`, and the BIMCV 512-patient H800 vs R3090
comparison in `docs/progress.md`. Numbered 1.1–1.5 below; all five remain
valid after Tier-B-lite results.

### 1.1 Binary logit KD carries no dark knowledge
With `num_classes=2`, the teacher softmax has one degree of freedom (P(class=1)).
KD's value comes from off-target probability mass; here that is absent. So the
*only* signal flowing student-ward through the dominant `distillation_loss`
path is a single scalar per sample. DPE / MHRA refine the teacher *internally*,
but their output never reaches the student through this 1-scalar conduit.

**Update 2026-05-10**: prototype distillation widens this conduit from 1 scalar
to `num_classes × embedding_dim` (≈ 1024) signals, but the resampled Δ vs sup
stayed at +0.028 (one-sided p=0.180). So bandwidth is necessary but not
sufficient — there is a second blocking factor.

### 1.2 CT teacher has no real modality advantage
`prepare_bimcv_dataset.py` selects a single central axial slice and stores it
as 8-bit grayscale at 128×128. CT's volumetric advantage — multi-slice context,
density gradients, anatomical depth — is discarded. Effectively CT becomes
"another grayscale photo".

Empirical confirmation: CT teacher BA ≈ 0.69 on 512 patients (custom-CNN);
0.715 on ResNet-18; resampled mean BA 0.815. The teacher has a real but
modest advantage over the student supervised (0.691). KD literature requires
the teacher to be substantially stronger than the student; here the gap is
inside the seed noise band, so KD often injects noise rather than signal.

### 1.3 Cross-modal feature alignment is geometrically unjustified
`attention_transfer_loss` and `feature_hint_loss` impose L2 alignment between
teacher (CT axial slice) and student (X-ray coronal projection) deepest features.
The two views see different anatomy in different coordinate frames. Forcing
their feature maps to match implements an **incorrect geometric prior**, which
is why AT achieves the same mean as plain KD (no-op) rather than improving it.

**Update 2026-05-10**: prototype-KD partly bypasses this by aligning **class
centroids** in the embedding space rather than spatial feature maps. This is
geometrically agnostic. Yet PROTO-KD didn't break significance either, which
means even centroid-level alignment can't fix the fact that the student needs
to learn **what to look at on the X-ray**, not just **which class label CT
endorses**. → DRR is the natural fix.

### 1.4 Backbone capacity-vs-data mismatch
- TeacherCNN: ~470k params, StudentCNN: ~94k params, custom 3–4 stage CNN.
- 1251 paired images / 512 patients at 128×128.
- Custom CNN at this scale cannot match what an ImageNet-pretrained ResNet18
  produces with the same supervision. Supervised X-ray ceiling around BA 0.55–
  0.61 is consistent with under-capacity learner, not data scarcity alone.

**Update 2026-05-10**: ResNet-18 raised supervised from 0.598 → 0.693 (+0.10),
which is large and reproducible (`std≈0.008` at n=4 seeds). Backbone capacity
was indeed a real lever. But **on the same backbone, neither plain KD nor
prototype KD beats supervised**, so capacity was the floor, not the gap.

### 1.5 No teacher-confidence gating
When the CT teacher's max softmax probability is ~0.55, KD still pulls the
student. This explains the H800 vs R3090 result divergence with identical
manifest and seeds: H800 cross-modal KD collapsed to recall=0, R3090 stayed at
BA 0.60 — same data, same algorithm, knife-edge stability.

**Update 2026-05-10**: instability disappeared on ResNet-18 (no recall=0
collapse in any of the 16 ResNet-18 KD/PROTO-KD runs). Capacity buys you
robustness; confidence-gating would be a marginal additional safeguard but is
no longer the dominant failure mode.

## 2. Original three-tier upgrade plan (2026-05-09)

### Tier-A — Minimum viable upgrade (2–3 GPU days) — partially executed

Original plan:
- A1. ResNet-18 backbone for both teacher and student
- A2. Multi-slice CT teacher (top-k by lung area, mean-pool features)
- A3. Confidence-gated KD per-sample weight
- A4. Symmetric KL or JSD soft objective

**Status 2026-05-10**: A1 done (Phase 1 + Tier-B-lite). A2/A3/A4 deferred
because A1 alone showed they were no longer dominant levers. They can still
be folded into Tier-B Full as cheap additional wins.

### Tier-B — Architectural rebuild (5–7 GPU days, target = validated architecture)

Original plan:
- B1. **DRR (Digitally Reconstructed Radiograph) anchor**
- B2. **Multi-target distillation**: lung-mask attention + class prototypes
- B3. **InfoNCE with memory bank** (MoCo-style queue, K=512)

**Status 2026-05-10**: B2 prototype-only sub-component executed (Wave 1/2/3
on R3090). Lung-mask deferred earlier (PSPNet weights wouldn't transfer to
R3090). B1 (DRR) and B3 (memory bank) **never executed**. B2 alone failed.

### Tier-C — LUPI reframe + cross-modal SSL pretraining (10+ days)
Out of scope; only relevant if A and B both validate.

## 3. Phase-1 + Tier-B-lite sweep — completed (2026-05-09 to 2026-05-10)

### Experiment timeline on R3090
| Wave | Date (UTC) | Method | Seeds | Outcome |
|---|---|---|---|---|
| Phase 1 | 2026-05-09 06–11h | sup / teacher / KD (ResNet-18) | 42–45 | KD vs sup: Δ=+0.025, p=0.668 |
| Wave 1 | 2026-05-09 14–18h | Proto-KD w=0.5 | 42–45 | Δ=−0.017 vs sup, p=0.743 |
| Wave 2 | 2026-05-09 18–22h | Proto-KD w=1.0 | 42–45 | Δ=+0.028 vs sup, one-sided p=0.180 |
| Wave 3 | 2026-05-09 22h – 2026-05-10 00:42h | Proto-KD w=2.0† | 42–45 | Δ=+0.008 vs sup, p=0.963 |

†Wave 3 truncated at epoch 20/50 due to DataLoader worker deadlock.
Best.pt saved; epoch-20 checkpoints used for resample eval.

### Resampling Wilcoxon stats (n=40 paired observations each)
- KD vs sup:           mean Δ=+0.025, two-sided p=0.668
- Proto-KD w=0.5 vs sup: mean Δ=−0.017, two-sided p=0.743
- Proto-KD w=1.0 vs sup: mean Δ=+0.028, two-sided p=0.360, one-sided p=0.180
- Proto-KD w=2.0 vs sup: mean Δ=+0.008, two-sided p=0.963
- **Proto-KD w=1.0 vs Proto-KD w=0.5**: mean Δ=+0.045, **one-sided p=0.059**

The weight-monotonicity signal is the strongest result we have — it's
consistent with "richer transfer signal helps" but is below `p<0.05` by a
hair. Critically, it does **not** translate into significance against
supervised, so it doesn't unlock H1.

### Why prototype-only Tier-B-lite failed
Prototype distillation aligns **class centroids** in the joint embedding
space. This is information-rich (≈1024 scalars per pair vs 1 scalar for
plain KD), but it is still a **classification-level** signal: it encodes
"which class label CT endorses for this patient", not "what anatomical
region on the X-ray is consistent with that label".

For cross-modal transfer to work in the COVID-vs-Negative setting, the
student needs to learn:
1. Where to look on the X-ray (lungs, opacity patterns)
2. Which features there correspond to disease (texture, density)

Prototypes give signal (1) at the embedding level only, and sidestep (2)
entirely. The student is left to discover (2) on its own from the
hard cross-entropy label, which is exactly what the supervised baseline
does — hence the tied performance.

## 4. Revised plan (2026-05-10): Tier-B Full with DRR + multi-slice + lung-mask

### 4.1 Why DRR is the right next lever

A Digitally Reconstructed Radiograph (DRR) is a synthesised X-ray-like
image computed from a CT volume by parallel projection along the AP axis.
It has three properties that are exactly what plain logit KD and
prototype-KD lack:

- **Geometric correspondence with the real X-ray**: same view, same
  orientation, same anatomical layout (lungs in the same place).
- **Pixel-space supervision**: the student can be asked to produce the
  same X-ray-like output that the teacher's CT volume would produce when
  projected — a much denser signal than any class-level alignment.
- **Differentiable through standard 2D CNNs**: no special 3D backbone or
  point-cloud machinery needed.

The mechanism becomes:
```
CT volume → DRR projection → DRR feature (teacher path)
real X-ray   →                 X-ray feature (student path)
                              ↓
                 anchor loss: align in same coordinate frame
                              +
                 standard logit KD on top
```

This is precisely the missing geometric prior that Section 1.3
diagnoses as the failure mode of feature_hint_loss and
attention_transfer_loss.

### 4.2 Concrete Tier-B Full experiment matrix

**Pre-step (offline, ~1 GPU-hour)**: build DRR cache.
```
src/jdcnet_exp/build_drr.py
  - Inputs: CT NIfTI volumes from BIMCV
  - Library: torchio (parallel projection, AP direction)
  - Output: data/bimcv/drr_512/<patient_id>.png (~10 MB total)
  - Manifest extension: add `drr_path` column to bimcv_merged_paired_manifest.csv
```

**Code changes** (build on top of existing tier_b_proto branch):
```
src/jdcnet_exp/distillation.py:
  + drr_anchor_loss(student_feature, drr_feature)
    Cosine similarity between L2-normalized features at the same spatial
    resolution. Optional: lung-region weighted L2 (use lung mask to focus
    loss on diagnostically relevant areas).

src/jdcnet_exp/data.py:
  + Read drr_path column; PairedTriplet dataset returns (xray, ct, drr, label)
    or (xray, drr, label) depending on paired_input mode.

src/jdcnet_exp/train.py:
  + Forward DRR through teacher backbone (ResNet-18) or a lightweight DRR
    encoder; extract spatial feature.
  + Add drr_anchor_loss with weight `drr_anchor_weight` to the training loss.
  + Optionally: train DRR teacher head jointly (not just frozen anchor).

src/jdcnet_exp/config.py:
  + DistillationConfig.drr_anchor_weight: float = 0.0
  + DistillationConfig.drr_anchor_resolution: int = 14  (final feature size)
  + ModelConfig: add `paired_drr_input: bool = False`
```

**Training matrix on R3090** (~6–8 GPU-hours wall time, all 4 GPUs):

| # | Method | Seeds | GPU |
|---|---|---|---|
| 1 | DRR-anchor only (no logit KD) | 42–45 | 0 |
| 2 | DRR-anchor + logit KD | 42–45 | 1 |
| 3 | DRR-anchor + Proto-KD w=1.0 (best Tier-B-lite weight) | 42–45 | 2 |
| 4 | DRR-anchor + logit KD + multi-slice teacher | 42–45 | 3 |

All use ResNet-18, BIMCV 512-patient manifest, same optimization budget.
Run #4 is the "kitchen-sink" Tier-B Full configuration — if any combination
flips H1, it's the most likely candidate.

### 4.3 Decision rule

After resample eval (10 same-case Monte Carlo resamples, n=40 paired
observations per row):

- **If any of #1–#4 achieves Wilcoxon two-sided `p<0.05` vs supervised**:
  → H1 in `tab:hypothesis_status` flips from "directional" to "supported"
  → Run leave-one-out ablation (DRR off / Proto off / multi-slice off) to
    isolate which component drives the gain. If DRR is necessary, this is
    the validated-architecture story for the paper revision.

- **If all of #1–#4 stay at `p ≥ 0.10`**:
  → Cohort scale is the dominant constraint, not architecture. Document
    DRR as a clean negative result. Pivot the paper revision to
    "evidence-bounded protocol with comprehensive next-evidence-layer
    sweep" rather than "validated architecture". Identify a specific
    target cohort size (≥ 100 paired patients in val) needed for the
    follow-up study.

- **If exactly one combination achieves `p ∈ [0.05, 0.10)`** (marginal
  significance):
  → Re-run with 8 seeds × 10 resamples (n=80 paired) to disambiguate
    between "small real effect" and "type-1-error-on-the-edge". This costs
    another ~12 GPU-hours but is the only way to settle the borderline
    case responsibly.

### 4.4 Optional follow-up: lung-mask attention + memory bank

If DRR alone breaks `p<0.05`, do **not** add lung-mask attention or
memory-bank InfoNCE — they would inflate complexity without changing the
headline. Reserve them for a Tier-C extension paper.

If DRR alone is borderline, add lung-mask attention on top of run #4 as a
deciding test. The TorchXRayVision PSPNet weights deployment was blocked
last time by SSH timeouts; need to retry the local-then-rsync push to
R3090 under a different network condition (e.g., during off-peak hours).

## 5. Statistical bar (unchanged from 2026-05-09)

Final paper-grade evidence requires:
- 4 seeds × 10 same-case resamples = **40 paired observations** per row.
  (Original target was 5×5=25; we exceeded that with 4×10=40.)
- Two-sided Wilcoxon signed-rank, target `p<0.05`.
- Headline metric: balanced accuracy. Secondary: specificity, MCC, PR-AUC.
- Ablation rule: every module added (DPE / MHRA / DFPN / DRR / lung-mask /
  prototype / memory-bank) reports its leave-one-out BA delta and an FDR-
  adjusted p-value.

## 6. Status tracking (updated 2026-05-10)

- [x] Phase 1 diagnostic ablation queued on R3090 (done 2026-05-09 11:45 UTC)
- [x] Phase 1 results recorded in `docs/progress.md` (2026-05-09)
- [x] Tier-B-lite prototype distillation code (2026-05-09): `prototype_distill_loss`
      in `distillation.py`, config + train wiring complete
- [x] Tier-B-lite three-weight sweep (2026-05-09 to 2026-05-10): all 12
      runs (3 weights × 4 seeds) executed; resample eval ran 2026-05-10 00:52 UTC
- [x] Paper backfill (2026-05-10): Execution D in `paper/appendix.tex`,
      H1/Limitations/Conclusion in `paper/main.tex`
- [ ] **DRR pre-step**: implement `build_drr.py`, generate 512 DRRs offline
- [ ] **Tier-B Full code**: `drr_anchor_loss` + data pipeline + train.py wiring
- [ ] **Tier-B Full sweep**: 4 configs × 4 seeds on R3090 (~8 GPU-hours)
- [ ] **Decision and paper revision**: per Section 4.3 decision rule

## 7. What goes wrong if Tier-B Full also fails

A clean negative DRR result is still scientifically informative: it locates
the bottleneck at cohort scale rather than at architecture, mechanism, or
backbone capacity. In that scenario, the paper's contribution becomes:

> "We provide a falsification-oriented evaluation protocol and a
> comprehensive negative-evidence stack — bandwidth (logit KD), capacity
> (custom CNN vs ResNet-18), embedding alignment (prototype KD), and
> geometric alignment (DRR anchor) — all of which fail to recover a
> statistically reliable cross-modal advantage at the 512-patient cohort
> scale. The minimum decisive next experiment is a paired CT/X-ray cohort
> of at least 100 validation patients per resample, with the same baseline
> grid we provide as a Code Ocean capsule."

This is honest and publishable as a "negative results paper" or as the
main contribution of an evidence-bounded TCSVT submission. It's *not* a
"validated architecture" claim, but it would still be the strongest
falsification-oriented protocol in the same-modality vs. cross-modality
KD literature for tiny paired thoracic cohorts.

## 8. Open questions / unknowns

1. **Are CT NIfTI volumes available on R3090?** The current manifest stores
   `teacher_image_path` pointing to extracted 128×128 PNG slices. Need to
   verify the original NIfTI files are still accessible (they may have been
   deleted to save disk space). If not, DRR generation must come from a
   different source.

2. **Does torchio support batch parallel projection?** If yes, the DRR
   pre-step is ~1 GPU-hour. If no, may need to do it on CPU at ~30 minutes
   per patient × 512 = ~10 wall hours (parallelizable across multiple cores).

3. **Lung-mask PSPNet weights**: the previous attempt to deploy
   `torchxrayvision` PSPNet weights to R3090 failed due to repeated SCP
   timeouts. Retrying during off-peak hours is the obvious workaround;
   alternative is to pre-compute lung masks locally and rsync only the
   PNG masks (much smaller transfer).

4. **Multi-slice teacher implementation**: top-k slices by lung area
   requires lung segmentation on the CT volumes too, so it shares
   infrastructure with the lung-mask deployment. Cleaner sequencing:
   first deploy the lung segmenter, then both multi-slice teacher and
   lung-mask attention come for free.
