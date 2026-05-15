# JDCNet TCSVT 实验蓝图更新 (2026-05-15) — 路径 B 后的新探索

> **决策背景**：Priority 2 calibration scan（T×threshold 8-cell，120 runs）全部失败（最近格 T=4, thr=0.50: ΔBA=+0.034，CI [-0.004, +0.073]）。已选择路径 B（evidence-bounded 写作）。  
> 但在最终提交前，存在三条低成本、高潜力的探索路径，值得在 3090 上快速验证。

---

## 1. 根因分析：为什么 gated KD 只有 20% 转移效率？

当前数字：teacher ΔBA = **+0.075**，gated KD ΔBA = **+0.015**，转移效率 = **20%**。

### 根因 1：模态空间错位（最主要）

```
CT 横断面切片 teacher  →  logit [p_covid, p_neg]
    ↑ 基于横断面特征校准的置信度

X-ray 正位 AP student  →  完全不同的特征空间
    ↑ 根本无法直接使用 CT-domain 的软标签
```

DRR（Digitally Reconstructed Radiograph）= 沿 AP 方向积分 CT 体积生成的合成 X-ray，**几何等价于真实 X-ray**。DRR teacher 的软标签标定在 X-ray 可见的解剖特征上，student 可以直接使用。

**关键代码确认**：`data.py` 中 `_load_rgb_image` 已有 `.convert("RGB")`，灰度 DRR PNG 无需任何代码修改。

**DRR 缓存可用性**：
- `/data/bimcv/drr_cache/`：510 个患者，224×224 灰度 PNG，9.6MB 总大小
- 228 平衡队列覆盖 226/228（缺 S03048 COVID+ 和 S05726 COVID-，排除后 226 患者 113+/113-）
- 文件命名：`bimcv_S{patient_id}.png`，直接映射现有 manifest

**历史对比（避免重复错误）**：Execution E（BIMCV 512-patient 不平衡队列）DRR-KD 崩溃（修正后 ΔBA ≈ -0.001）。原因：不平衡分割 + 无 gate 机制 + 不同 backbone。**当前设置完全不同**：平衡 5-fold + confidence gate + ResNet18，不存在直接可比性。

### 根因 2：梯度步数极少（次要）

```
160 训练样本 ÷ batch_size=256 → 1 batch/epoch × 50 epochs = 50 次梯度更新
普通 ImageNet KD 通常 >10,000 次
```

Fix：batch_size=64 → 3 batches/epoch × 50 epochs = 150 次（3×）；或 epochs=100 → 300 次（6×）。

### 根因 3：requires_correct=True 过滤有价值边界样本（轻微）

teacher BA=0.640 → 在测试集上错误率 36%，但 gate_active_fraction=0.88 说明训练集上 teacher overfit（正确率 >90%）。训练集上 teacher 不稳定的样本（correct but low-confidence）带有真实的不确定性信息，不应被全部过滤。

---

## 2. 三个实验计划

### 实验 1：DRR Teacher 5-fold CV（主实验，最高潜力）

**假设**：DRR→X-ray 模态差 ≪ CT切片→X-ray，KD 效率从 20% 提升到 50%+。

**数据集**：226 平衡患者（113+/113-，排除 2 个缺 DRR 的患者）

**矩阵**（与 CT mid-slice 实验完全对称）：
| 行 | 方法 | 说明 |
|---|---|---|
| 1 | DRR teacher | 用 DRR 图像训练教师，测上界 |
| 2 | X-ray supervised | baseline（对照，同分割） |
| 3 | Plain DRR logit KD | 无门控，看退化是否仍存在 |
| 4 | Gated DRR KD (T=4, thr=0.50) | 主候选（最优 T/thr from 扫描） |

**运行规模**：4 rows × 5 folds × 3 seeds（42,43,44）= **60 runs**

**决策标准（保持不变）**：gated_kd vs supervised ΔBA ≥ +0.03 AND CI lower > 0

**预计时间**：3090 四卡并行 ~2 小时

---

### 实验 2：Extended Seeds T=4.0, thr=0.50（快速统计功效）

**假设**：当前 9/15 pos 接近验证门槛，增加 seeds 45-47 可能收窄 CI 到 lower > 0。

**使用现有 CT mid-slice manifests**（228 患者）

**矩阵**：只运行 teacher_drr + xray_supervised + gated_kd（T=4, thr=0.50）× seeds 45,46,47

**运行规模**：3 rows × 5 folds × 3 seeds = **45 runs**

**统计分析**：与已有 seeds 42-44 合并 → 共 30 fold-seed cells，检查是否 CI lower > 0

**注意**：这是对扫描发现的最优格做进一步验证。需在论文中说明是探索性结果。

**预计时间**：~30 分钟

---

### 实验 3：Batch Size 敏感性（batch=64, epochs=50）

**假设**：3 batches/epoch × 50 epochs = 150 次梯度更新（当前 50 次的 3×），学生更充分收敛。

**配置**：T=4, thr=0.50，gated_kd only，seeds 42-44，使用现有 teacher_drr checkpoints

**运行规模**：5 folds × 3 seeds = **15 runs**

**对比**：与现有 batch=256 结果配对比较（同 fold-seed）

**预计时间**：~20 分钟

---

## 3. GPU 压榨策略

**3090 硬件**：4× RTX 3090 (24GB VRAM each)，CPU ~40 threads

**策略**：
- 全部 4 GPU（GPU 0,1,2,3）
- 每 GPU 3 并发（xargs -P 3）= 12 simultaneous runs
- /dev/shm 存放图像数据（DRR 9.6MB + CT slices 16MB + X-ray ~19MB）
- BIMCV 数据集极小（160 训练样本）→ 每 run 约 3-5 分钟
- 3 concurrent × 4 GPU = 12 run/批次，几乎 100% GPU 利用率

**总计**：120 runs / 12 concurrent ≈ 10 批 × ~4 min = **~40 分钟完成全部三个实验**

---

## 4. 实现路径

### Step 1：准备 /dev/shm DRR 数据
```bash
mkdir -p /dev/shm/bimcv_drr
cp /data/bimcv/drr_cache/bimcv_S*.png /dev/shm/bimcv_drr/
```

### Step 2：生成 DRR teacher manifests
Python 脚本：读取现有 5-fold manifests，替换 `teacher_image_path` 为 DRR 路径，排除 2 个缺失患者。

### Step 3：生成训练 configs 并并发启动
参照 `remote_3090_bimcv_calibration_scan.sh` 模式：
- Python 生成 JSON configs
- 4 screen 会话 × xargs -P 3 并发

### Step 4：汇总并生成 decision report
沿用 calibration scan 的 bootstrap CI 汇总逻辑。

---

## 5. 决策矩阵

| 实验结果 | 结论 | 论文处理 |
|---|---|---|
| 实验 1 DRR gated KD ΔBA ≥ +0.03，CI lower > 0 | **Validated architecture（DRR-guided）** | 升级 appendix pilot；可扩展 seeds 45-47 |
| 实验 2 合并 30 cells CI lower > 0 | **CT mid-slice gated KD 探索性通过** | appendix 明确标注 post-hoc 探索 |
| 实验 3 batch=64 ΔBA 明显提升 | **Gradient steps 是瓶颈** | 论文新增诊断结论 |
| 全部失败 | 维持 evidence-bounded 路径 B | 以诊断价值写入 appendix |

---

## 6. 文件路径

| 资源 | 路径 |
|---|---|
| 本计划 | `docs/tmp/report516.md` |
| 实验脚本 | `src/ops/remote_3090_bimcv_drr_cv.sh` |
| 汇总脚本 | `src/ops/remote_3090_bimcv_drr_summarize.sh` |
| 3090 DRR 图像 | `/dev/shm/bimcv_drr/bimcv_S{patient_id}.png` |
| 3090 run root | `/data1/midrc/runs/bimcv_drr_cv_20260515/` |
| 3090 logs | `/data1/logs/bimcv_drr_cv_20260515/` |
| 决策报告 | `/data1/logs/bimcv_drr_cv_20260515/decision_report.md` |
| 现有 CV manifests | `/data1/midrc/bimcv_only_cv_20260514/fold_0{0..4}/` |
| 现有 CT teacher ckpts | `/data1/midrc/runs/bimcv_only_5fold_cv_balanced/` |
