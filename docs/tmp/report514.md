# C1 + C2 实验任务规格 (2026-05-15)

> **目的**: 为 Codex 提供两个新实验（C1 multi-slice CT teacher 对比，C2 BiomedCLIP fine-tune baseline）的可执行规格。
> 这两个实验直接回应 TCSVT 审稿意见 R8 (stronger baselines), M8 (foundation-model fine-tune), M9 (CT representation under-specified)。
>
> **背景上下文文件**: `docs/revision_suggestions.tex`（审稿原文）、`paper/main.tex`、`paper/supplementary.tex`、`docs/tmp/drr_cv_decision_report.md`（已完成的 DRR 实验结果）。
>
> **已完成的工作**（不要重复）:
> - 立即文本修改 (A): 已 commit
> - B1 页数压缩、B2 TCSVT framing、B3 statistical protocol: 已 commit
> - DRR multi-seed pilot (165 runs): 结果在 `docs/tmp/drr_cv_decision_report.md`，结论 FAIL

---

## 0. 共用环境

### 0.1 计算资源

```
3090 服务器: mabo1215@10.147.20.176, 密码 mabo1215
工作目录:    /data/JDCNET_git
数据目录:    /data1/midrc/
GPU:         4× RTX 3090 (24 GB each)
登录命令:    sshpass -p mabo1215 ssh mabo1215@10.147.20.176
```

### 0.2 已有数据资产（不要重复下载）

| 资源 | 路径 | 备注 |
|---|---|---|
| BIMCV 平衡 CV manifests | `/data1/midrc/bimcv_only_cv_20260514/fold_0{0..4}/bimcv_only_fold0X_paired_manifest.csv` | 228 患者 (114+/114-)，5-fold |
| BIMCV X-ray 图像 (256×256) | `/data1/midrc/bimcv_xray_256/` | 已 resize |
| BIMCV X-ray 原始 | `/dev/shm/bimcv_paired/sub-S*/cxr/*.png` | manifest `image_path` 列指向此 |
| BIMCV CT mid-slice | manifest `teacher_image_path` 列 | 单中央轴位切片 PNG |
| BIMCV DRR 缓存 | `/data/bimcv/drr_cache/bimcv_S*.png` (源) → `/dev/shm/bimcv_drr/` (运行时) | 510 患者，224×224 灰度 |
| BIMCV CT volumes (NIfTI) | `/data1/midrc/bimcv_ct_nifti/` （**Codex 需先确认存在**） | 用于 C1 multi-slice 提取 |

### 0.3 参考脚本（直接复制改造，不要从零写）

| 脚本 | 用途 |
|---|---|
| `src/ops/remote_3090_bimcv_drr_cv.sh` | 主 launcher：生成 manifests + configs，4×3 GPU 并发 |
| `src/ops/remote_3090_bimcv_drr_summarize.sh` | 汇总：bootstrap CI + decision report |
| `src/ops/remote_3090_bimcv_drr_ext_seeds.sh` | 扩展模板 |

### 0.4 训练命令模板（已经在 3090 上验证可用）

```bash
cd /data/JDCNET_git && python3 -u -m jdcnet_exp.train --config <config.json>
cd /data/JDCNET_git && python3 -m jdcnet_exp.evaluate \
    --config <test_config.json> --checkpoint <best.pt> --output-dir <run_dir>/test_eval
```

### 0.5 Config 关键字段

- 必含：`distillation: {enabled: false}`、`data.val_modalities`
- Teacher 训练：manifest `image_path` 必须指向 teacher 图像（CT slice / DRR / multi-slice），`train_modalities: ["xray"]`（manifest `modality` 列恒为 `"xray"`，data.py 通过该列过滤）
- Student 训练：manifest `image_path` 指向 X-ray，`paired_image_column: teacher_image_path`
- KD gated 配置：`temperature=4.0, alpha=0.6, confidence_gate_threshold=0.50, confidence_gate_floor=0.0, confidence_gate_requires_correct=true`

### 0.6 决策门（pre-specified）

- 主端点: gated KD vs supervised on BIMCV-only balanced 5-fold CV (15 fold-seed cells, seeds 42-44)
- 通过门: mean ΔBA ≥ +0.03 AND 95% bootstrap CI lower bound > 0
- bootstrap 用 numpy.random + 10000 resamples（参考 `remote_3090_bimcv_drr_summarize.sh` 的 `bootstrap_ci()`）

---

## C1. Multi-slice / Volume CT Teacher Comparison

### C1.1 审稿动机

> M9 原话: "If CT is claimed to be a richer teacher modality, the teacher should exploit CT more meaningfully... Add or emphasize multi-slice/volume teacher experiments."

当前 DRR pilot 只用单中央切片或 DRR 做 CT teacher，被 reviewer 视为 CT 信息使用不充分。需在同样的 BIMCV 5-fold CV 框架下对比 4 种 CT teacher 表征。

### C1.2 实验矩阵

4 种 teacher 表征（**全部从 `/data1/midrc/bimcv_ct_nifti/` NIfTI volume 提取**）：

| ID | Teacher 表征 | 提取方式 | 输出 |
|---|---|---|---|
| `mid` | mid-slice (现有) | 取轴位中央切片 | 224×224 灰度 PNG |
| `3slice` | 3-slice 中央 stack | 取中央切片 + 上下各 1 个（间隔 5 mm） | 3 通道 224×224 |
| `proj` | 多切片肺野投影 | 沿 axial 平均所有切片，可选 lung mask 加权 | 224×224 灰度 |
| `drr` | DRR (已有) | AP 投影 (沿 sagittal)，复用现有 cache | 224×224 灰度 |

每种 teacher 跑完整 4 行 × 5 folds × 3 seeds = **60 runs/teacher × 4 teachers = 240 runs**

每个 4-row matrix 复用 `remote_3090_bimcv_drr_cv.sh` 的 EXP1 段：
1. teacher（在该 teacher 表征上训练）
2. xray supervised（baseline，可复用已有 12 个 runs from DRR pilot）
3. plain logit KD
4. gated KD (T=4, thr=0.50)

### C1.3 实施步骤

**Step 1**: 检查 `/data1/midrc/bimcv_ct_nifti/` 是否存在，至少覆盖 226 patients（DRR cache 同样的 patient set，排除 S03048 + S05726）。
- 存在 → 进入 Step 2
- 不存在 → 写一份 `docs/tmp/c1_blocker.md`，列出缺什么数据，C1 暂停

**Step 2**: 写 `src/ops/extract_ct_teacher_variants.py`：
- 输入：NIfTI volume 路径
- 输出：3 种 teacher 表征（mid/3slice/proj）的 PNG 到 `/dev/shm/bimcv_ct_{mid,3slice,proj}/`
- DRR 复用 `/dev/shm/bimcv_drr/`
- 224×224 输出尺寸

**Step 3**: 复制 `remote_3090_bimcv_drr_cv.sh` → `remote_3090_bimcv_ct_variants_cv.sh`，参数化 teacher type（`TEACHER_TYPE=mid|3slice|proj|drr`）。
- TAG=`bimcv_ct_variants_cv_20260516`
- RUN_ROOT=`/data1/midrc/runs/bimcv_ct_variants_cv_20260516/<teacher_type>/`
- 每种 teacher 的 manifests 单独生成（teacher manifest 指向对应 PNG 路径）
- 4 GPU × 3 concurrent
- 4 teachers 顺序跑（每种内部 30 min）≈ **2 小时总时间**

**Step 4**: 写 `remote_3090_bimcv_ct_variants_summarize.sh`：
- 读取 4 种 teacher 的 run_root
- 每种独立计算 4 row × 15 cells 的 means + bootstrap CI
- 输出对比表 + decision report

**Step 5**: scp 结果回本地 `docs/tmp/ct_variants_decision_report.md` + `ct_variants_summary.csv`。

### C1.4 预期输出文件

```
3090: /data1/midrc/runs/bimcv_ct_variants_cv_20260516/{mid,3slice,proj,drr}/
3090: /data1/logs/bimcv_ct_variants_cv_20260516/decision_report.md
本地: docs/tmp/ct_variants_decision_report.md
本地: docs/tmp/ct_variants_summary.csv
```

### C1.5 论文产出（**不要 Codex 写论文段落**，user 自己改）

- supplementary.tex 新增 1 个表（4 teachers × 4 methods × means/CI）
- main.tex Limitations § 加 1 句："Multi-slice and projection-based CT teachers were also evaluated in Supplementary~\\ref{sec:ct_variants}; none closes the validation gate."
- 预期结论：极可能仍 FAIL（数据规模瓶颈），但可以 cleanly 回答 M9

---

## C2. BiomedCLIP Fine-tune Baseline

### C2.1 审稿动机

> R8 原话: "Consider foundation-model baselines with fine-tuning, not only frozen linear probing."
> M8: "Use a consistent backbone family for supervised, teacher, and KD comparisons. Include stronger X-ray-only baselines."

当前论文只在 supplementary 用 BiomedCLIP frozen-feature linear probe (E3/E4)，被 reviewer 视为太弱。需 fine-tune full visual encoder。

### C2.2 实验矩阵

**模型**: BiomedCLIP visual encoder (ViT-B/16, 224×224 input) + 二分类头 (2-layer MLP)
- HuggingFace ID: `microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224`
- 仅用 vision tower（忽略 text encoder）

**训练设置**:
- 3 seeds × 5 folds = **15 runs**
- 同 BIMCV-only balanced 5-fold CV 数据（226 patients）
- learning_rate: 1e-5（fine-tune ViT 用小 lr）
- batch_size: 32（ViT 显存比 ResNet 大）
- epochs: 50
- AMP, channels_last 同 baseline

**对比基准**（已有，直接引用）:
| Method | 已有结果 |
|---|---|
| ResNet18 supervised | BA=0.566 |
| ResNet18 teacher_drr | BA=0.640 |
| ResNet18 + gated DRR-KD (T=4, thr=0.50) | BA=0.580 |
| **BiomedCLIP fine-tuned (NEW)** | **要测** |

**目标比较**:
1. BiomedCLIP fine-tune vs ResNet18 supervised → 看 foundation model 是否更强 baseline
2. BiomedCLIP fine-tune vs ResNet18 + gated DRR-KD → 看是否 foundation model 已经吸收了 KD 能给的信息

### C2.3 实施步骤

**Step 1**: 检查 3090 是否能访问 HuggingFace：
```bash
sshpass -p mabo1215 ssh mabo1215@10.147.20.176 'pip show open_clip_torch 2>/dev/null || pip install open_clip_torch'
sshpass -p mabo1215 ssh mabo1215@10.147.20.176 \
  'python3 -c "import open_clip; m, p, _ = open_clip.create_model_and_transforms(\"hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224\"); print(m.visual)"'
```
失败 → 先在本机下载 cache，再 scp 到 3090 `~/.cache/huggingface/`

**Step 2**: 在 `src/jdcnet_exp/` 新增 `models/biomedclip_classifier.py`：
```python
import open_clip, torch.nn as nn
class BiomedCLIPClassifier(nn.Module):
    def __init__(self, num_classes=2, freeze_backbone=False):
        super().__init__()
        m, _, _ = open_clip.create_model_and_transforms(
            'hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224')
        self.visual = m.visual
        if freeze_backbone:
            for p in self.visual.parameters(): p.requires_grad = False
        self.head = nn.Sequential(nn.Linear(768, 256), nn.GELU(),
                                   nn.Linear(256, num_classes))
    def forward(self, x):
        return self.head(self.visual(x))
```

**Step 3**: 在 `src/jdcnet_exp/train.py` 模型工厂注册 `model.name == "biomedclip"` 分支。

**Step 4**: 写 `src/ops/remote_3090_bimcv_biomedclip_cv.sh`，模仿 DRR CV launcher 但只生成 1 row × 5 folds × 3 seeds = 15 configs。
- TAG=`bimcv_biomedclip_cv_20260516`
- learning_rate=1e-5, batch_size=32, num_workers=2
- 4 GPU × 1 concurrent (ViT 显存大) = 4 simultaneous
- 预计 ~30 分钟

**Step 5**: 复用 DRR summarize 脚本计算 means + bootstrap CI vs 已有 ResNet18 supervised baseline（取自 `/data1/midrc/runs/bimcv_only_5fold_cv_balanced/`）。

### C2.4 预期输出文件

```
3090: /data1/midrc/runs/bimcv_biomedclip_cv_20260516/
3090: /data1/logs/bimcv_biomedclip_cv_20260516/decision_report.md
本地: docs/tmp/biomedclip_decision_report.md
本地: docs/tmp/biomedclip_summary.csv
```

### C2.5 论文产出

- supplementary.tex 现有 "ImageNet-Pretrained ResNet18 and BiomedCLIP Frozen-Feature Baselines (E3, E4)" 节增补 1 段 + 1 行表（fine-tune 结果）
- main.tex 不需改

---

## D. 共享约束 / 常见坑

1. **不要修改 `paper/main.tex` 或 `paper/supplementary.tex`** —— C1+C2 只跑实验、写脚本、生成数据；论文段落 user 自己改
2. **完成后必须 commit** Bash 脚本（`src/ops/remote_3090_*.sh`）和结果（`docs/tmp/*_decision_report.md`、`*_summary.csv`）
3. **3090 不计费**，可放心跑；但避免影响其他人作业
4. **Manifest modality 列恒为 `"xray"`** —— teacher train 也用 `train_modalities=["xray"]`，靠 `image_path` 切换实际加载的图像（DRR 实验已踩过的坑，详见 `src/jdcnet_exp/data.py` 的 `_filter_manifest`）
5. **不要重新生成已有 manifests** —— C1+C2 都基于 `/data1/midrc/bimcv_only_cv_20260514/` 的 5-fold 划分
6. **每个 run 完成后必须执行 test_eval**（与 DRR 脚本相同模式：把 val_split 改成 test，跑 evaluate）

---

## E. 验收标准

**C2 完成 = 满足全部**:
1. `docs/tmp/biomedclip_decision_report.md` 存在并包含: BiomedCLIP fine-tune mean BA + CI vs ResNet18 supervised baseline (15 fold-seed cells)
2. `src/jdcnet_exp/models/biomedclip_classifier.py` 和 launcher 脚本已 commit
3. 3090 上 `/data1/midrc/runs/bimcv_biomedclip_cv_20260516/` 包含 15 个 run dirs，每个有 `test_eval/metrics.json`

**C1 完成 = 满足全部**:
1. `docs/tmp/ct_variants_decision_report.md` 存在并包含 4 种 teacher × 4 methods 的对比表
2. `src/ops/extract_ct_teacher_variants.py` + `src/ops/remote_3090_bimcv_ct_variants_cv.sh` 已 commit
3. 3090 上 4 种 teacher 各自的 run_root 包含 60 个 run dirs

**如果 C1 因 NIfTI 缺失而无法执行**：至少完成 C2 + 写一份 `docs/tmp/c1_blocker.md` 说明缺什么数据。

---

## F. 文件 / 资源清单

| 类别 | 路径 |
|---|---|
| 本规格 | `docs/tmp/report516.md` |
| 审稿原文 | `docs/revision_suggestions.tex` |
| 论文当前主稿 | `paper/main.tex` (411 行, 已 B1+B2+B3) |
| 论文 supplementary | `paper/supplementary.tex` (906 行) |
| DRR pilot 结果 | `docs/tmp/drr_cv_decision_report.md` |
| 项目 memory | `~/.claude/projects/-mnt-c-source-JDCNET/memory/project_jdcnet.md` |

---

## 2026-05-15 3090 execution completion: C1 + C2

- Remote: `mabo1215@10.147.20.176`.
- C1 run root: `/data1/midrc/runs/bimcv_ct_variants_cv_20260516/`.
- C2 run root: `/data1/midrc/runs/bimcv_biomedclip_cv_20260516/`.
- Completed at: 2026-05-15 12:42 UTC / 2026-05-16 00:42 NZST.
- GPU pressure settings:
  - C1: 4 x RTX 3090, `batch_size=512`, `num_workers=8`, 4 independent runs per GPU (16 concurrent runs total).
  - C2: GPU2/GPU3, `batch_size=64`, `num_workers=8`, BiomedCLIP full visual-tower fine-tune, 50 epochs, lr=1e-5.
- Completion:
  - C1: `240/240` runs completed with `test_eval/metrics.json`.
  - C2: `15/15` runs completed with `test_eval/metrics.json`.
- Local result files:
  - `docs/tmp/ct_variants_decision_report.md`
  - `docs/tmp/ct_variants_summary.csv`
  - `docs/tmp/ct_variants_deltas.csv`
  - `docs/tmp/biomedclip_decision_report.md`
  - `docs/tmp/biomedclip_summary.csv`
  - `docs/tmp/biomedclip_deltas.csv`
  - `docs/tmp/ct_variants_status.tsv`
  - `docs/tmp/biomedclip_status.tsv`
- Key conclusion:
  - C1: projection CT teacher itself is strongest (teacher BA 0.6760; teacher_vs_supervised Delta BA +0.0449, CI [0.0077, 0.0813]), but gated KD does not pass the pre-specified validation gate. No gated_vs_supervised or gated_vs_plain comparison passes.
  - C2: BiomedCLIP fine-tune BA is 0.6333. It is essentially tied with the C1 same-split ResNet18 supervised baseline (Delta BA +0.0022, CI [-0.0476, 0.0496]) and positive vs the older 228-patient BIMCV-only supervised baseline (Delta BA +0.0675, CI [0.0213, 0.1119]).
