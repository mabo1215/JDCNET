# MIDRC Data Readiness Audit Checklist

**目的**: 在启动 GAP-KD 真实训练前，验证 MIDRC 数据的完整性与可用性  
**时间**: 2026-05-11  
**优先级**: 🔴 BLOCKING - GAP-KD 实验无法启动，直到 Phase 1 通过  

---

## Phase 1A: H800 现有数据检查

### ☐ Check H800 `/root/autodl-tmp/midrc/` 目录状态

```bash
# SSH 到 H800（终端已配置）
ssh -p 12437 root@connect.westc.seetacloud.com

# 检查 1: 目录大小
du -sh /root/autodl-tmp/midrc/

# 预期: 约 120-140 GB（137 GB expected from manifest）

# 检查 2: 文件数
find /root/autodl-tmp/midrc -type f | wc -l

# 预期: 1118 files (559 CT + 559 Xray, 2 per case)
#       如果 < 1100: 数据下载未完成

# 检查 3: 目录结构
find /root/autodl-tmp/midrc -type d -maxdepth 1

# 预期输出示例:
# /root/autodl-tmp/midrc
# /root/autodl-tmp/midrc/case_001
# /root/autodl-tmp/midrc/case_002
# ...
# 或者按 MIDRC subject_id 组织
```

### ☐ 诊断：数据下载是否完成？

| 检查项 | Pass Criterion | 如果失败 |
|-------|----------------|---------|
| 文件数 ≥ 1100 | ✓ 90% 下载完成 | ⏳ 需要恢复下载 |
| 总大小 ≥ 120 GB | ✓ 完整 | ⏳ 需要恢复下载 |
| 子目录 > 100 | ✓ 案例分布合理 | ⚠️ 检查 ZIP 解压 |

**决策**:
- [ ] **是**: 所有文件已下载 → 进入 Phase 1B
- [ ] **否**: 文件下载未完成 → 执行恢复下载脚本
  ```bash
  # 在 H800 上继续下载
  cd /root/autodl-tmp/midrc
  
  # 使用 gen3-client（如已安装）
  # gen3-client download-manifest \
  #   --profile=<profile> \
  #   --manifest=MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.manifest.json \
  #   --download-path=/root/autodl-tmp/midrc/
  
  # 或者重新跑之前的下载脚本
  # bash /root/autodl-tmp/midrc/download_559_cases.sh
  ```

---

## Phase 1B: 数据格式 & 完整性检查

### ☐ 检查 H800 数据的文件格式

```bash
ssh -p 12437 root@connect.westc.seetacloud.com

# 检查 1: 是否都是 ZIP 文件（来自 gen3-client）
find /root/autodl-tmp/midrc -name "*.zip" | head -5

# 预期: 很多 .zip 文件，每个案例 2 个（CT + Xray）

# 检查 2: 是否有 DICOM 文件（解压后）
find /root/autodl-tmp/midrc -name "*.dcm" | head -5

# 预期（如果已解压）: 很多 .dcm 文件

# 检查 3: 是否有混合格式（部分 ZIP，部分解压）
ls -lah /root/autodl-tmp/midrc/ | head -20
```

**诊断**:
- [ ] **所有都是 ZIP**: 需要解压 DICOM → 进入 Phase 1C
- [ ] **所有都解压了**: 跳过 Phase 1C，进入 Phase 1D
- [ ] **混合格式**: 不推荐，需要统一格式

### ☐ Phase 1C: 解压 DICOM ZIP 文件（如需要）

```bash
# 在 H800 上，批量解压所有 ZIP
cd /root/autodl-tmp/midrc

# 安全的解压脚本（保留原 ZIP）
for zf in *.zip; do
    # 用 unzip 创建同名目录
    unzip -q "$zf" -d "${zf%.zip}"
    echo "Extracted: $zf"
done

# 验证解压结果
find . -name "*.dcm" | wc -l
# 预期: 数千个 DICOM 文件（多个 slices per CT）
```

**预计时间**: 5-10 分钟（取决于 I/O）

### ☐ Phase 1D: MD5 校验（可选，但推荐）

```bash
# 本地拉取清单
scp -P 12437 root@connect.westc.seetacloud.com:/root/autodl-tmp/MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.manifest.json ./

# Python 脚本验证（本地运行）
python << 'EOF'
import json
import hashlib
from pathlib import Path

manifest = json.load(open('MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.manifest.json'))

# 采样 10 个文件验证（完全校验可能很慢）
import random
sample = random.sample(manifest, min(10, len(manifest)))

h800_root = "/root/autodl-tmp/midrc"

for item in sample:
    file_path = h800_root + "/" + item["file_name"]
    expected_md5 = item["md5sum"]
    
    try:
        with open(file_path, 'rb') as f:
            actual_md5 = hashlib.md5(f.read()).hexdigest()
        
        status = "✓" if actual_md5 == expected_md5 else "✗"
        print(f"{status} {item['file_name']}: {actual_md5} vs {expected_md5}")
    except Exception as e:
        print(f"✗ {item['file_name']}: {e}")
EOF

# 预期: 所有采样文件都 ✓ 通过
```

**如果所有文件都通过验证**:
- ✓ 数据完整性确认
- 进入 Phase 1E

---

## Phase 1E: 配对完整性检查

### ☐ 验证每个案例都有 CT + Xray

```python
# 在 H800 上运行 Python 脚本
python << 'EOF'
import json
from pathlib import Path
from collections import defaultdict

# 加载清单
manifest_path = "/root/autodl-tmp/MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.manifest.json"
with open(manifest_path) as f:
    manifest = json.load(f)

# 按 case_submitter_id 分组
cases = defaultdict(list)
for item in manifest:
    case_id = item["case_submitter_id"]
    modality = item.get("selected_modality", "unknown")
    cases[case_id].append(modality)

# 检查配对
unpaired = []
ct_only = []
xray_only = []
properly_paired = 0

for case_id, modalities in cases.items():
    if len(modalities) == 2 and "CT" in modalities and "CR" in modalities:
        properly_paired += 1
    elif "CT" in modalities and "CR" not in modalities and "DX" not in modalities:
        ct_only.append(case_id)
    elif "CR" in modalities or "DX" in modalities:
        if "CT" not in modalities:
            xray_only.append(case_id)
    else:
        unpaired.append(case_id)

print(f"✓ Properly paired: {properly_paired} cases")
print(f"✗ CT only: {len(ct_only)} cases")
print(f"✗ Xray only: {len(xray_only)} cases")
print(f"✗ Unpaired: {len(unpaired)} cases")
print(f"\nTotal cases: {len(cases)}")
print(f"Expected: 559")

if properly_paired >= 550:
    print("\n✓ 配对检查通过 (≥ 98% 配对)")
else:
    print(f"\n✗ 配对检查失败: 仅 {properly_paired}/559")
EOF
```

**预期结果**:
```
✓ Properly paired: 559 cases
✗ CT only: 0 cases
✗ Xray only: 0 cases
✗ Unpaired: 0 cases

Total cases: 559
Expected: 559

✓ 配对检查通过 (≥ 98% 配对)
```

---

## Phase 1F: COVID 标签分布检查

```python
# 确保 COVID+/- 平衡
python << 'EOF'
import json

manifest_path = "/root/autodl-tmp/MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.manifest.json"
with open(manifest_path) as f:
    manifest = json.load(f)

covid_pos = sum(1 for item in manifest if item.get("covid19_positive") == "Yes")
covid_neg = sum(1 for item in manifest if item.get("covid19_positive") == "No")

print(f"COVID positive: {covid_pos}")
print(f"COVID negative: {covid_neg}")
print(f"Total objects: {len(manifest)}")

# Note: 1118 objects = 559 cases × 2 modalities per case
print(f"Expected objects: 559 × 2 = 1118")
print(f"Actual objects: {len(manifest)}")

if abs(len(manifest) - 1118) < 10:
    print("✓ Object count OK")
else:
    print("✗ Object count mismatch")

# COVID 分布
pos_ratio = covid_pos / (covid_pos + covid_neg) if (covid_pos + covid_neg) > 0 else 0
print(f"\nCOVID+ ratio: {pos_ratio:.1%}")
if 0.4 <= pos_ratio <= 0.7:
    print("✓ COVID label balance OK")
else:
    print("⚠️ COVID label balance skewed")
EOF
```

**预期**:
- COVID+: ~350-400 objects (COVID+ cases)
- COVID-: ~350-400 objects (COVID- cases)
- 比例约 45%-55%

---

## Phase 1G: 本地清单验证（可选）

如果想在本地运行代码准备脚本，先验证清单：

```bash
# 下载清单到本地
scp -P 12437 root@connect.westc.seetacloud.com:/root/autodl-tmp/MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.manifest.json \
    src/data/midrc_manifests/

scp -P 12437 root@connect.westc.seetacloud.com:/root/autodl-tmp/MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.metadata.json \
    src/data/midrc_manifests/

# 本地验证清单有效
python -c "
import json
m = json.load(open('src/data/midrc_manifests/MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.manifest.json'))
print(f'Cases: {len(set([x[\"case_submitter_id\"] for x in m]))}')
print(f'Objects: {len(m)}')
"
```

---

## 总检查清单

| Phase | 检查项 | Pass? | 备注 |
|-------|--------|-------|------|
| 1A | H800 文件数 ≥ 1100 | ☐ | 如否 → 恢复下载 |
| 1A | H800 总大小 ≥ 120 GB | ☐ | 如否 → 检查磁盘 |
| 1B | 检查文件格式 (ZIP or DICOM) | ☐ | 如否 → 统一格式 |
| 1C | 解压 ZIP（如需要） | ☐ | 预计 5-10 min |
| 1D | MD5 采样验证 | ☐ | 可选，推荐 |
| 1E | 配对完整性 ≥ 550 cases | ☐ | 如否 → 调查 |
| 1F | COVID 标签分布 | ☐ | 如否 → 检查清单 |
| 1G | 本地清单下载 | ☐ | 可选，用于代码测试 |

---

## 如果 Phase 1 失败

### 场景 A: 数据下载未完成

```bash
# H800 上检查进程
pgrep -af "gen3-client|download"

# 如有进程: 等待完成
# 如无进程: 执行恢复下载
# 或重新运行原始下载脚本
```

### 场景 B: 文件损坏或不完整

```bash
# 删除损坏的 ZIP，重新下载
cd /root/autodl-tmp/midrc
find . -size -1M -name "*.zip" -delete  # 删除小于 1MB 的（可能是损坏的）

# 重新下载缺失的文件
# gen3-client download-manifest ...
```

### 场景 C: 解压失败

```bash
# 检查磁盘空间
df -h /root/autodl-tmp

# 预期: 至少 200 GB 空闲
# 如小于 100 GB: 清理其他文件或使用流式处理

# 仅解压需要的文件（而不是所有 ZIP）
# 见下面的"流式处理"方案
```

---

## Phase 2: 数据准备脚本（在 Phase 1 通过后）

一旦 Phase 1 通过，执行：

```python
# 创建 src/jdcnet_exp/prepare_midrc_dataset.py
python -m jdcnet_exp.prepare_midrc_dataset \
    --h800-midrc-root /root/autodl-tmp/midrc \
    --output-dir /root/autodl-tmp/midrc/prepared_559_paired \
    --manifest-json src/data/midrc_manifests/MIDRC_strict_chest_paired_559cases_largestCT_nearestXR.manifest.json
```

**预期输出**:
```
/root/autodl-tmp/midrc/prepared_559_paired/
├── manifest.json          (对齐格式)
├── case_001/
│   ├── ct_slice.png
│   ├── xray.png
│   └── metadata.json
├── case_002/
│   └── ...
└── split/
    ├── train.json (350 cases)
    ├── val.json (84 cases)
    └── test.json (125 cases)
```

---

## Timeline & Dependencies

```
Phase 1 (今天-明天)
├─ 1A-1B: 数据检查 (30 min)
├─ 1C: 解压 (5-10 min)
├─ 1D: MD5 验证 (10 min, optional)
├─ 1E-1F: 配对/标签验证 (5 min)
└─ 1G: 本地下载 (10 min, optional)
   └─> 决策: 数据就绪 Y/N?

Phase 2 (明天-后天)
├─ 创建 prepare_midrc_dataset.py
├─ 测试本地/H800 运行
└─ 生成 prepared_559_paired/ 目录

Phase 3 (后天-2 周)
├─ 锁参 4 行验证矩阵 GPU 训练
├─ 结果收集 & 统计分析
└─ 论文更新决策
```

---

## Updated Phase 3: validated architecture 锁参验证

当前不再建议直接启动 6 行大矩阵。已有 BIMCV Path-C、3090 sweep 和 MIDRC pilot 表明：projection/anatomy loss 尚未稳定有效，最稳的信号是 conservative reliability-gated KD。

详细计划已放入：

```text
docs/VALIDATED_ARCHITECTURE_EXPERIMENT_PLAN.md
```

实际入口脚本：

```bash
bash src/ops/h800_midrc_locked_validation.sh
```

默认 4 行矩阵：

1. CT teacher
2. X-ray supervised
3. Plain CT logit KD
4. Reliability-gated KD：`confidence_gate_threshold=0.55`, `projected_attention_weight=0`

升级为 validated architecture 的最低门槛：

- held-out test split 上 3 个 seeds 均优于 supervised 和 plain KD；
- mean ΔBA 至少约 `+0.03`；
- macro-F1 同方向；
- specificity 不塌；
- 看 test 结果后不得再改阈值或 projection 权重。

如果该门槛不过，论文继续保持 evidence-bounded negative-result 口径。

---

## Key Decision Point

**Question**: 在启动下一个步骤前，需要用户确认：

- [x] **A) 确认 MIDRC 559-case manifest 是正确的版本**
    - (不是 50、100、next50 的子集) 在 3090 上下载全量数据
  
- [x] **B) 允许 H800 继续存储 120-140 GB 数据**
    - (会占用 autodl-tmp 盘的空间) 请在 3090 上下载全量数据
  
- [x] **C) 允许在 Phase 2 后启动 GPU 训练**
    - 当前建议先跑锁参 4 行验证矩阵，而不是继续烧卡做 post-hoc 6 行大矩阵。

**如果所有选项均 ✓**: 可以立即进入 Phase 1

---

**Created**: 2026-05-11  
**Status**: 📋 Ready for locked validation after MIDRC download completes  
**Blocker**: ⏳ Awaiting complete MIDRC 559 download and final data audit
