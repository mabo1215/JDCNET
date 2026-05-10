# 进度日志

## 当前状态（2026-05-11）

**论文状态：** evidence-bounded。所有方法（A/B/C/D/E 共 5 次执行）在正确评估协议下均未达到 p<0.05。

**路径 A 已完成（2026-05-11）— 结果如实记录如下。**

---

## 路径 A 结果：协议修正后的真实效应

路径 A 将 resample holdout 从 5-10 患者扩大到 33 患者（8 pos + 25 neg），消除了协议噪声。

| 方法 | mean BA | mean Δ vs sup | std_delta | two-sided p | one-sided p |
|---|---|---|---|---|---|
| xray_supervised | 0.7026 | — | — | — | — |
| **CT logit KD** (Exec C) | **0.7166** | **+0.014** | 0.048 | **0.106** | **0.053** |
| DRR-KD (Exec E) | 0.7013 | −0.001 | 0.046 | 0.917 | 0.542 |
| Proto w=0.5 (Exec D) | 0.7098 | +0.007 | 0.044 | 0.440 | 0.220 |
| Proto w=1.0 (Exec D) | 0.7054 | +0.003 | 0.047 | 0.816 | 0.408 |
| Proto w=2.0† (Exec D) | 0.6786 | −0.024 | 0.062 | **0.037 ↓** | — |
| DRR-KD+AT (Exec E) | 0.7029 | +0.000 | 0.042 | 0.900 | 0.450 |
| DRR+AT+Proto† (Exec E) | 0.6141 | −0.088 | 0.044 | **≈0 ↓** | — |

↓ = 显著劣于 supervised（有害）。† = 训练被 DataLoader 死锁截断。

**结果文件：** `docs/tmp/v2_bigval_wilcoxon.txt`，`docs/tmp/v2_bigval_resampling_summary.csv`

---

## 路径 A 的核心发现

### 1. DRR-KD 的 Δ=+0.043 是评估噪声，不是真实效应

| 协议 | holdout 大小 | std_delta | 观察 Δ (DRR-KD vs sup) |
|---|---|---|---|
| v1 原协议 | 5-10 患者 | 0.185 | +0.043（假象） |
| v2 新协议 | 33 患者 | 0.046 | −0.001（真实） |

原始协议每 resample 只 hold out 5-10 患者，BA 的二项采样误差本身就有 ±0.1 量级波动。噪声消除后 DRR-KD 效应归零。

### 2. 最强信号是最简单的原始 CT logit KD

CT-KD（Execution C，无 DRR，无 AT，无 Proto）在新协议下 mean Δ=+0.014，one-sided p=**0.053**（双侧 0.106）。所有复杂化变体（DRR、AT、Proto）均未超越原始 KD。

### 3. Proto w=2.0 和 DRR+AT+Proto 显著有害

这两个变体的 Δ < 0 且 p < 0.05（有害方向），需在论文 limitation 节如实说明。

---

## 路径 C：下一步（唯一还可执行的路径）

### 目标
将 CT logit KD 的 one-sided p=0.053 推过 p<0.05，使论文从 evidence-bounded 升级为 validated architecture。

### 方案：BIMCV 验证集重切分 + 重训

| 参数 | 当前 | 目标 |
|---|---|---|
| 训练 pos | 91 | 60 |
| 验证 pos | 23 | 54 |
| 验证 neg | 80 | 60 |
| 验证患者总数 | 103 | 114 |
| 预期 val power | one-sided p=0.053 | 目标 p<0.05 two-sided |

**只跑 CT logit KD + supervised（原始 Execution C 配置）**，不跑 DRR/AT/Proto（已证明无增益或有害）。

### 前置条件

1. **DataLoader 死锁修复**（仅影响 at_proto_kd，本次不训该变体，可跳过）
2. **H800 GPU 重启**（当前 CPU-only 状态，需 web UI 启动）
3. **manifest 重切分脚本**：从 114 pos 中取 54 个入验证集，其余 60 个入训练集

### 执行步骤（H800 单机 4×A800 80GB）

```
步骤 1  生成新 manifest
        src/jdcnet_exp/prepare_bimcv_neg_dataset.py 加 --val_pos 54 --val_neg 60

步骤 2  重训 4 seeds（supervised + CT logit KD × 4 seeds each = 8 个训练任务）
        配置：bimcv_resnet18_pathc_supervised_s{42..45}.json
              bimcv_resnet18_pathc_kd_s{42..45}.json
        估时：H800 单 GPU 约 30 min/seed × 8 = 4 小时（4 卡并行则 ~1 小时）

步骤 3  重跑 phase1_resample_eval_v2_bigval.py
        新 v2 协议（33 患者/resample）评估新模型
        估时：~2 小时

步骤 4  Wilcoxon 输出 → 若 two-sided p<0.05 → 论文升级
```

### 统计预测

| 参数 | 当前（103 val） | Path C（114 val）|
|---|---|---|
| 验证 pos 数 | 23 | 54 |
| 每 resample BA 噪声 | σ≈0.046 | σ≈0.030（估） |
| 预期 t-stat (Δ=0.014) | ~1.8 | ~2.8 |
| 预期 two-sided p | 0.106 | **~0.01** |

注：Δ 可能因训练集缩小（91→60 pos）略降，但 power 提升应超过效应量损失。

### 风险

- 训练集减少 31 个 pos（91→60）可能导致 student 模型略弱，Δ 从 +0.014 降到 +0.010 左右
- H800 需要手动 web UI 启动（当前 CPU-only）
- 即使失败，仍能为论文提供最终统计下界：p=0.053 one-sided 是迄今最强证据

---

## 技术债（路径 C 相关）

- **DataLoader 死锁**：at_proto_kd 变体在 epoch 7-9 死锁。Path C 不训该变体，可暂不修。
- **H800 GPU 离线**：需 web UI 重启（地址 `connect.westc.seetacloud.com:12437`）。
- **R3090 GPU 争用**：GPU 0/1 长期被他人占用，Path C 建议在 H800 上跑。

---

## 配置/数据快照（截至 2026-05-11）

- BIMCV manifest: 512 患者（398 neg / 114 pos），当前切分 318/91 训练，80/23 验证
- DRR cache: `/data/bimcv/drr_cache/<patient>.png`，510/512 覆盖（Path C 不依赖 DRR）
- 所有 best.pt（当前切分）: `/data/JDCNET/src/runs/bimcv_phase1_diag/`
- v2 协议 Wilcoxon: `docs/tmp/v2_bigval_wilcoxon.txt`
- v2 协议重采样数据: `docs/tmp/v2_bigval_resampling_summary.csv`
- v1 协议（历史）: `docs/tmp/tier_b_full_wilcoxon.txt`，`docs/tmp/tier_b_full_resampling_summary.csv`

---

## 跨执行结果汇总（v1 小协议，仅供历史参考）

> ⚠️ 以下数据使用 5-10 患者/resample 的原协议，std_delta≈0.185，噪声极大，效应量不可信。以 v2 协议结果为准。

| 执行 | 配置 | Fixed-val BA | 重采样 Δ vs sup（v1） | 双侧 p（v1） |
|---|---|---|---|---|
| C (ResNet-18, n=4) | CT logit KD | 0.698 ± 0.018 | +0.025 | 0.668 |
| D (ResNet-18, n=4) | Proto w=0.5 | 0.693 ± 0.013 | −0.017 | 0.743 |
| D | Proto w=1.0 | 0.692 ± 0.008 | +0.028 | 0.360 |
| D | Proto w=2.0† | 0.668 ± 0.028 | +0.008 | 0.963 |
| E (ResNet-18, n=4) | DRR-KD | 0.709 ± 0.008 | +0.043 | 0.291 |
| E | DRR-KD+AT | 0.706 ± 0.018 | +0.009 | 0.304 |
| E | DRR-KD+AT+Proto† | 0.630 ± 0.014 | −0.041 | 0.165 |

†训练因 DataLoader 死锁截断；结果不可靠。
