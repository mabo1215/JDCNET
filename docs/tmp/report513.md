结论先说清楚：**目前“代码/数据流程有效”，但“论文希望的 GAP-KD 框架有效性”还没有被实验证明。**  
现有结果只能支持“发现了一个弱正向、但不稳定的可靠性门控 KD 信号”，不能支持“validated architecture”。

---

## 1. 现有实验结论

### A. BIMCV / Cohen 旧实验

结论：**不能作为框架有效性的主证据。**

原因：

- Cohen 队列太小，阴性样本极少，BA / specificity 很容易退化。
- BIMCV Path-C 中：
  - supervised 与 plain KD 基本接近；
  - plain KD 没有稳定显著优于 supervised；
  - GAP-KD 模块有时提升，但不稳定。
- 3090 GAP-KD sweep 里，较好的配置是：

```text
confidence_gate_threshold = 0.55
projected_attention_weight = 0.0
```

也就是：**门控有一点帮助，projection attention 没有稳定帮助。**

但提升幅度只有约 `+0.009 BA`，太弱，不能支撑论文主张。

---

### B. MIDRC 126 balanced pilot

数据本身是有价值的：

```text
MIDRC chest paired subset:
126 cases = 63 positive + 63 negative
train/val/test ≈ 70/15/15
test ≈ 10 positive + 10 negative
```

优点：

- 比 Cohen 队列好很多；
- 阴性数量足够打破原来的 1-negative 退化问题；
- 数据路径、manifest、训练脚本都跑通了。

但问题是：**测试集太小。**

10/10 test split 会导致一个病例判断变化就影响 BA 约 0.05，所以 seed 波动很大。

---

### C. MIDRC short proof

`midrc_short_proof_h800` 的结果是：

```text
supervised mean BA ≈ 0.605
plain KD mean BA ≈ 0.605
GAP-KD mean BA ≈ 0.623
```

表面看 GAP-KD 有一点优势，但 per-seed 不稳定：

```text
seed 42: GAP-KD > supervised / plain KD
seed 43: GAP-KD < supervised / plain KD
seed 44: GAP-KD > supervised / plain KD
```

所以这个实验只能说明：

> GAP-KD 方向有可继续探索的信号，但不能证明框架有效。

---

### D. H800 locked validation

这是最关键的结果。根据已拉回的 locked validation summary：

```text
test BA mean:
teacher_ct             ≈ 0.433
xray_supervised        ≈ 0.467
plain_kd               ≈ 0.483
reliability_gated_kd   ≈ 0.450
```

per-seed GAP-KD 对比：

```text
seed 42: gated - supervised = +0.150, gated - plain = +0.050
seed 43: gated - supervised = -0.200, gated - plain = -0.100
seed 44: gated - supervised = +0.000, gated - plain = -0.050
```

所以 locked validation **失败**：

- 没有稳定超过 supervised；
- 没有稳定超过 plain KD；
- mean BA 也低于 plain KD；
- Macro-F1 方向也不稳定；
- test set 太小，无法做有力统计验证。

这说明当前 locked candidate：

```text
confidence_gate_threshold = 0.55
projected_attention_weight = 0.0
```

虽然是当前最保守的 GAP-KD 版本，但仍然没有达到论文希望的“框架有效性”。

---

## 2. 现有改进方法是否有效？

### 工程上：有效

已经完成：

- MIDRC / BIMCV manifest 混合队列；
- train/val/test split；
- label / paired relation 记录；
- H800 跑通；
- 3 seeds pilot 跑通；
- locked validation 跑通；
- 自动/远程调度流程基本可用。

所以工程链路没问题。

---

### 科学结论上：暂时无效

目前不能说：

> GAP-KD validated architecture works.

只能说：

> GAP-KD reliability-gated KD 有弱正向探索信号，但在 MIDRC locked validation 中未稳定优于 supervised 或 plain KD。

尤其关键问题是：

### CT teacher 本身太弱

locked validation 里 CT teacher test BA 只有约：

```text
0.43
```

如果 teacher 都不比 X-ray supervised 强，那么 KD 很难稳定带来提升。

这可能是当前失败的核心原因。

---

## 3. 当前最大问题

### 问题 1：Teacher 不可靠

现有 CT teacher 可能只是 mid-slice / 简化 CT 表征。  
COVID CT 信息本应比 X-ray 丰富，但现在 teacher 没体现出来。

所以 KD 变成了：

> 从一个不稳定 teacher 给 X-ray student 传递噪声。

门控可以减轻噪声，但不能创造可靠知识。

---

### 问题 2：test split 太小

MIDRC balanced 126 例里面只有 63 阳性。  
70/15/15 split 后 test 只有 20 例左右。

这不够做论文主验证。

想要达到原计划的：

```text
ΔBA ≥ +0.03–0.05
Wilcoxon p < 0.05
95% CI lower bound > 0
```

目前这个 test size 很难支撑。

---

### 问题 3：projection attention 暂时不成立

现有结果显示：

```text
projected_attention_weight > 0
```

没有稳定帮助，甚至可能引入跨模态错配。

所以短期内不要把 projection attention 当主贡献。

---

## 4. 下一步怎么改，才可能达到论文希望的框架有效性？

我建议不要马上继续完整 6 行矩阵。  
应该先做 **teacher 修复 + 更强验证协议**。

---

## 推荐路线

### Step 1：先确认 teacher upper bound

先单独提升 CT teacher。

目标：

```text
CT teacher test BA / AUC 明显高于 X-ray supervised
```

如果 teacher 仍然不强，GAP-KD 没有理论基础。

建议尝试：

1. **multi-slice CT teacher**
   - 不要只用单 slice；
   - 使用 3-slice / 5-slice / 9-slice 2.5D 输入。

2. **multi-window CT**
   - lung window；
   - mediastinal window；
   - bone window；
   - 拼成多通道输入。

3. **CT MIP / DRR / projection view**
   - 让 CT teacher 的表征更接近 X-ray；
   - 减少 CT-to-Xray domain gap。

4. **teacher calibration**
   - temperature scaling；
   - entropy / margin confidence gate；
   - 只传递 teacher 高置信且预测正确的样本。

判断标准：

```text
如果 CT teacher 不能稳定超过 X-ray supervised，停止 KD，先修 teacher。
```

---

### Step 2：保留 gating-only，暂停 projection attention

当前最合理候选仍是：

```text
confidence_gate_threshold = 0.55
confidence_gate_requires_correct = true
projected_attention_weight = 0.0
```

不要继续扩大 projection attention，除非先证明 attention map 有医学合理性或统计收益。

---

### Step 3：改验证协议

由于 MIDRC 只有 63 positive，单次 70/15/15 test 太小。

建议改成：

#### 方案 A：5-fold stratified patient-level CV

每 fold 大概：

```text
test ≈ 12–13 positive + 12–13 negative
```

然后汇总 5 folds 的 out-of-fold 结果。

好处：

- 每个病例都能作为 test 一次；
- 比单一 10/10 test 更稳定；
- 可以做 paired statistical test。

#### 方案 B：repeated stratified split

例如：

```text
10 repeats × 70/15/15
```

但需要严格预注册，不能根据结果挑 split。

---

### Step 4：重新定义最小验证矩阵

先不要跑完整 6 行，先跑 locked 4 行：

```text
1. CT teacher
2. X-ray supervised
3. plain CT logit KD
4. reliability-gated KD
```

只有当 gated KD 满足：

```text
每个 seed / fold 大多数为正
mean ΔBA ≥ +0.03
Macro-F1 同方向提升
specificity 不崩
CI lower bound > 0
```

再扩展到完整 6 行矩阵。

---

### Step 5：BIMCV + MIDRC mixed 只作为诊断，不作为主验证

BIMCV + MIDRC 混合可以继续用于：

- 训练增强；
- 正负比例调节；
- source-bias stress test；
- hyperparameter sanity check。

但不建议作为论文主验证，因为：

```text
BIMCV mostly positive
MIDRC balanced / negative-rich
```

会引入 source-label confounding。

最终验证必须是：

```text
patient-level split
same dataset distribution
source-stratified or single-source evaluation
```

---

## 5. 论文层面的当前表述建议

目前论文不能写：

> GAP-KD framework is validated.

更稳妥写法是：

> We developed and audited a reliability-gated cross-modal KD framework.  
> Across BIMCV and MIDRC pilots, reliability gating reduced some failure modes, but the current CT teacher and limited paired validation size did not yield statistically validated improvement over supervised or plain KD baselines.

如果后续 teacher-v2 + CV 成功，再升级为：

> validated architecture.

---

## 6. 我建议的立即行动

优先级如下：

1. **不要继续完整 6 行矩阵。**
2. 先做 CT teacher v2：
   - multi-slice；
   - multi-window；
   - teacher calibration。
3. 对 MIDRC 126 balanced 做 5-fold patient-level CV。
4. 只跑 4 行 locked matrix。
5. 如果 gating-only 在 CV 中稳定超过 supervised 和 plain KD，再启动完整 6 行矩阵。
6. 如果仍失败，论文维持 evidence-bounded negative-result / audit framing。

最关键一句：

> 当前失败不是 manifest 或 dataloader 问题，而是 teacher reliability + validation power 不足。下一步应该先证明 CT teacher 有信息优势，再证明 gated KD 能把这个优势稳定转移到 X-ray student。

---

## 7. 2026-05-13 作者决策：teacher upper bound 优先 + 混合队列扩大验证规模

本轮决策采用以下推进路线，作为后续 H800 无卡预处理与有卡训练的执行依据。

### 7.1 总原则

当前不再直接扩大完整 6 行矩阵。先解决两个核心瓶颈：

1. **CT teacher upper bound 不足**：必须先证明 CT teacher 的 test BA / AUC 稳定高于 X-ray supervised。
2. **test split 太小**：通过可控 manifest / index 机制，协调 BIMCV 阳性样本与 MIDRC 阴性样本比例，扩大可支撑的验证规模。

如果 CT teacher 不能稳定超过 X-ray supervised，则停止 KD 主实验，继续修 teacher；不再用不可靠 teacher 训练 GAP-KD。

### 7.2 H800 无卡预处理决策

先在 H800 无卡模式下完成数据清单与比例控制，不占用 GPU：

- 使用现有 `src/` 中的数据调控与 manifest 生成代码；
- 训练阶段只读取生成后的调控表 / index，不直接临时拼数据；
- index 中记录：
  - 数据来源：BIMCV / MIDRC；
  - patient id；
  - CT 路径；
  - X-ray 路径；
  - label；
  - split：train / val / test；
  - 配对关系；
  - source-stratified 标记。

混合策略：

- BIMCV 用于补充阳性病例；
- MIDRC 用于补充阴性病例；
- 通过人为设置 positive / negative 比例，构造更大的 train / val / test；
- 目标是解决单一 MIDRC 126 balanced cohort 下 test size 过小的问题。

方法学保护：BIMCV + MIDRC 混合验证必须报告 source-stratified 结果，避免把“数据来源差异”误判为“疾病标签差异”。混合队列可以作为扩大验证和诊断队列；若要作为论文主验证，需要额外证明结果不是 source-label confounding。

### 7.3 Teacher upper bound 四阶段修复顺序

后续 teacher 修复按以下顺序轮流推进，每一步都先看 CT teacher 是否明显超过 X-ray supervised。

#### 阶段 1：multi-slice CT teacher

不再只依赖 single mid-slice。优先尝试：

- 3-slice 2.5D；
- 5-slice 2.5D；
- 9-slice 2.5D。

成功标准：CT teacher 的 BA / AUC 在 validation 和 test 上均稳定高于 X-ray supervised。

#### 阶段 2：multi-window CT teacher

将 CT window 信息拼成多通道输入：

- lung window；
- mediastinal window；
- bone window。

目标是让 teacher 更充分利用 CT 信息，而不是只学习单一窗宽下的弱表征。

#### 阶段 3：CT MIP / DRR / projection view

构建更接近 X-ray 成像几何的 CT 表征：

- MIP；
- DRR；
- projection-like view。

目标是减少 CT-to-X-ray domain gap，使 teacher 的知识更容易迁移给 X-ray student。

#### 阶段 4：teacher calibration 与可靠性门控

在 teacher 具备上界优势后，再做 calibration：

- temperature scaling；
- entropy gate；
- margin confidence gate；
- only-correct teacher gate；
- 只传递 teacher 高置信且预测正确的样本。

如果 calibration 后 teacher 的 reliable subset 太小，也要记录 active gate fraction，避免 KD 训练实际没有足够有效监督。

### 7.4 GAP-KD 方法锁定

在 teacher 修复阶段后，KD 只保留 conservative gating-only 版本：

```text
confidence_gate_threshold = 0.55
confidence_gate_requires_correct = true
projected_attention_weight = 0.0
```

暂时暂停 projection attention。除非后续单独证明 projection attention 在 source-stratified / CV 结果中稳定有效，否则不作为主贡献。

### 7.5 验证协议修改

优先采用：

```text
5-fold stratified patient-level CV
```

如果 5-fold 因数据或工程原因暂时不可行，再使用：

```text
repeated stratified split
```

但 repeated split 必须预注册 split 数、随机种子、比例和决策标准，不能根据结果挑选 split。

### 7.6 最小验证矩阵

teacher upper bound 达标后，先跑 4 行 locked matrix：

```text
1. CT teacher
2. X-ray supervised
3. plain CT logit KD
4. reliability-gated KD
```

只有当 reliability-gated KD 满足以下条件，才扩展到完整 6 行矩阵：

```text
每个 seed / fold 大多数为正
mean ΔBA ≥ +0.03
Macro-F1 同方向提升
specificity 不崩
95% CI lower bound > 0
```

### 7.7 失败分支

如果完成 teacher 修复、混合队列扩大、5-fold / repeated validation 后，GAP-KD 仍不能稳定超过 supervised 和 plain KD，则论文维持：

```text
evidence-bounded negative-result / audit framing
```

不再强行声称 validated architecture。

---

## 8. 2026-05-14 3090 BIMCV-only 4-row 5-fold CV 结果

本轮在 3090 四卡远端完成了 BIMCV-only same-source paired pilot。核心目的是排除 MIDRC/BIMCV mixed CV 中的跨机构 source/domain shift，测试“同一 BIMCV 患者的 DRR teacher 是否比 X-ray supervised 更有信息优势，以及 gated KD 是否能稳定转移该优势”。

### 8.1 执行状态

```text
数据：BIMCV-only balanced patient-level 5-fold CV
样本：228 patients = 114 positive + 114 negative
每折 test：fold0-3 为 23+/23-，fold4 为 22+/22-
矩阵：5 folds × 3 seeds × 4 rows = 60 runs
完成度：60/60 best.pt，60/60 test_eval
远端：3090 10.147.20.176
本地结果：src/results/bimcv_only_5fold_cv_3090_20260514/
```

四行矩阵：

```text
1. teacher_drr
2. xray_supervised
3. plain_kd
4. gated_kd_thr055_proj0000
```

执行中为了压榨 4 张 3090，采用多 independent run 并发调度；最终配置主要为 `batch_size=1024` / `num_workers=16` / `input_size=224`，部分较早启动 run 保留 `batch_size=128/256`。由于每折训练样本很小，继续增大 batch size 不再显著增加 GPU 利用率，瓶颈转为小数据集和 run 数量。

### 8.2 主要数值结果

15 个 fold-seed cell 上的均值：

| row | mean BA | 95% CI | mean Macro-F1 | mean specificity | mean AUC |
|---|---:|---:|---:|---:|---:|
| teacher_drr | 0.6403 | [0.6076, 0.6722] | 0.6262 | 0.7220 | 0.7059 |
| xray_supervised | 0.5657 | [0.5309, 0.6010] | 0.5358 | 0.5057 | 0.6208 |
| plain_kd | 0.5368 | [0.5031, 0.5693] | 0.5207 | 0.5390 | 0.5753 |
| gated_kd_thr055_proj0000 | 0.5803 | [0.5466, 0.6121] | 0.5608 | 0.5906 | 0.5922 |

paired BA delta：

| comparison | mean ΔBA | 95% CI | positive / zero / negative |
|---|---:|---:|---:|
| teacher - supervised | +0.0746 | [+0.0314, +0.1144] | 12 / 0 / 3 |
| plain KD - supervised | -0.0290 | [-0.0842, +0.0240] | 7 / 0 / 8 |
| gated KD - supervised | +0.0146 | [-0.0264, +0.0531] | 9 / 1 / 5 |
| gated KD - plain KD | +0.0435 | [+0.0052, +0.0858] | 7 / 4 / 4 |
| gated KD - teacher | -0.0600 | [-0.1011, -0.0133] | 3 / 0 / 12 |

### 8.3 解释

这组结果有一个明确的正向信号，但仍不能升级为 validated architecture。

正向部分：

- **same-source BIMCV DRR teacher 成立**：teacher_drr mean BA `0.6403`，比 X-ray supervised 高 `+0.0746`，95% CI lower bound `+0.0314`，15 个 fold-seed cell 中 12 个为正。
- 这说明 mixed CV 失败很可能包含明显的跨机构 / 跨源域差因素；在同源 BIMCV 内，DRR teacher 的确比 X-ray supervised 捕获了更多可用信号。
- **reliability gate 有效削弱 plain KD 退化**：plain KD 比 supervised 低 `-0.0290`，而 gated KD 比 plain KD 高 `+0.0435`，且 CI lower bound 为正。

限制部分：

- **gated KD 仍未稳定超过 supervised**：gated KD - supervised mean ΔBA 只有 `+0.0146`，CI 为 `[-0.0264, +0.0531]`，lower bound 仍小于 0。
- gated KD 明显低于 teacher：gated KD - teacher mean ΔBA `-0.0600`，说明 teacher 的上界优势没有被充分转移到 X-ray student。
- 单折 test 仍只有 22/22 或 23/23，低于原始 validation gate 要求的 `≥50+/50-`。虽然 5-fold 聚合覆盖 114+/114-，但每个 fold 的决策方差仍然较大。

### 8.4 对论文结论的影响

这组实验可以支持一个更精确的中间结论：

> In a same-source BIMCV paired setting, the DRR teacher has a measurable upper-bound advantage, and reliability gating partially rescues the degradation of plain KD. However, the gated student does not yet achieve a statistically reliable improvement over the supervised X-ray baseline.

因此论文可以增加一个 **BIMCV same-source paired pilot** 作为 limited positive evidence，但主叙事仍应保持：

```text
evidence-bounded negative / diagnostic benchmark
```

不能写成：

```text
GAP-KD validated architecture works.
```

当前最稳妥的结论是：

1. teacher upper-bound 在 same-source BIMCV 中成立；
2. plain KD 会退化；
3. reliability gating 能部分修复 plain KD；
4. 但 gated KD 尚未稳定超过 supervised，因此框架有效性仍未被验证成功。
