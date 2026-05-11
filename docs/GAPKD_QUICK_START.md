# GAP-KD MIDRC Validation Quick Start Guide

**目标**: 在 MIDRC paired cohort 上验证 confidence-gated KD 的有效性  
**时间线**: 14-20 days (data audit + GPU training + paper update)  
**状态**: 🚀 Ready to Launch (code framework complete)  

---

## 🎯 Current Status at a Glance

| Component | Status | Location |
|-----------|--------|----------|
| GAP-KD Code | ✅ Complete | `src/jdcnet_exp/` (distillation.py, config.py, train.py) |
| Smoke Tests | ✅ Passing | `src/results/gapkd_cpu_smoke_local/` + H800 CPU |
| MIDRC Manifest | ✅ Ready | `src/data/midrc_manifests/MIDRC_strict_chest_paired_559cases_*.json` |
| Data on H800 | ⏳ Unknown | `/root/autodl-tmp/midrc/` (needs audit) |
| Data Prep Script | ❌ TODO | Need `prepare_midrc_dataset.py` |
| GPU Training | ⏳ Blocked | Waiting for data audit + prep |

---

## ⚡ Quick Start (Next 2 Hours)

### Step 1: Verify Uncommitted Changes (5 min)

```bash
cd c:\source\JDCNET

# See what's changed
git status

# You should see:
# - Modified: src/jdcnet_exp/{config.py, distillation.py, train.py}
# - Untracked: src/jdcnet_exp/smoke_gapkd.py
# - Modified: docs/{progress.md, experiment_plan.md, jdcnet_upgrade_plan.md}
```

### Step 2: Review 3 Key Documentation Files (10 min)

1. **What changed?**
   ```bash
   cat docs/GAPKD_UNCOMMITTED_CHANGES.md
   ```
   - Summary of all code modifications
   - Smoke test results
   - Next actions

2. **Architecture Overview?**
   ```bash
   cat docs/GAPKD_ARCHITECTURE_DIAGRAM.md
   ```
   - Visual before/after
   - New modules (A-E)
   - Training loop integration

3. **How to audit data?**
   ```bash
   cat docs/MIDRC_AUDIT_CHECKLIST.md
   ```
   - 7-phase checklist (1A-1G)
   - SSH commands for H800
   - Decision gates

### Step 3: Decide on Data Audit Scope (10 min)

**Question A**: Should we validate all 559 MIDRC cases?
- **Yes** → Full audit required (Phase 1A-1G)
- **No** → Use smaller subset (MIDRC_*_50cases or _100cases)

**Question B**: Can we tolerate download/decompression time?
- **Yes** → Full prep (Phase 1C, data unzip on H800)
- **Partial** → Stream processing later (skip 1C now)

**Question C**: After data audit, approve GPU training budget?
- **Yes** → 300-450 GPU days for 6 methods
- **No** → Need cost estimate / alternative plan

---

## 📊 Immediate Next Steps (Do This Now)

### Option A: Start Data Audit Immediately

If you want to unblock GPU training ASAP:

```bash
# 1. SSH to H800
ssh -p 12437 root@connect.westc.seetacloud.com

# 2. Run Phase 1A checks
du -sh /root/autodl-tmp/midrc/
find /root/autodl-tmp/midrc -type f | wc -l

# 3. Report findings back to this doc
# Expected: ~1100 files, ~120-140 GB
```

Then reference **MIDRC_AUDIT_CHECKLIST.md** for remaining phases.

### Option B: Start Code Integration Testing

While data audit happens in parallel:

```bash
# 1. Create a test config with gating enabled
cat > src/configs/gapkd_test.json << 'EOF'
{
  "model": {...},
  "distillation": {
    "confidence_gate_enabled": true,
    "confidence_gate_threshold": 0.5,
    "confidence_gate_floor": 0.05,
    "confidence_gate_power": 1.0,
    "confidence_gate_requires_correct": true,
    "projected_attention_weight": 0.5,
    ...
  }
}
EOF

# 2. Run local CPU test
python -m jdcnet_exp.smoke_gapkd --output-json gapkd_test_result.json

# Expected: 5/5 checks passed (should already pass)
```

---

## 📅 Detailed Timeline

### Week 1: Data Readiness
```
Day 1 (2026-05-11):
  ├─ Phase 1A: Check file count/size on H800 (30 min)
  ├─ Phase 1B: Verify ZIP vs DICOM format (10 min)
  └─ Decision: Is download complete?

Day 2 (2026-05-12):
  ├─ Phase 1C: Decompress ZIPs if needed (10 min runtime)
  ├─ Phase 1D: MD5 spot-check 10 files (10 min)
  ├─ Phase 1E-F: Verify pairing & labels (10 min)
  ├─ Phase 1G: Download manifest locally (5 min)
  └─ Decision: Data ready for preparation?

Day 2-3: Parallel: Create prepare_midrc_dataset.py
  ├─ Handle DICOM extraction (pydicom)
  ├─ CT slice extraction (nibabel)
  ├─ Xray normalization
  ├─ Manifest alignment
  └─ Output: prepared_559_paired/ structure
```

### Week 2: Training
```
Day 4 (2026-05-13):
  ├─ Create train/val/test splits (350/84/125)
  ├─ Pre-register success metrics
  └─ Generate 6 config files (baseline, teacher, plain KD, gated, gated+attn, oracle)

Day 5-16 (2026-05-13 to -24):
  ├─ GPU training on H800
  ├─ Method 1 (baseline):    100 epochs @ GPU 1
  ├─ Method 2 (teacher):     100 epochs @ GPU 2
  ├─ Method 3 (plain KD):    100 epochs @ GPU 3-4
  ├─ Method 4 (gated KD):    100 epochs @ GPU 5-6
  ├─ Method 5 (gated+attn):  100 epochs @ GPU 7-8
  ├─ Method 6 (oracle):      post-processing @ CPU
  └─ Parallel execution → ~12-18 wall clock days

Day 17 (2026-05-25):
  ├─ Collect results
  ├─ Run statistical analysis (paired Wilcoxon)
  └─ Compute 95% CI
```

### Week 3: Validation & Paper Update
```
Day 18 (2026-05-26):
  ├─ Decision:
  │  ├─ If Δ BA ≥ +0.03 → SUCCESS
  │  │  └─ Update paper: "validated architecture"
  │  └─ If Δ BA < +0.03 → NO IMPROVEMENT
  │     └─ Paper stays "evidence-bounded"
  └─ Either way: paper revision complete

Day 19-20 (2026-05-27-28):
  ├─ Final build & proofs
  ├─ Submit updated paper
  └─ Done!
```

---

## 🔑 Key Decisions Required from You

### Decision 1: MIDRC Manifest Version

Which MIDRC manifest to use?

| Option | Cases | Size | Time |
|--------|-------|------|------|
| A (recommended) | 559 | 137 GB | Full validation |
| B (quick test) | 100 | 26 GB | Fast test |
| C (very quick) | 50 | 13 GB | Proof of concept |

**Recommendation**: Option A (559 cases) to properly validate cross-modal KD

### Decision 2: Download Completeness

Do you have SSH key and network access to resume downloads if needed?

- [ ] Yes, can SSH & continue downloads
- [ ] Unsure, will verify

### Decision 3: GPU Budget Approval

Estimated GPU days for 6 methods, 100 epochs each:

```
Method 1 (baseline):     50 GPU days
Method 2 (teacher):      50 GPU days
Method 3 (plain KD):    100 GPU days (try multiple runs)
Method 4 (gated KD):    100 GPU days
Method 5 (gated+attn):  100 GPU days
Method 6 (oracle):       10 CPU days

Total: 300-450 GPU days
Time: 12-18 days (assuming 4 H100 GPUs in parallel)
Cost: depends on H800 hourly rate
```

Do you approve this budget?

- [ ] Yes, proceed with full 559-case MIDRC
- [ ] Partial: only Methods 1-4 (200 GPU days)
- [ ] Defer: wait for cost estimate

---

## 🚨 Critical Path Items

These items **must be completed** before GPU training can start:

| Item | Owner | Timeline | Blocker? |
|------|-------|----------|----------|
| Data audit (Phase 1) | You | Today-tomorrow | ✅ YES |
| Create prepare_midrc_dataset.py | Me | Tomorrow-day after | ✅ YES |
| Generate train/val/test splits | Me | After prep script | ✅ YES |
| Pre-register success metrics | You | After splits | ⚠️ RECOMMENDED |
| Create 6 config files | Me | After metrics | ✅ YES |
| Launch GPU training | You | After configs | (no blocker) |

---

## 📝 Documentation You Now Have

1. **GAPKD_UNCOMMITTED_CHANGES.md**
   - Detailed change list (13 files, 610 lines)
   - What each new function does
   - Smoke test results

2. **GAPKD_ARCHITECTURE_DIAGRAM.md**
   - Visual before/after comparison
   - 5 modules (A-E) explained
   - Experimental matrix structure

3. **MIDRC_AUDIT_CHECKLIST.md** ← **START HERE**
   - 7-phase audit plan
   - SSH commands ready to copy-paste
   - Decision gates & fallbacks

4. **This file: Quick Start Guide**
   - Timeline summary
   - Immediate actions
   - Decision templates

---

## 🎬 Action Now (Next 30 Minutes)

### If You're Ready to Move Fast:

```bash
# 1. Copy audit checklist
cat docs/MIDRC_AUDIT_CHECKLIST.md

# 2. SSH to H800 and run Phase 1A
ssh -p 12437 root@connect.westc.seetacloud.com

# On H800:
du -sh /root/autodl-tmp/midrc/
find /root/autodl-tmp/midrc -type f | wc -l

# 3. Report results back
# Expected: ~1100 files, ~120-140 GB
```

### If You Want to Understand First:

```bash
# 1. Read MIDRC_AUDIT_CHECKLIST.md (~10 min)
# 2. Read GAPKD_ARCHITECTURE_DIAGRAM.md (~10 min)
# 3. Then decide: proceed with Phase 1? (Y/N)
```

---

## ✅ Success Criteria

**This roadmap is successful when:**

1. ✅ Phase 1 audit complete → data confirmed ready
2. ✅ `prepare_midrc_dataset.py` working → 559 cases extracted & aligned
3. ✅ Train/val/test splits generated → reproducible protocol
4. ✅ GPU training launched → all 6 methods running
5. ✅ Results collected → statistical analysis done
6. ✅ Decision made → paper updated accordingly
7. ✅ Paper submitted → validation cycle closed

**Timeline goal**: All 7 items done by 2026-05-28 (17 days)

---

## 🆘 If Blocked

If any phase fails, check:

| Block | Fallback |
|-------|----------|
| Data download incomplete | Resume with gen3-client or identify network issues |
| Decompression fails | Use streaming processing (don't decompress all) |
| Disk space issues | Clean logs or use external drive |
| GPU unavailable | Run Methods 1-3 on CPU first, then Methods 4-6 |
| Time too tight | Run smaller cohort (100 or 50 cases) for proof of concept |

---

## 📞 Questions?

- **"What if data is corrupt?"** → Phase 1D MD5 check will catch it
- **"What if I don't have all 559 cases?"** → Start with available subset, document limitation
- **"What if GAP-KD doesn't improve BA?"** → Paper stays evidence-bounded (not a failure)
- **"When to commit code?"** → After all tests pass on MIDRC, before paper submission

---

## TL;DR (Ultra-Quick Version)

1. **Check H800 data** (30 min): `docs/MIDRC_AUDIT_CHECKLIST.md` Phase 1A-B
2. **Approve** 559 cases + 300-450 GPU days budget (Y/N)
3. **Start Phase 1 audit** (today-tomorrow)
4. **I create prep script** (day after)
5. **GPU training** (week 2)
6. **Paper update** (week 3)
7. **Done** (2026-05-28)

---

**Created**: 2026-05-11  
**Status**: 🚀 Ready to Launch  
**Next**: User to approve + start Phase 1 audit
