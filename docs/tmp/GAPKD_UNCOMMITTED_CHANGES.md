# GAP-KD/JDCNet-v2 本地未提交修改总结

**修改状态**: 2026-05-11 | **修改数**: 13 个文件 | **总行数**: 610 insertions, 472 deletions

---

## 📋 修改文件清单

### ✨ 新增文件（Untracked）

1. **`src/jdcnet_exp/smoke_gapkd.py`** - GAP-KD CPU smoke test
   - 验证 confidence-gated KD、projected attention loss、一步学生更新
   - 不依赖 GPU 或本地数据集
   - 5/5 checks: confidence gate、distillation loss、attention loss、optimizer step、backward pass

2. **`src/ops/h800_gapkd_cpu_smoke.sh`** - H800 CPU smoke test 执行脚本
   - SSH 到 H800 并运行 smoke_gapkd.py 的无卡环境
   - 结果保存到 `src/results/h800_gapkd_cpu_smoke/`

3. **`src/ops/launch_h800_gapkd_cpu_smoke.ps1`** - H800 smoke test PowerShell 启动器
   - Windows PowerShell 脚本，调用上述 bash 脚本
   - 包含结果拉取逻辑

---

### 🔧 修改文件（Modified）

#### **代码框架核心修改**

1. **`src/jdcnet_exp/config.py`** (+7 lines)
   - 新增 `DistillationConfig` 参数（GAP-KD）:
     ```python
     confidence_gate_enabled: bool = False
     confidence_gate_threshold: float = 0.0
     confidence_gate_floor: float = 0.0
     confidence_gate_power: float = 1.0
     confidence_gate_requires_correct: bool = True
     projected_attention_weight: float = 0.0
     ```
   - 用途：控制置信度门控和投影对齐的启用/禁用及参数

2. **`src/jdcnet_exp/distillation.py`** (+89 lines)
   - **修改 `distillation_loss` 函数**:
     - 新增 `sample_weights: torch.Tensor | None` 参数
     - 如果有样本权重，按样本计算 KL divergence，然后加权求和
     - 支持每样本的蒸馏强度调整（置信度门控）
   
   - **新增 `teacher_confidence_gate()` 函数**:
     ```python
     def teacher_confidence_gate(
         teacher_logits: torch.Tensor,
         labels: torch.Tensor,
         threshold: float = 0.0,
         floor: float = 0.0,
         power: float = 1.0,
         requires_correct: bool = True,
     ) -> torch.Tensor
     ```
     - 计算按样本的蒸馏权重 $q_i$
     - 当 teacher 不确定 → 降低权重
     - 当 teacher 预测错误 (if `requires_correct=True`) → 权重为 0
     - 支持幂次变换实现非线性加权
     - 返回 detached 权重（梯度不回传到 teacher）
   
   - **修改 `attention_transfer_loss()` 函数**:
     - 现在直接调用新的 `projected_attention_loss()`
   
   - **新增 `projected_attention_loss()` 函数**:
     ```python
     def projected_attention_loss(
         student_feature: torch.Tensor,
         teacher_feature: torch.Tensor,
         anatomical_mask: torch.Tensor | None = None,
         confidence_weights: torch.Tensor | None = None,
     ) -> torch.Tensor
     ```
     - 投影兼容的空间注意力对齐
     - 支持解剖学掩码 (lung mask) 以避免模型学到非肺部特征
     - 支持置信度加权（与 confidence gate 配合）
     - 当 teacher feature shape ≠ student feature shape 时，插值调整

3. **`src/jdcnet_exp/train.py`** (+19 lines)
   - 导入新的 loss 函数：
     - `teacher_confidence_gate`
     - `projected_attention_loss`
   
   - 在训练循环中新增：
     ```python
     kd_sample_weights = None
     if config.distillation.confidence_gate_enabled:
         kd_sample_weights = teacher_confidence_gate(
             teacher_logits=teacher_logits,
             labels=labels,
             threshold=config.distillation.confidence_gate_threshold,
             floor=config.distillation.confidence_gate_floor,
             power=config.distillation.confidence_gate_power,
             requires_correct=config.distillation.confidence_gate_requires_correct,
         )
     ```
   - 在 `distillation_loss()` 调用时传入 `sample_weights=kd_sample_weights`
   - 在 `projected_attention_loss()` 调用时传入 `confidence_weights=kd_sample_weights`

#### **文档与实验计划修改**

4. **`docs/progress.md`** (-58 lines, 重组)
   - 总结 GAP-KD 框架已启动状态
   - 清晰列出"已完成"、"未修改或部分修改"、"遗留问题"三个部分
   - 新增"当前 H800 无卡 smoke 实验已完成"记录
   - 标记"GAP-KD 只有代码和 CPU smoke，不应写成论文有效性结果"

5. **`docs/tmp/experiment_plan.md`** (+138 lines, 重组)
   - 添加"新代码路径已为 GAP-KD/JDCNet-v2 打开"说明
   - 明确"本地 smoke test 通过、H800 CPU smoke test 通过"
   - 重申"这是实现就绪检查，不是论文证据"
   - 新增"条件：仅当新 paired cohort 可用时，才值得启动新实验"
   - 新增"最小实验矩阵"（只有新 cohort 才需要跑）

6. **`docs/tmp/jdcnet_upgrade_plan.md`** (+205 lines, 重组)
   - 完整记录"不能靠继续调 DPE/MHRA/DFPN 证明框架有效性"的结论
   - 详细说明 GAP-KD 的 5 个模块（Module A~E）：
     - **Module A**: 多 window、多 slice CT teacher（而不是单 slice）
     - **Module B**: 几何感知投影桥（DRR/MIP/learned projection）
     - **Module C**: 置信度门控 KD（本次实现）
     - **Module D**: 解剖学约束的注意力转移（本次实现）
     - **E**: source-bias robust training（数据采集源的鲁棒性）
   - 最小实验矩阵表格（6 行对比）
   - 成功标准必须预注册（Δ BA ≥ +0.03~0.05、paired Wilcoxon、95% CI）
   - 数据要求说明（必须新 cohort，而不是 BIMCV 512 患者的重新切割）

#### **其他修改**

7. **`.gitignore`** (+2 lines)
   - 新增忽略规则，适应 GAP-KD 相关的临时文件

8. **`src/ops/pull_3090_pathc_results.ps1`** (226 lines reformat)
   - 重新整理脚本格式（主要是行号调整，逻辑无变）

9. **`src/ops/pull_h800_pathc_results.ps1`** (200 lines reformat)
   - 重新整理脚本格式（主要是行号调整，逻辑无变）

10. **`docs/tmp/h800_pathc/analyze_partial.py`** (80 lines reformat)
    - 代码格式调整

11. **`docs/tmp/h800_pathc/manual_stop_summary.md`** (+2 lines)
    - 添加注记

12. **`docs/tmp/h800_pathc/remote_status.txt`** (56 lines reformat)
    - 状态记录调整

13. **`paper`** (modified content, untracked content)
    - 子模块更新（论文代码库 JDCNET_Overleaf）
    - Main.tex / appendix.tex 已更新 GAP-KD 相关的 limitations/future work

---

## 🎯 GAP-KD 核心改动三要点

### 1. **置信度门控 KD（Module C）**

**问题**: 之前的 plain KD 无条件蒸馏，可能转移 CT 中的 shortcut 或错误信息到 X-ray 学生。

**解决**: 
$$\lambda_i = \lambda_0 \cdot q_i$$
$$q_i = \mathbf{1}[\hat{y}_T = y_i] \cdot \text{Conf}(T_i) \cdot \text{floor}$$

- 当 teacher 预测错误 → $q_i = 0$（不蒸馏）
- 当 teacher 不确定（低置信度） → $q_i$ 接近 0
- 有 floor 值 → 即使不符合条件，也保留最小蒸馏强度
- 硬分类损失（CE）仍然对所有样本有效

**配置参数**:
- `confidence_gate_enabled`: 开启/关闭
- `confidence_gate_threshold`: 置信度最低阈值
- `confidence_gate_floor`: 最小权重（如 0.05）
- `confidence_gate_power`: 幂次（如 1.0 为线性，< 1.0 为缓和）
- `confidence_gate_requires_correct`: 是否要求 teacher 预测正确

### 2. **投影兼容的注意力对齐（Module D）**

**问题**: 之前的注意力转移是全图 feature map 对齐，过于粗糙，可能让模型学边框、设备等伪特征。

**解决**:
$$L_{\text{attn}} = \| M_{\text{lung}} \odot A_S - M_{\text{lung}} \odot \Pi(A_T) \|_1$$

- $A_S$: X-ray 学生的注意力图
- $A_T$: CT teacher 的注意力图
- $\Pi(A_T)$: CT 注意力投影到 X-ray 平面（或插值调整大小）
- $M_{\text{lung}}$: X-ray 肺部掩码（可选）
- 限制在肺部区域 → 避免学习非疾病信息
- 提高 radiological interpretability

**配置参数**:
- `projected_attention_weight`: 注意力损失权重（如 0.5）
- 支持通过 `anatomical_mask` 参数传入肺部掩码

### 3. **样本级蒸馏加权**

**实现**:
- `distillation_loss()` 接受 `sample_weights` 参数
- 如果无权重 → 传统 KL divergence（batchmean reduction）
- 如果有权重 → 按样本计算 KL div，加权求和
- `projected_attention_loss()` 也支持 `confidence_weights` 参数
- 两个 loss 都可以用同一组置信度权重 $q_i$

---

## ✅ 本地 & H800 Smoke Test 结果

### 本地 CPU Smoke Test
```
src/results/gapkd_cpu_smoke_local/smoke_gapkd.json
5/5 checks passed:
  ✓ build teacher/student models
  ✓ forward logits and feature maps
  ✓ confidence gate weights
  ✓ distillation loss with sample weights
  ✓ optimizer step
```

### H800 无卡 CPU Smoke Test
```
src/results/h800_gapkd_cpu_smoke/smoke_gapkd.json
5/5 checks passed
src/results/h800_gapkd_cpu_smoke/smoke.log (详细日志)
src/results/h800_gapkd_cpu_smoke/remote_status.txt (远端状态)
```

**结论**: 代码框架就绪，无语法错误，无 GPU 依赖。

---

## 📌 下一步行动

### Phase 1: MIDRC 数据审计（立即开始）
- [ ] 检查 H800 `/root/autodl-tmp/midrc/` 的实际下载状态
- [ ] 验证文件完整性（MD5 校验）
- [ ] 确认 559 cases paired manifest 是否已全部下载

### Phase 2: MIDRC 数据准备（如数据完整）
- [ ] 创建 `prepare_midrc_dataset.py` 脚本
- [ ] 提取 DICOM → PNG（CT 中轴切片，X-ray 标准化）
- [ ] 生成 train/val/test 分组 JSON
- [ ] 预注册成功标准与实验矩阵

### Phase 3: GPU 训练（Phase 2 完成后）
- [ ] 6 行实验矩阵在 MIDRC 上并行运行
- [ ] 主指标：Balanced Accuracy（Δ BA ≥ +0.03~0.05）
- [ ] 统计方法：paired Wilcoxon + 95% CI
- [ ] 预期周期：12-18 天（6 methods × 100 epochs）

### Phase 4: 结果评估与论文更新（Phase 3 完成后）
- [ ] 如成功 (Δ BA ≥ +0.03)：升级论文为"validated architecture"
- [ ] 如未成功：保持 evidence-bounded 口径，但已尽最大努力
- [ ] 更新 limitations / contributions / results 章节

---

## ⚠️ 重要声明

**当前状态**:
- ✅ 代码框架就绪
- ✅ CPU smoke test 通过
- ❌ **未在真实 cohort 上训练**
- ❌ **不应将代码修改写成论文结果**

**论文口径**:
- 当前投稿：evidence-bounded，cross-modal KD unvalidated
- GAP-KD：pre-specified future work（已在 limitations/conclusion 中声明）
- 只有 MIDRC 上的 GPU 实验成功，才能升级为 validated architecture

---

## 📊 修改统计总结

| 文件 | 类型 | 修改 | 说明 |
|------|------|------|------|
| `smoke_gapkd.py` | New | - | 5-check smoke test |
| `h800_gapkd_cpu_smoke.sh` | New | - | H800 启动脚本 |
| `launch_h800_gapkd_cpu_smoke.ps1` | New | - | PowerShell 启动器 |
| `config.py` | Modified | +7 | 新增 6 个参数 |
| `distillation.py` | Modified | +89 | 3 个新函数 |
| `train.py` | Modified | +19 | 训练循环集成 |
| `progress.md` | Modified | ±58 | 进度更新 |
| `experiment_plan.md` | Modified | ±138 | 实验计划更新 |
| `jdcnet_upgrade_plan.md` | Modified | ±205 | GAP-KD 详细设计 |
| 其他 | Modified | ±256 | 脚本格式、文档 |
| **总计** | **13 files** | **±610** | **+610, -472** |

---

**最后更新**: 2026-05-11 | **状态**: ✅ 代码框架 + ✅ 本地/远端 smoke test | ⏳ 等待 MIDRC 数据审计
