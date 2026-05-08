# JDCNet Upgrade Plan: Evidence-Bounded → Validated Architecture

Author working notes — 2026-05-09

This document captures (1) the structural reasons the current paper cannot
validate DPE/MHRA/DFPN, (2) the staged upgrade plan we agreed on, and
(3) the concrete experiment matrix to run on R3090. It is the durable
reference for the next 1–2 weeks of work.

## 1. Diagnosis: why DPE/MHRA/DFPN do not improve over plain logit KD

These five issues are derived from reading `src/jdcnet_exp/{models,distillation,
train,data}.py`, `paper/main.tex`, and the BIMCV 512-patient H800 vs R3090
comparison in `docs/progress.md`.

### 1.1 Binary logit KD carries no dark knowledge
With `num_classes=2`, the teacher softmax has one degree of freedom (P(class=1)).
KD's value comes from off-target probability mass; here that is absent. So the
*only* signal flowing student-ward through the dominant `distillation_loss`
path is a single scalar per sample. DPE / MHRA refine the teacher *internally*,
but their output never reaches the student through this 1-scalar conduit.

This is why Plain logit KD ≈ AT > Full JDCNet under same-case resampling:
modules without an information conduit cannot help.

### 1.2 CT teacher has no real modality advantage
`prepare_bimcv_dataset.py` selects a single central axial slice and stores it
as 8-bit grayscale at 128×128. CT's volumetric advantage — multi-slice context,
density gradients, anatomical depth — is discarded. Effectively CT becomes
"another grayscale photo".

Empirical confirmation: CT teacher BA ≈ 0.69 on 512 patients, only ~0.10 above
X-ray supervised. KD literature requires teacher ≫ student; here the gap is
inside the seed noise band, so KD often injects noise rather than signal.

### 1.3 Cross-modal feature alignment is geometrically unjustified
`attention_transfer_loss` and `feature_hint_loss` impose L2 alignment between
teacher (CT axial slice) and student (X-ray coronal projection) deepest features.
The two views see different anatomy in different coordinate frames. Forcing
their feature maps to match implements an **incorrect geometric prior**, which
is why AT achieves the same mean as plain KD (no-op) rather than improving it.

### 1.4 Backbone capacity-vs-data mismatch
- TeacherCNN: ~470k params, StudentCNN: ~94k params, custom 3–4 stage CNN.
- 1251 paired images / 512 patients at 128×128.
- Custom CNN at this scale cannot match what an ImageNet-pretrained ResNet18
  produces with the same supervision. Supervised X-ray ceiling around BA 0.55–
  0.61 is consistent with under-capacity learner, not data scarcity alone.

### 1.5 No teacher-confidence gating
When the CT teacher's max softmax probability is ~0.55, KD still pulls the
student. This explains the H800 vs R3090 result divergence with identical
manifest and seeds: H800 cross-modal KD collapsed to recall=0, R3090 stayed at
BA 0.60 — same data, same algorithm, knife-edge stability.

## 2. Upgrade plan (three tiers, agreed direction = diagnostic ablation first)

### Tier-A — Minimum viable upgrade (2–3 GPU days)
A1. Switch teacher and student backbones to **ResNet-18** (already implemented
    via `ResNet18Classifier`; only the config flag changes).
A2. Multi-slice CT teacher: `top-k` slices by lung-region area, mean-pool of
    per-slice features. Edit in `prepare_bimcv_dataset.py`.
A3. Confidence-gated KD: per-sample weight = `2 * (max(p_T) − 0.5)` clamped
    to [0, 1], multiplied into the soft-loss term in `distillation_loss`.
A4. Symmetric KL or Jensen–Shannon divergence as the soft objective, in
    place of forward KL only.

Expected effect: cross-modal KD vs supervised gap moves from +0.010 (current,
not significant) to +0.06–0.08 BA at n=10 resamples; H1 / H2 reach p<0.05.

### Tier-B — Architectural rebuild (5–7 GPU days, target = validated architecture)
B1. **DRR (Digitally Reconstructed Radiograph) anchor**. From the CT volume,
    use `torchio` parallel projection along the AP direction to synthesize
    a pseudo X-ray. Pre-generate 512 DRRs offline as PNG; treat the pair
    (CT, DRR) as a geometric anchor and align student X-ray features with
    teacher CT features *through* the DRR feature.
B2. **Multi-target distillation** beyond logits:
    - Lung-region attention map from a frozen pretrained lung segmentation
      net (e.g., TorchXRayVision's lung mask), distilled as soft spatial
      target.
    - Per-class prototype embeddings (teacher class centroids) for the
      student to match.
    These two extra targets give DPE / MHRA / DFPN a real downstream conduit;
    the module stack now has somewhere to push its representational gain.
B3. **InfoNCE with memory bank** (MoCo-style queue, K=512 patients) replacing
    the in-batch CRD that currently has only 15 negatives.

Expected effect: H4 (DPE/MHRA/DFPN improve over plain control) becomes
**Supported** at p<0.01; this is the validated-architecture milestone.

### Tier-C — LUPI reframe + cross-modal SSL pretraining (10+ days)
Generalized-distillation theoretical framing (Lopez-Paz 2016) plus
SimSiam/BYOL cross-modal pretraining on the 1251 paired CT–X-ray pairs
without labels, then linear probe + KD fine-tune. Target conference→journal
upgrade. Out of current scope unless A and B both validate cleanly.

## 3. Step-1 diagnostic ablation (this week, R3090)

**Question**: how much of the supervised baseline weakness is due to backbone
capacity rather than data scarcity?

If ResNet-18 supervised X-ray on the same 512-patient manifest reaches BA
≥0.70, then capacity matters and Tier-B is justified. If ResNet-18 also
plateaus near 0.60, the bottleneck is genuinely data and the paper's
evidence-bounded framing is honest; Tier-A is sufficient and Tier-B is
deferred until a larger paired cohort is available.

### Experiment matrix (Phase 1, ~6 GPU-hours)

| # | Backbone   | Method              | Seeds          | GPU |
|---|-----------|---------------------|----------------|-----|
| 1 | ResNet-18 | X-ray supervised    | 42, 43         | 0   |
| 2 | Custom CNN| X-ray supervised    | 42, 43 (rerun) | 1   |
| 3 | ResNet-18 | CT teacher          | 42, 43         | 2   |
| 4 | ResNet-18 | Cross-modal logit KD | 42, 43        | 3   |

- Manifest: existing `/data/JDCNET/src/data/bimcv/bimcv_merged_paired_manifest.csv`
  (512 patients, no change).
- Optimization: AdamW 3e-4, weight decay 1e-4, batch 16, 50 epochs, the same
  augmentation pipeline as `data.py`.
- Best-checkpoint criterion: balanced accuracy (already wired in `train.py`).
- Runtime estimate per run: ~90 min on a single RTX 3090 at 128×128.
- Total wall time: ~6 hours with four-card parallelism.

### Decision rules after Phase 1

- If (1) ResNet-18 supervised − Custom-CNN supervised ≥ 0.05 BA: backbone
  capacity is a real lever → proceed to Tier-A then Tier-B at full speed.
- If (2) ResNet-18 cross-modal KD − ResNet-18 supervised ≥ 0.05 BA: cross-modal
  signal is recoverable with a stronger learner → Tier-A is enough to upgrade
  the paper's H1 to "Supported".
- If both gaps remain <0.03 BA at n=2 seeds, flag the experiment for n=5 seeds
  before committing to Tier-B.

## 4. Tier-B implementation sketch (only if Phase 1 motivates it)

```
Pre-step (offline, one-time):
  src/jdcnet_exp/build_drr.py         # torchio parallel projection
  data/bimcv/drr_512/<patient_id>.png # 512 PNG images, ~10 MB total

Code changes:
  src/jdcnet_exp/models.py
    + class DRRAnchorHead(nn.Module): projection + adapter
    + ResNet18Classifier becomes the default teacher/student
  src/jdcnet_exp/distillation.py
    + drr_anchor_loss(student_feat, teacher_feat, drr_feat)
    + lung_mask_distill_loss(student_attn, teacher_lung_mask)
    + prototype_distill_loss(student_emb, teacher_class_centroids)
    + symmetric_kl(p, q, T)
    + confidence_gated_kd(student_logits, teacher_logits, ...)
  src/jdcnet_exp/data.py
    + read DRR path column from manifest
    + WeightedRandomSampler enabled for cross-modal KD configs
  src/jdcnet_exp/train.py
    + memory-bank queue (MoCo-style) for InfoNCE
    + DRR feature path for student-side adapter
  src/jdcnet_exp/config.py
    + DistillationConfig.drr_weight, lung_mask_weight, prototype_weight,
      memory_bank_size, confidence_floor, kd_divergence ("kl"|"sym"|"js")
```

## 5. Statistical bar

Final paper-grade evidence requires:
- 5 seeds × 5 same-case resamples = **25 paired observations** per row.
- Two-sided Wilcoxon signed-rank, target p<0.01 (was 0.625 in current paper).
- Headline metric: balanced accuracy. Secondary: specificity, MCC, PR-AUC.
- Ablation rule: every module added (DPE / MHRA / DFPN / DRR / lung-mask /
  prototype / memory-bank) reports its leave-one-out BA delta and an FDR-
  adjusted p-value.

## 6. Status tracking

- [ ] Phase 1 diagnostic ablation queued on R3090
- [ ] Phase 1 results recorded in `docs/tmp/upgrade_phase1_results.md`
- [ ] Tier-A code changes (config flag + confidence gating + multi-slice CT)
- [ ] Tier-A 5-seed × 5-resample evaluation
- [ ] Tier-B code changes (DRR + multi-target + memory bank) — gated on A success
- [ ] Tier-B 5-seed × 5-resample evaluation — gated on B implementation
- [ ] Paper revision: H4 row in `tab:hypothesis_status` flipped to Supported
