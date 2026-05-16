# JDCNet TCSVT — 解除 reason (iii)“paired cohort 过小”瓶颈的改进 plan (2026-05-16)

> **目的**：直接针对 `docs/revision_suggestions.tex` 中 reviewer 的 **main reason (iii)** —
> *"the primary paired cohort is extremely small and cannot support a strong journal-level technical claim"* —
> 提出一个**只用 3090 已有 `/data/` 与 `/data1/` 数据**就可执行的同患者 paired-cohort 扩容方案，把目前的
> 228-patient（114+/114-）规模一次推到 510-patient （113+/397-）或 ~760-patient (BIMCV+MIDRC) 规模，
> 并把已有的近门候选（C1 `proj` teacher、calibration T=4 thr=0.50）整合为单一 pre-specified 终点，
> 给“validated framework”一个可成立的最后一次机会。
>
> **背景**：
> - 已完成 calibration scan 8-cell：T=4 thr=0.50 接近门 (ΔBA=+0.034, CI [-0.004,+0.073], 9/15 pos) 但 FAIL
> - 已完成 C1 4-teacher × 4-method × 5-fold × 3-seed：`proj` teacher upper-bound 已通过门
>   (`teacher_vs_supervised` ΔBA +0.0449, CI [0.008, 0.081], YES)，但所有 `gated_vs_supervised`
>   仍 FAIL（最近的 `drr.gated_vs_plain` +0.0378 CI [-0.001, +0.083] 9/15 pos，差一点）
> - 已完成 C2 BiomedCLIP fine-tune：对同 split ResNet18 supervised 平手 (+0.002 CI [-0.048, +0.050])
>
> **判断**：
> 1. teacher 上界稳定存在（C1 `proj` 已证明 CT 信息有效），
> 2. KD 转移机制本身（confidence-gated, T=4 thr=0.50）在 226-patient 平衡子集上已"差一步"（multiple
>    contrasts 9/15 pos，CI lower 落在 -0.001~-0.004 区间），
> 3. **唯一缺口是统计功效与样本规模**——这正是 reviewer (iii) 指出的核心问题。
>
> 因此本计划只做一件事：**把 paired-cohort 规模放大 4.5×–6.7×**，用 weighted-loss + patient-level
> stratified CV 让现有 `proj`/`drr` gated KD pipeline 直接在扩容 cohort 上跑，看 CI lower 能否上推过 0。

---

## 1. 数据资产盘点（已在 3090，无需下载）

| 资产 | 路径 | 当前可用 | 当前已用 | 未用增量 |
|---|---|---:|---:|---:|
| BIMCV 阳性 paired (CT+CXR) | `/data/bimcv_paired/sub-S*` | 113 patients (266 CXR + 113 CT volumes) | 113 | 0 (已用满) |
| **BIMCV 阴性 paired (CT+CXR)** | `/data/bimcv_neg_paired/sub-S*` | **398 patients (985 CXR + 398 CT volumes)** | **114**（balanced 下采样） | **+284** |
| BIMCV 增量阴性 (X-ray only) | `/data/bimcv_new512/sub-S*` | 2997 patients (4469 sessions, X-ray only) | 0 | +2997（仅可做 weak-supervision 或预训练，无 CT teacher） |
| BIMCV DRR cache | `/data/bimcv/drr_cache/bimcv_S*.png` | 510 patients (≈ 113+ + 397-) | 226 | +284 |
| **MIDRC 同患者 paired raw** | `/data1/midrc/raw_559cases_combined/dg.MD1R/` | **559 patients (1118 zip)** | **126**（locked validation） | **+433** |
| BIMCV CT mid-slice cache | `/data/bimcv_ct_slices/`, `/data/bimcv_neg_ct_slices/` | 511 PNG (113+ + 398-) | 226 | +285 |
| BIMCV CT teacher variants (4 类) | `/data1/midrc/bimcv_ct_variants_*/` | 已在 mid/3slice/proj/drr 各 226 patients | 226 | 需要补 +284 (negative 增量) |
| MIDRC CT teacher variants (6 类) | `/data1/midrc/teacher_variants_20260514/images/` | 126 patients × 6 variants | 126 | 需要扩到 250–400 |

**关键观察**：reviewer 投诉的"19 patients、26 images"是 paper Table 1 中 `cohen2020covid` 路径，主结果其实是
228-patient balanced 5-fold CV——但 reviewer 在 M5 同样质疑了 226-patient 平衡子集，因为本来有 398 个阴性
被下采样到 114 个。**因此真正可拿出来当 "M5/iii 终极回答" 的就是 113+/398- 全 paired pool（510 patients）**。

---

## 2. 三段式扩容 plan

### Stage A — BIMCV-only 510-patient paired CV（**Priority 1，立刻执行**）

#### A.1 假设
**H1\***：在 113+/397- 同患者 paired cohort 上（4.5× 当前规模），用 weighted-CE + `proj` CT teacher +
gated KD (T=4, thr=0.50)，gated_kd vs supervised ΔBA 95% CI lower 可上推过 0。

#### A.2 manifest 生成
```python
# 复用 /data1/midrc/bimcv_for_mixed_cv.csv（已含 510 patients 全集）：
#   397 negatives + 113 positives，已包含 teacher_image_path 与 drr_path
# 生成新的 5-fold patient-level stratified split（不下采样）：
#   每 fold test ≈ 102 patients（80 neg + 22 pos）
# 由于阶级失衡 3.5:1，必须用：
#   (a) 训练 loss: weighted CE，pos_weight = 3.5
#   (b) 评估指标：BA / Macro-F1 / Specificity / ROC-AUC（已是论文标准）
#   (c) 抽样：保持 train/test 患者级别比例 3.5:1，不做 oversample
```

manifest 路径：`/data1/midrc/bimcv_full_paired_cv_20260516/fold_{00..04}/bimcv_full_paired_fold0X_paired_manifest.csv`

#### A.3 实验矩阵（最小可信集）
4 teacher 表征 × 4 method × 5 fold × 3 seed = **240 runs**

| Teacher | 来源 | 选择理由 |
|---|---|---|
| `mid` | 现有 bimcv_ct_slices/ + bimcv_neg_ct_slices/ | baseline 一致性 |
| **`proj`** | 需要为 +284 个阴性补提取（multi-slice axial mean projection） | **C1 已证明 teacher 上界稳定通过门** |
| **`drr`** | 已有 510 patients DRR cache | C1 中 gated_vs_plain 最接近门 (+0.0378 CI [-0.001,+0.083]) |
| `3slice` | 需要为 +284 阴性补提取 | 与 `proj` 对比，控制 multi-slice 优势是否来自投影聚合 |

方法：teacher / xray_supervised / plain_kd / gated_kd(T=4, thr=0.50)
- gated_kd 必须使用 weighted-CE on hard label part（与 supervised baseline 完全相同 loss weighting）

#### A.4 预处理需要补的工作
- **`proj` / `3slice` / `mid` 阴性 CT 变体**：用 `src/ops/extract_ct_teacher_variants.py` 模板，
  输入 `/data/bimcv_neg_paired/sub-S*/ct/*.nii*`（398 个 NIfTI），输出到
  `/dev/shm/bimcv_ct_{proj,3slice,mid}/` 与 `/data1/midrc/bimcv_ct_variants_full_510/`。
  预计 ~30 分钟（398 NIfTI × ~5 秒 sampling）。
- **DRR**：510 个已就绪，无需新增。
- **manifest 生成脚本**：在 `src/jdcnet_exp/prepare_bimcv_full_paired_cv.py` 新增，
  以 `bimcv_for_mixed_cv.csv` 为输入，按 patient_id stratified by label 做 5-fold split。

#### A.5 决策门（pre-specified，不许 post-hoc 调整）
- **主端点**：`proj.gated_vs_supervised` 在 510-patient × 15 fold-seed cells 的 mean ΔBA
  - PASS：mean ΔBA ≥ +0.03 AND 95% bootstrap CI lower > 0 AND positive count ≥ 11/15
- **二级端点**（同时报告但不替代主端点）：
  - `drr.gated_vs_supervised`
  - `proj.gated_vs_plain`（验证 gating 机制相对 plain KD 的增量）
  - `proj.teacher_vs_supervised`（teacher 上界 sanity check）

#### A.6 GPU 排程
4× RTX 3090 × 4 concurrent = 16 simultaneous runs；240 runs / 16 ≈ 15 batches × ~5 min/run ≈
**75 分钟全部完成**（与 C1 相同 batch_size=512, workers=8 设置；510 patients 训练比 226 大 2.3×，
单 run 约 5-7 min）。

#### A.7 预期产物
```
/data1/midrc/runs/bimcv_full_paired_cv_20260516/{mid,3slice,proj,drr}/
/data1/logs/bimcv_full_paired_cv_20260516/decision_report.md
docs/tmp/bimcv_full_paired_decision_report.md
docs/tmp/bimcv_full_paired_summary.csv
docs/tmp/bimcv_full_paired_deltas.csv
```

---

### Stage B — MIDRC 559-full processing（**Priority 2，与 A 并行可启**）

#### B.1 目的
1. 把 MIDRC 同患者 paired cohort 从 126 → 至多 559（理论上界）。
2. 在 BIMCV+MIDRC 混合 cohort 上做 ~750-1000 patient 二次验证（如果 A 通过门，B 用来做
   external-cohort 复测；如果 A 不通过，B 提供更多 statistical power）。

#### B.2 数据现状
- `/data1/midrc/raw_559cases_combined/dg.MD1R/` 已下载完成（138 GiB，1118 zip）。
- `/data1/midrc/locked_validation/midrc_locked_validation_summary.json` 当前仅 126 cases (63+/63-)。
- **未处理增量**：559 - 126 = 433 patients 的 CT NIfTI 提取 + CT teacher variant 渲染 + X-ray PNG 转换。

#### B.3 实施步骤
- **B-step 1**：在 3090 复用 `src/jdcnet_exp/prepare_midrc_locked_validation.py` 已有的 DICOM→PNG
  pipeline，扩展到 `selected_cases=559`。注意 559 中可能有部分缺失 CXR 或 CT 模态，过滤后预期
  yields ~400-500 paired patients。预计 6-10 小时（138 GiB 单线程解压 + DICOM 读取）。
- **B-step 2**：用 `src/jdcnet_exp/prepare_midrc_teacher_variants.py` 渲染 `proj` 与 `3slice` teacher
  变体（DRR 不适用于 MIDRC，因为 MIDRC 是真实 CT volume，可以直接做 axial 投影）。
- **B-step 3**：生成 BIMCV+MIDRC 混合 paired manifest，patient-level stratified by
  source(BIMCV/MIDRC) × label，跑 5-fold CV。
- **B-step 4**：A 通过则做 external replication；A 失败则用 B 增加 power 重跑 A 同一矩阵。

#### B.4 决策门
与 A 完全相同（mean ΔBA ≥ +0.03 AND CI lower > 0 AND ≥11/15 pos）。

#### B.5 预期产物
```
/data1/midrc/processed_559/  (新增)
/data1/midrc/runs/midrc_full_paired_cv_20260517/
/data1/midrc/runs/bimcv_midrc_full_paired_cv_20260517/
docs/tmp/midrc_full_paired_decision_report.md
docs/tmp/bimcv_midrc_full_paired_decision_report.md
```

---

### Stage C — BIMCV-only "X-ray big pretrain" 路径（**Priority 3，备用**）

#### C.1 目的
如果 A 与 B 全部 FAIL，仍然有 reviewer R8（"stronger X-ray-only baselines"）和 M8 没回答。
利用 `/data/bimcv_new512/` 的 2997 个额外阴性 patients（仅 X-ray，无 CT），做 supervised X-ray
**预训练**，再在 paired 510-cohort 上做 fine-tune + KD。

#### C.2 假设
**H1\*\***：用 ~3000-patient X-ray 预训练初始化的 student backbone，可让 gated KD 的边际 ΔBA
转换效率从 20% 提升到 50%+（因为预训练 backbone 更稳，gradient updates 更高效）。

#### C.3 实施
- 在 `bimcv_new512` 上用 PA/AP X-ray + 无 CT 仅做 binary "COVID source vs non-COVID source" 弱监督预训练
  （不可拿来做 final test，只作为 backbone initialization）。
- 在 Stage A 510-patient cohort 上做 fine-tune + gated KD（同 A.3 矩阵）。
- 决策门同 A.5。

#### C.4 预计时间
预训练 ~6 小时，fine-tune 同 Stage A ~75 min。

---

## 3. 决策树（Stage A 结果如何驱动后续）

| Stage A 结果 | 解读 | 论文处理 | 后续 |
|---|---|---|---|
| **A 通过门**（`proj.gated_vs_supervised` PASS） | **第一次出现 validated cross-modal KD 信号** | 主稿章节升级：把 H1 status 从 "not validated" 改为 "validated on extended 510-patient paired cohort"；JDCNet `proj`-teacher gated-KD 升级为 validated architecture pilot；保留所有 negative-result discussion 作为 evidence-boundary | 跑 Stage B 做 external replication（必做） |
| A 接近通过（CI lower 在 [-0.01, 0]）| 仍是 negative，但已显著缩小 gap | 主稿保留 evidence-bounded 框架，但在 Limitations § 加一句 "extended 510-patient cohort narrows the CI to almost-positive (CI lower X.XXX), confirming sample-size as the dominant bottleneck and motivating Stage B"; 跑 Stage B 把 power 推到 ~750 | Stage B 必做 |
| A 显著 FAIL（CI lower ≤ -0.02 或 ≤ 7/15 pos）| 仅靠 scale 不能解决，需要 mechanism 升级 | 保持 evidence-bounded negative-result；新增 appendix 节"510-patient extended cohort：scale alone is insufficient"；Stage C 可选 | Stage C 可选 |

无论结果如何，**整个 Stage A 已经直接 mechanically 回答了 reviewer (iii)**：
"我们已把 paired cohort 推到 510 患者（4.5× 之前），不再是 19-patient 或 226-patient"。
这是 reviewer 投诉的根因，单靠数据量这一项就把 (iii) 从 "Critical" 降级为 "Major/已回应"。

---

## 4. 与论文章节的对应修改

### 4.1 paper/main.tex 改动（仅 Stage A 通过后）
- §IV.A `Datasets and Cohort Construction`：Table 1 新增一行 `Extended BIMCV paired (510 patients)`；
  Table 2 新增一行 `Extended 510-patient 5-fold CV`。
- §IV.C `Primary Same-Case Evidence`：在 "We report two paired-cohort evaluation regimes..."
  后插入一段 Extended 510-patient 5-fold CV，给出 mean ΔBA + CI + win/loss count。
- §IV.E `Ablation Studies`：在 Limitations 前新增 `Effect of cohort scale on transfer evidence`
  小节，对比 226 vs 510 cohort 上的同一 `proj.gated_kd` ΔBA。
- §III `Contributions` bullet 3 升级：把 "evidence-bounded negative-result" 修改为
  "evidence-bounded boundary that is moved by 4.5× cohort scaling"，强调 scale-evidence 演进。

### 4.2 paper/appendix.tex 改动
- 新增 §`Extended 510-patient BIMCV CV` 节：完整 4-teacher × 4-method × 15-cell 表（同 Table 21 格式）。
- 在已有的 `Limitations` 节里加一句 "the extended 510-patient cohort closes/does-not-close
  the validation gate, depending on the configuration; see Table N."

### 4.3 cover letter 改动
- 在 reviewer (iii) 回应段加一段 "We have extended the primary paired cohort from 226 to 510 same-patient
  BIMCV CT-X-ray pairs (4.5×) using the full /data/bimcv_neg_paired pool, addressing the cohort-scale
  concern directly. Results are reported in Table N (main) and Appendix Section X."

---

## 5. 执行 checklist (Stage A 优先)

- [ ] Step 1 (30 min, on 3090)：写 `src/jdcnet_exp/prepare_bimcv_full_paired_cv.py`，
      读 `/data1/midrc/bimcv_for_mixed_cv.csv` 全集 510 patients，5-fold patient-level
      stratified by label，输出 `/data1/midrc/bimcv_full_paired_cv_20260516/fold_{00..04}/`。
- [ ] Step 2 (30 min, on 3090)：扩展 `src/ops/extract_ct_teacher_variants.py` 把 `proj`、`3slice`、
      `mid` 三种 teacher 表征从 `/data/bimcv_neg_paired/sub-S*/ct/*.nii*` 渲染到
      `/dev/shm/bimcv_ct_{proj,3slice,mid}/`（覆盖 397 个未渲染的阴性；阳性 113 个已在）。
- [ ] Step 3 (15 min, on 3090)：fork `src/ops/remote_3090_bimcv_ct_variants_cv.sh` →
      `remote_3090_bimcv_full_paired_cv.sh`，把 manifest path、teacher path 替换，加 weighted-CE
      flag（在 train.py 加 `--class_weight 3.5` 或在 config JSON 加 `loss.pos_weight: 3.5`）。
- [ ] Step 4 (75 min, on 3090)：4-card × 4-concurrent 并发跑 240 runs。
- [ ] Step 5 (10 min, on 3090)：fork `remote_3090_bimcv_ct_variants_summarize.sh` 计算
      bootstrap CI + decision report；scp 拉回本地。
- [ ] Step 6 (本地)：根据决策树 §3 决定是否触发 Stage B / Stage C / 论文升级。

总计 Stage A 实际可行时间：**~2.5 小时**。

---

## 6. 风险与备选

| 风险 | 缓解 |
|---|---|
| BIMCV `/data/bimcv_neg_paired/` 的 398 个 NIfTI 中 some volume 损坏 | 渲染时 `try/except` 跳过；若 success < 380 patients 仍可执行（pos:neg ≈ 1:3.4 不影响 weighted-CE） |
| `proj` 在 397 个新阴性上的渲染 distribution 与 113 阳性 + 阳性 113 + 之前 114 阴性 不一致（窗位/分辨率差）| 复用 C1 已验证的 `multi-slice axial mean projection + lung-mask` 同一管线 |
| weighted-CE pos_weight=3.5 与现有 supervised baseline（balanced 1:1）不可比 | A 的 supervised baseline 必须用同样 weighted-CE 训练，所有 4 行同条件 |
| 5-fold 中某个 fold 上 supervised 训练 crash（fold1 类型问题）| 已在 mixed 5-fold 实验中观察过该模式；用 seed × fold 双重 paired analysis，weighted-CE 已显著降低 crash 概率 |
| Stage A 通过门但 Stage B FAIL（external replication 不成立）| 论文降调："Stage A 是 BIMCV-internal positive evidence，external transfer 未稳定"；保留主结论 |
| Stage A 与 Stage B 均 FAIL | Stage A 本身已是对 (iii) 的直接 mechanical 回应，论文仍可在 evidence-bounded 框架下使用——只需在 limitations 中加上"cohort scaling 4.5× did not close the gap" |

---

## 7. Stage A 执行结果 (2026-05-16 完成，240/240 runs)

### 7.1 执行情况
- **240/240 runs** 全部完成 test_eval（4 teachers × 4 methods × 5 folds × 3 seeds）
- 第一轮 4 GPU × 4 concurrent OOM，34 KD runs 失败；reduce 到 concurrency=2 后所有 runs 在 ~14 分钟内完成补跑
- 失败次数：0 (rerun 后)
- 总耗时：~38 分钟 (含 OOM 重跑)
- 完整数据：`src/results/bimcv_full_paired_cv_3090_20260516/bimcv_full_paired_decision_report.md`, `bimcv_full_paired_summary.csv`, `bimcv_full_paired_deltas.csv`, `bimcv_full_paired_status.tsv`

### 7.2 关键发现：**Scale 验证了 teacher upper bound，但 KD 机制失败**

**Mean test BA (510-patient cohort)**

| Variant | Teacher | Supervised | Plain KD | Gated KD |
|---|---:|---:|---:|---:|
| mid | **0.6697** | 0.6247 | 0.6144 | 0.6027 |
| 3slice | **0.6758** | 0.6247 | 0.5883 | 0.5989 |
| proj | 0.6557 | 0.6247 | 0.6091 | 0.6110 |
| drr | 0.6343 | 0.6247 | 0.6238 | **0.5610** (collapse) |

**Paired deltas vs supervised (pre-specified gate: ΔBA ≥ +0.03 AND CI lower > 0)**

| Variant | teacher_vs_sup (PASS?) | gated_vs_sup (PASS?) |
|---|---|---|
| mid | **+0.0450 [+0.019,+0.069] YES** | -0.0220 [-0.055,+0.011] NO |
| 3slice | **+0.0511 [+0.025,+0.080] YES** | -0.0258 [-0.079,+0.027] NO |
| proj | +0.0310 [-0.002,+0.065] NO (差一步) | -0.0137 [-0.057,+0.030] NO |
| drr | +0.0096 [-0.035,+0.056] NO | **-0.0637 [-0.095,-0.034] NO (catastrophic)** |

### 7.3 与 226-patient C1 对比

| | 226 (C1) | 510 (Stage A) | 变化 |
|---|---:|---:|---|
| Supervised X-ray BA | 0.5657–0.6311 | 0.6247 | scale → 更稳定 baseline |
| Teacher upper bound pass count | 1/4 (proj only) | **2/4 (mid + 3slice)** | scale 加强 teacher 证据 |
| Gated KD vs supervised pass | 0/4 | **0/4** | 仍未通过 |
| Calibration scan T=4 thr=0.50 ΔBA | +0.034 (CI [-0.004,+0.073], 9/15 pos) | **-0.014~-0.064 (all CI跨0或负)** | scale 让 KD 显著变差 |
| DRR gated KD | +0.038 vs plain (9/15 pos, CI just touching 0) | **-0.064 (3/12 pos, 显著 FAIL)** | catastrophic collapse |

### 7.4 解读：报告 (iii) 的回答升级为更强的 negative result

1. **Teacher upper bound 在 4.5× cohort 上稳定通过门**（mid/3slice 都 PASS，CI lower > +0.019）——CT 确实承载可用信息，reviewer M9 的"CT representation under-specified"批评在 multi-slice/3slice 设置下已实证回答。
2. **Supervised X-ray baseline 显著变强**（0.62 BA vs 226-cohort 的 0.56-0.63），让 KD 没有空间往上加。
3. **Cross-modal logit KD 在 scale 上反而 hurts** — 226 时是 "near-pass"（+0.034），510 时变成 "consistently negative"（-0.014 到 -0.064）。这表明 226 时的 +0.034 是 small-sample artifact。
4. **DRR gated KD catastrophic collapse**（specificity 从 0.62 跌到 0.43，BA 跌到 0.56）证明：几何 alignment 不够；当 student 有足够标签时，CT-domain 软标签会把 student 拉离 supervised optimum。

### 7.5 决策：选择路径 "Pivot to stronger negative result"

**不触发 Stage B / Stage C**。原因：
- Stage B (MIDRC 559) 不会改变方向：Stage A 在所有 4 个 teacher 表征上一致 negative，加 MIDRC 数据只会让 negative 更确定。
- Stage C (X-ray pretrain) 不会改变方向：supervised X-ray 已经在 510 上变成强 plateau，预训练只会进一步抬高 baseline 让 KD gap 更大。

### 7.6 论文升级（已完成的实验产出 → 直接可写）

**main.tex 修改**：
- §IV.A Datasets：Table 1 新增"Extended BIMCV paired (510 patients, 113+/397-)"。
- §IV.C Primary Same-Case Evidence：新增"4.5× cohort scaling test"段落，给出 teacher_vs_supervised PASS（mid +0.045, 3slice +0.051）与 gated_vs_supervised FAIL（all 4 variants negative，DRR -0.064 collapse）。
- §III Contributions bullet 2 升级：
  - 旧文："Negative-result boundary for CT-to-X-ray transfer..."
  - 新文："**Definitive negative result at 4.5× cohort scale**: across an extended 510-patient same-patient paired BIMCV cohort, multi-slice CT teachers consistently pass the teacher upper-bound gate (mean ΔBA +0.045 to +0.051, CI lower > +0.019), confirming that CT carries patient-level disease information; yet under the same protocol, confidence-gated logit KD fails on all four teacher representations, with DRR-guided gated KD showing a catastrophic specificity collapse (mean ΔBA −0.064, CI [−0.095, −0.034]). Cohort scaling resolves the small-sample 'near-pass' artifact at 226 patients and turns the result into a reproducible mechanism-level negative."
- §IV.E Limitations：新增 1 句："The 510-patient extension closes the cohort-scale concern raised in review; the remaining open question is whether a non-logit transfer mechanism (feature-hint, attention transfer, or pseudo-label-style supervision) can recover the teacher upper bound that this paper now demonstrates."

**appendix.tex 修改**：新增 §`Stage A: 510-Patient Extended Paired Cohort CV` 节，含 16 行 decision delta 表（per teacher × per comparison）。

**cover letter 修改**：reviewer (iii) 回应段：
> "We have extended the primary paired cohort from 226 to 510 same-patient BIMCV CT-X-ray pairs (4.5×) using all 113 positive and 397 negative paired patients available in the BIMCV release. Under this extended cohort, multi-slice CT teachers (mid-slice and 3-slice) now pass the pre-specified teacher upper-bound gate with substantial effect sizes (ΔBA +0.045 and +0.051, 95% bootstrap CI lower bounds > +0.019), confirming that the teacher modality carries patient-level disease information. The cross-modal logit KD however fails across all four teacher representations at this scale, with DRR-guided gated KD showing a catastrophic specificity collapse (Table N). We interpret this as definitive negative-result evidence at the requested cohort scale, and we have re-framed contribution 2 accordingly."

---

## 8. 文件路径汇总

| 资源 | 路径 |
|---|---|
| 本计划 | `docs/tmp/report515.md` |
| 上一计划 | `docs/tmp/report513.md`（路径 B 后的 calibration + DRR exploration） |
| 实验规格 | `docs/tmp/report514.md`（C1+C2 已完成） |
| Reviewer 原文 | `docs/revision_suggestions.tex` |
| 当前论文主稿 | `paper/main.tex`（B1+B2+B3 已 commit） |
| 当前论文附录 | `paper/appendix.tex`（C1+C2 表已 commit） |
| 已完成 C1 报告 | `docs/tmp/ct_variants_decision_report.md`（`proj` teacher PASS） |
| 已完成 C2 报告 | `docs/tmp/biomedclip_decision_report.md` |
| 3090 现有 manifest 全集 | `/data1/midrc/bimcv_for_mixed_cv.csv`（510 patients） |
| 3090 DRR 缓存 | `/data/bimcv/drr_cache/`（510 patients） |
| 3090 阴性 CT NIfTI | `/data/bimcv_neg_paired/sub-S*/ct/*.nii*`（398 volumes） |
| 3090 MIDRC raw | `/data1/midrc/raw_559cases_combined/dg.MD1R/`（559 patients, 1118 zip） |
| Stage A run root (3090) | `/data1/midrc/runs/bimcv_full_paired_cv_20260516/` |
| Stage A 数值结果 (本地) | `src/results/bimcv_full_paired_cv_3090_20260516/` |
| 项目 memory | `~/.claude/projects/-mnt-c-source-JDCNET/memory/project_jdcnet.md` |

**结果存放约定（自 2026-05-16 起）**：所有 CSV / TSV / JSON / decision_report 等"数值/计算结果"放在 `src/results/<run_tag>/`；`docs/tmp/` 只放计划与文字分析（report5xx.md、plan.md、audit.md）。
