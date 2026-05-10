# 进度日志

## 2026-05-10 Execution E（DRR 几何锚点）完成 + 论文回填（11:10 UTC）

### Execution E 结果：最大 Δ，但仍未达 p<0.05

**Fixed-val BA（4 seeds 均值±标准差）：**
| 方法 | Fixed-val BA | Δ vs sup |
|---|---|---|
| DRR-KD（logit） | 0.709 ± 0.008 | +0.017 |
| DRR-KD+AT | 0.706 ± 0.018 | +0.014 |
| DRR-KD+AT+Proto† | 0.630 ± 0.014 | −0.062 |

†DataLoader 死锁，训练在 ep 4-7 截断（best.pt 已保存，但未充分收敛）。

**重采样 Wilcoxon（n=40 paired observations，与 supervised 比较）：**
| 方法 | mean Δ | std | 双侧 p | 单侧 p |
|---|---|---|---|---|
| DRR-KD（logit） | **+0.043** | 0.185 | **0.291** | **0.145** |
| DRR-KD+AT | +0.009 | 0.209 | 0.304 | 0.152 |
| DRR-KD+AT+Proto† | −0.041 | — | 0.165 | 0.917 |

**关键比较：DRR-KD vs CT-KD（Execution C）**
- DRR-KD mean Δ vs supervised = +0.043（vs CT-KD +0.025），提升 +0.018
- DRR-KD two-sided p = 0.291（vs CT-KD p = 0.668），大幅改善
- DRR-KD vs CT-KD 配对测试：mean Δ = +0.017，22 胜 / 6 平 / 12 负，p=0.116（单侧）

**结论：** DRR 几何锚点是迄今最强的转移信号，但 p=0.291 仍未越过 0.05 门槛。瓶颈已从"机制不足"转移到"验证集方差过大"（σ≈0.22，由 80 neg / 23 pos 验证集规模决定）。

### 角色级重采样均值（n=40 each，更新后全量）
| 角色 | mean BA | std |
|---|---|---|
| CT teacher | 0.815 | 0.131 |
| DRR-KD (logit) | **0.734** | 0.221 |
| Proto-KD w=1.0 | 0.719 | 0.207 |
| Cross-modal logit KD | 0.717 | 0.199 |
| DRR-KD+AT | 0.700 | 0.229 |
| Proto-KD w=2.0 | 0.700 | 0.227 |
| X-ray supervised | 0.691 | 0.223 |
| Proto-KD w=0.5 | 0.675 | 0.244 |
| DRR-KD+AT+Proto† | 0.650 | 0.226 |

### Wave 执行时间线
- Wave 1 (logit_kd): 05:10–07:38 UTC（2h28m，30 epochs × 4 seeds × GPU 时间分片）
- Wave 2 (at_kd): 07:38–10:06 UTC（2h28m）
- Wave 3 (at_proto_kd): 10:06–10:52 UTC（46m，因 DataLoader 死锁在 ep9 截断，手动 kill 触发 orchestrator 继续）
- Resample eval (GPU2): 10:52–11:10 UTC（18m）

### 论文回填（paper/appendix.tex + paper/main.tex）
- Section intro：从 "four configurations" 改为 "five configurations"，新增 Execution E 描述
- 表格 caption：更新说明 Execution E + 截断标注
- 新增三行 Execution E 数据行（DRR-KD / DRR-KD+AT / DRR-KD+AT+Proto†）
- 新增 Execution E 解释段落（Δ=+0.043，p=0.291，方差瓶颈分析）
- Minimum Next Experiment 段：从 "three levers failed" 到 "four levers exhausted"，指向更大配对队列 + DRR 锚点
- main.tex H1 行：新增 DRR-KD Δ=+0.043，p=0.291
- main.tex Limitations/Conclusion：更新 Execution E 叙述 + 方差瓶颈诊断

---

## 2026-05-10 Tier-B-lite 原型权重扫描完成 + 论文回填

### 总体结论
- **Tier-B-lite 原型蒸馏（prototype distillation only）三个权重值的扫描已全部完成**，所有结果均未达到与 supervised 相比的统计显著性 (p<0.05)。
- 论文升级为 "validated architecture" 的目标在当前证据下**无法达成**；论文继续保持 "evidence-bounded" 框架，但负面证据集变得显著更厚实。
- 已完成 `paper/main.tex` 与 `paper/appendix.tex` 的回填（Execution D 行 + Limitations + Conclusion 全部更新）。

### Wave 1/2/3 完整结果（4 seeds × 10 resamples = n=40 paired observations）

| 配置 | 固定 val BA | 重采样 Δ vs sup | 双侧 p | 单侧 p |
|---|---|---|---|---|
| 普通 logit KD | 0.698 ± 0.018 | +0.025 | 0.668 | 0.334 |
| Proto-KD w=0.5 | 0.693 ± 0.013 | −0.017 | 0.743 | 0.628 |
| Proto-KD w=1.0 | 0.692 ± 0.008 | **+0.028** | 0.360 | **0.180** |
| Proto-KD w=2.0† | 0.668 ± 0.028 | +0.008 | 0.963 | 0.481 |

†w=2.0 在 epoch 20/50 因 DataLoader worker 死锁挂起，best.pt 已保存。

**关键的权重单调性测试**（PROTO_W1 vs PROTO_W05, n=40）：
- mean Δ = +0.045, 中位数 = 0.000, 16 胜 / 15 平 / 9 负
- 双侧 p = 0.118, **单侧 p = 0.059**
- 符合 "更宽的特征对齐通道在方向上有效" 的假设，但效应量不足以越过 0.05 显著性阈值。

### 角色级重采样均值（n=40 each）
| 角色 | mean BA | std |
|---|---|---|
| CT teacher | 0.815 | 0.131 |
| Cross-modal logit KD | 0.717 | 0.199 |
| Proto-KD w=1.0 | **0.719** | 0.207 |
| Proto-KD w=2.0 | 0.700 | 0.227 |
| X-ray supervised | 0.691 | 0.223 |
| Proto-KD w=0.5 | 0.675 | 0.244 |

CT teacher 仍然是绝对最强的（0.815），但 student 端任何方法（KD / Proto KD）都未能在统计上显著超过 supervised 0.691。

### Wave 3 故障与处理
- 启动时间：2026-05-09 22:57 UTC，4 张 GPU 同时运行 4 个 seed
- 所有 4 个进程在 epoch 20/50 之后停止打 log（约 2026-05-10 00:37 UTC），但进程仍 alive，GPU sm=1%
- 推断：典型的 PyTorch DataLoader worker 死锁
- 处理：手动 kill 4 个 PID（660850/661015/661161/661325），best.pt 已保存
- Orchestrator 在 60 秒内检测到 tier_b 进程归零，触发 resample eval（00:42 UTC）
- 2026-05-10 00:52 UTC AUTOPILOT_DONE 写入

### 论文回填
**`paper/appendix.tex`：**
- Section 5 BIMCV stress test 引言：从 "three configurations" 改为 "four configurations"，新增对 Execution D 的总结
- `tab:bimcv_512_stress_test`：新增三行 D (ResNet-18, n=4) Prototype-KD w=0.5/1.0/2.0
- caption 扩展：说明 D 是 C 的延伸，标注 w=2.0† 截断
- Interpretation 段：新增 Execution D 段落，给出完整 Wilcoxon 数据 + 权重单调性 (p=0.059) + 全配置 (KD + 三个 proto 权重) 全部 p≥0.18 的总结
- Minimum Next Experiment 段：从 "two natural levers" 改为 "three natural levers"，新增 prototype 失败 → DRR 几何锚点是下一个杠杆

**`paper/main.tex`：**
- `tab:hypothesis_status` H1 行：新增原型扫描总结 (Δ∈[-0.017,+0.028], 无 p<0.05) + 单调性 p=0.059
- Limitations Data 段：新增 Execution D 失败 + 单调性信号 + 重新表述瓶颈定位
- Conclusion 段：扩展为 "stress-test series"，列出 plain KD + prototype 三权重均未显著，将 next evidence layer 重定向到 DRR 解剖锚点 + 更大配对队列

### 基础设施状态
- R3090 现在空闲：4 张 GPU 全部 idle，screen `660837.tier_b_orchestrator` 已在 00:52 UTC 自动终止
- 所有 24 个 best.pt 仍在 `/data/JDCNET/src/runs/bimcv_phase1_diag/`
- `/data/logs/phase1_autopilot/AUTOPILOT_DONE`、`resampling_summary.csv`、`resampling_wilcoxon.txt` 均存在
- Windows Task Scheduler `JDCNETR3090Poll` 仍在每小时拉取（不会再触发 FINAL_SUMMARY 写入因为已经写过）

### 回答用户问题：当前训练能否达到论文修改目标
**不能。** 三个层级的证据全部已收集，结论清晰：
1. **更大队列**（512 患者，A/B 执行）单独不足以恢复 KD 优势
2. **更强 backbone**（ResNet-18，Execution C）将 supervised 抬升 +0.10，但 KD 仍与 supervised 持平
3. **更宽蒸馏通道**（Execution D 三个 proto 权重）也未达到显著性

下一个决定性实验只能是 **DRR 几何锚点 + 多切片 teacher** 或者 **更大配对队列**（详见更新后的 `docs/tmp/jdcnet_upgrade_plan.md`）。

### 同日（2026-05-10 01:18+ UTC）启动 Tier-B Full 实验
- DRR 生成脚本完成：`/data/JDCNET/src/jdcnet_exp/build_drr.py`，使用 nibabel 平行投影（沿 AP 轴线积分，HU 截断到 [-1000, 400]，归一化输出 224×224 PNG）
- 视觉验证（`docs/tmp/drr_smoke/bimcv_S04529.png`）：肺部、肋骨、心影、横膈膜结构清晰，符合 X-ray 视觉规律
- 全 512 患者 DRR 缓存生成中：`/data/bimcv/drr_cache/`（仅 1 患者缺 NIfTI，被自动过滤）
- 16 个新配置文件（4 DRR teacher + 12 学生：3 变体 × 4 seeds）已生成于 `configs/bimcv_headline/`
- 学生配置使用 `paired_image_column="drr_path"`：teacher 输入 DRR，学生输入真 X-ray
- 因 DRR 与 X-ray 同坐标系，**复用现有 `attention_transfer_loss`** 即可作为几何锚点（无需新 loss）
- Tier-B Full orchestrator 序列化执行：
  - Wave T (DRR teachers, 50 epochs): 完成于 02:15 UTC，**Mean BA = 0.752 ± 0.042**（s44 = 0.801 最高），**+0.06 vs CT teacher** (0.715)，确认 DRR 含有比 CT 单切片更强的诊断信号
  - Wave 1: tier_b_full_logit_kd（DRR teacher + 普通 logit KD）
  - Wave 2: tier_b_full_at_kd（DRR teacher + AT，几何锚点）
  - Wave 3: tier_b_full_at_proto_kd（DRR teacher + AT + Proto w=1.0，kitchen sink）
  - 全部完成后自动触发 resample eval，写入 `AUTOPILOT_DONE_TIER_B_FULL`
- `phase1_resample_eval.py` 已升级以识别 4 个新角色名 + 增加 FULL_LOGIT_KD / FULL_AT_KD / FULL_AT_PROTO_KD vs sup/KD/PROTO_W1 的 Wilcoxon 比较
- **2026-05-10 04:41 UTC**: Wave 1 在 epoch 2/50 时被 kill 重启，因为 50 epoch × 5 min/epoch × 3 waves = 12h 太长。配置改为 30 epochs（Tier-B-lite 数据显示最佳 BA 在 ep 17-20，30 充分覆盖），新 orchestrator screen `879488.tier_b_full_resume`，预计 ~12:30 UTC 完成全部 3 wave + eval（~8 小时）
- **决策规则**: 任一变体 p<0.05 vs sup → H1 "Supported" → 论文升级为 validated architecture


## 2026-05-09 Paper-facing BIMCV wording update

- Updated `paper/main.tex` and `paper/appendix.tex` to present the BIMCV 512-patient results conservatively.
- Main framing now states: BIMCV supports CT-teacher feasibility, but cross-modal KD remains unstable and is not used to strengthen the main transfer claim.
- Added appendix subsection `BIMCV 512-Patient Paired Stress Test` with a 6-row table comparing two independent executions over CT teacher, X-ray supervised, and cross-modal logit KD.
- The table keeps the two executions separate rather than averaging them into a single headline number, because cross-modal KD collapses to zero sensitivity in one execution.
- Updated Data/Evaluation limitations to avoid claiming strong external validation or clinical readiness.
- Ran `paper/build.bat`; main and appendix PDFs were generated. Existing LaTeX warnings remain, but no fatal compilation error occurred.


## 2026-05-09 H800 completed: 512-patient comparison and shutdown pre-check

- **H800 full 512-patient run completed.**
  - Final H800 status: `9/9` jobs completed.
  - Final completion timestamp: `2026-05-09T06:10:35+08:00` for `bimcv_h800_xray_cross_modal_kd_s44`.
  - H800 summary: `/root/autodl-tmp/logs/bimcv_h800_headline/best_metrics_summary.csv`.
  - Integrity counts: `best_metrics.json=9`, `history.csv=9`, `START=9`, `DONE=9`.
  - H800 GPU idle: memory `0 / 81559 MiB`, utilization `0%`.
  - No active `jdcnet_exp.train` or `run_bimcv_h800_headline` process remains.

- **H800 artifacts preserved locally before shutdown.**
  - Local archive: `docs/tmp/h800_bimcv_headline_artifacts_20260509_0610CST.tgz`.
  - SHA256: `a00e21c0517c203bba8be5b88008acb2720aac980edd0f135588c81daac9c7a0`.
  - Archive includes H800 headline logs, run outputs, configs, and BIMCV CSV manifests.

- **H800 vs R3090 aggregate comparison files generated.**
  - `docs/tmp/h800_bimcv_512_best_metrics_summary.csv`
  - `docs/tmp/r3090_bimcv_512_best_metrics_summary.csv`
  - `docs/tmp/bimcv_512_h800_vs_r3090_per_seed.csv`
  - `docs/tmp/bimcv_512_h800_vs_r3090_aggregate.csv`

| Host | Method | n | Balanced accuracy mean ? std | ROC-AUC mean ? std | Recall mean | Specificity mean |
|---|---|---:|---:|---:|---:|---:|
| H800 | CT teacher | 3 | 0.6858 ? 0.0552 | 0.6705 ? 0.0389 | 0.5918 | 0.7797 |
| H800 | X-ray supervised | 3 | 0.5512 ? 0.0537 | 0.6162 ? 0.0347 | 0.3197 | 0.7826 |
| H800 | Cross-modal KD | 3 | 0.4826 ? 0.0075 | 0.5882 ? 0.0411 | 0.0000 | 0.9652 |
| R3090 | CT teacher | 3 | 0.6960 ? 0.0283 | 0.6819 ? 0.0477 | 0.7007 | 0.6913 |
| R3090 | X-ray supervised | 3 | 0.5973 ? 0.0133 | 0.6111 ? 0.0113 | 0.7279 | 0.4667 |
| R3090 | Cross-modal KD | 3 | 0.5991 ? 0.0215 | 0.6344 ? 0.0060 | 0.6054 | 0.5928 |

- **Current interpretation.**
  - CT teacher is consistent across hosts and remains the strongest overall arm at about `0.69` mean balanced accuracy.
  - R3090 X-ray supervised and R3090 cross-modal KD are close around `0.60` mean balanced accuracy.
  - H800 cross-modal KD collapsed with mean recall `0.0000`; this should be treated as an instability warning rather than evidence of positive transfer.
  - Because H800/R3090 manifests have matching patient/label/split hashes, the host discrepancy is not due to sample-support mismatch.

- **Remaining H800 tasks.**
  - No more H800 GPU training is required for the current BIMCV 512-patient batch.
  - Optional only: copy the local artifact archive to another persistent remote if a second backup is desired.
  - The shutdown watcher is still running but will not auto-shutdown because `runner.log` lacks `runner_done`; watcher logs show `best=9`, `history=9`, `summary_rows=9`, `runner_done=0`.
  - From the JDCNET/BIMCV perspective H800 is safe to shut down after user confirmation, provided no unrelated screen session is needed.

- **Paper backfill status.**
  - Still pending. Do not blindly backfill all BIMCV numbers.
  - Recommended paper-facing use: report BIMCV 512-patient as an additional evidence layer emphasizing CT-teacher feasibility and cross-modal KD instability, not as a strong positive transfer claim.


## 2026-05-09 R3090 512-patient BIMCV and B2Drop audit closure

- **R3090 now has complete path-valid 512-patient BIMCV training inputs.**
  - Manifest: `/data/JDCNET/src/data/bimcv/bimcv_merged_paired_manifest.csv`.
  - `1251 rows / 512 patients`.
  - Patient labels: negative `398`, positive `114`.
  - Split labels: train `318 neg / 91 pos`; val `80 neg / 23 pos`.
  - Path audit: missing `image_path` = `0`; missing `teacher_image_path` = `0`.
  - Current R3090 state: all four RTX 3090 GPUs idle; job pool `RUNNING_PID=none`, `QUEUE_LENGTH=0`.

- **R3090 completed the new full 512-patient engineering/headline batch.**
  - Run directory: `/data/JDCNET/src/runs/r3090_bimcv_512/`.
  - Log/summary directory: `/data/logs/r3090_bimcv_512/`.
  - Scheduler: `2026-05-08T19:45:15+00:00 DONE all all summary_written`.
  - Completed `9/9`: CT teacher, X-ray supervised, and cross-modal KD for seeds `42/43/44`.
  - Summary file: `/data/logs/r3090_bimcv_512/best_metrics_summary.csv`.

| Experiment | Balanced accuracy | ROC-AUC | Note |
|---|---:|---:|---|
| `r3090_bimcv_512_teacher_ct_s43` | 0.7269 | 0.7353 | full 512-patient R3090 manifest |
| `r3090_bimcv_512_teacher_ct_s44` | 0.6898 | 0.6668 | full 512-patient R3090 manifest |
| `r3090_bimcv_512_teacher_ct_s42` | 0.6713 | 0.6437 | full 512-patient R3090 manifest |
| `r3090_bimcv_512_xray_cross_modal_kd_s43` | 0.6158 | 0.6311 | full 512-patient R3090 manifest |
| `r3090_bimcv_512_xray_cross_modal_kd_s44` | 0.6067 | 0.6308 | full 512-patient R3090 manifest |
| `r3090_bimcv_512_xray_cross_modal_kd_s42` | 0.5748 | 0.6413 | full 512-patient R3090 manifest |
| `r3090_bimcv_512_xray_supervised_s43` | 0.6056 | 0.5988 | full 512-patient R3090 manifest |
| `r3090_bimcv_512_xray_supervised_s44` | 0.6043 | 0.6136 | full 512-patient R3090 manifest |
| `r3090_bimcv_512_xray_supervised_s42` | 0.5819 | 0.6209 | full 512-patient R3090 manifest |

- **H800/R3090 manifest alignment check.**
  - Both hosts have the same support: `1251 rows / 512 patients`, negative `398` / positive `114`, and identical train/val label counts.
  - Normalized patient/label/split hash matches: `6b660a6c145be39a9148268a20f9b184dd762f65f4a8455ebf4007f9b7bf8175`.
  - Normalized patient/label/split/finding/view/offset hash matches: `b15ccdd6a8ae6f96937ec30cedc41229f18b0ec88af627472d88ff37ddeff483`.
  - Full path hash differs only because the two machines use different absolute path roots.
  - H800 was still running the final job at the 2026-05-09 05:43 CST check: `bimcv_h800_xray_cross_modal_kd_s44`, epoch `44/50`; no H800 `best_metrics_summary.csv` yet.

- **B2Drop/WebDAV audit download completed on R3090.**
  - Audit root: `/data/bimcv_b2drop_audit/`.
  - Inventory: `/data/bimcv_b2drop_audit/audit_inventory.tsv` and `/data/bimcv_b2drop_audit/audit_inventory.json`.
  - Downloaded/verified `106` logical items (`108` files including inventory outputs), about `13 MB`.
  - Positive share `BIMCV-COVID19`: README plus `35` `.tar-tvf.txt` manifests.
  - Negative share `BIMCV-COVID19-cIter_1_2-Negative`: `67` manifest/readme-style files plus three small auxiliary archives:
    - `covid19_neg_derivative.tar.gz`, `1,787,838` bytes, SHA256 `957f3afe5e036f3f5048ca401b71904c9031d80c875723773d4e5aa7c0a626f0`.
    - `covid19_neg_metadata.tar.gz`, `36,753` bytes, SHA256 `cf5ed63297fcbbdf8ddc1f948923daa9d60e11d07075f17c6a3323e4c8b78834`.
    - `covid19_neg_sessions_tsv.tar.gz`, `1,349,377` bytes, SHA256 `bd9794027c47e01274ef6369b20a65f60897bd06fb530d871eb4ffdc7c984fc3`.
  - Full original subject archives were not downloaded: positive archives are about `70 GB`, negative archives are about `304 GB`, while R3090 `/data` is about `93%` used with only about `255 GB` free.

- **Manuscript backfill decision.**
  - The old R3090 `481-patient` results still must not be backfilled into manuscript headline tables.
  - The new R3090 `512-patient` results are valid candidate evidence, but remain **pending paper backfill** until the H800 full run finishes, H800/R3090 summaries are compared under the same manifest/split/config assumptions, and a paper-facing seed aggregation table is generated.


## 2026-05-08 远端收口复核（当前有效状态）

### 2026-05-08 H800 全量 BIMCV headline 训练已启动

- H800 有卡模式已确认：`nvidia-smi` 可见 1 张 NVIDIA H800 PCIe，PyTorch `cuda_available=True`。
- 已在 H800 创建并启动后台 screen：`1264.bimcv_h800_headline`。
- 远端 runner：`/root/autodl-tmp/run_bimcv_h800_headline.sh`。
- 日志目录：`/root/autodl-tmp/logs/bimcv_h800_headline/`。
- 结果目录：`/root/autodl-tmp/runs/bimcv_h800_headline/`。
- 配置目录：`/root/autodl-tmp/JDCNET/src/configs/bimcv_h800_headline/`。
- 训练计划：3 个 seed（42/43/44），每个 seed 顺序执行 `CT teacher -> X-ray supervised -> cross-modal KD`，共 9 个 50-epoch 任务；每一步独立日志、`history.csv`、`best_metrics.json`。
- 首个任务 `bimcv_h800_teacher_ct_s42` 已开始并完成 epoch 1 日志输出，说明 CUDA、全量 manifest、CT slice 路径和训练写盘链路已打通。
- 当前监控文件：
  - `/root/autodl-tmp/logs/bimcv_h800_headline/status.tsv`
  - `/root/autodl-tmp/logs/bimcv_h800_headline/bimcv_h800_teacher_ct_s42.log`
  - `/root/autodl-tmp/logs/bimcv_h800_headline/best_metrics_summary.csv`（所有任务完成后生成）

### 2026-05-08 R3090 数据源直连补齐尝试已启动

- R3090 当前已有 `POS=113`、`NEG=368/398`，无下载进程，`/data` 约 `260G` 可用。
- 已创建并启动 screen：`3490822.r3090_bimcv_direct_neg`。
- 远端脚本：`/data/JDCNET/src/ops/r3090_bimcv_direct_neg_resume.sh`。
- 日志目录：`/data/logs/r3090_bimcv_direct_neg/`。
- 当前状态：第 1 次 direct-source negative 下载尝试已启动；已成功进入 B2Drop WebDAV archive manifest 枚举阶段，说明 3090 当前能读到数据源目录；subject 计数暂未增长，仍为 `368/398`，需等进入 archive 下载/解包阶段后继续观察。
- 监控文件：
  - `/data/logs/r3090_bimcv_direct_neg/status.tsv`
  - `/data/logs/r3090_bimcv_direct_neg/download.log`
  - `/data/logs/r3090_bimcv_direct_neg/runner.log`

### R3090 (`10.147.20.176`)

- 当前无训练进程；四张 RTX 3090 均空闲（`nvidia-smi` 显存约 1 MB/卡）。
- `job_pool` 当前空闲：`RUNNING_PID=none`，`QUEUE_LENGTH=0`。
- 已完成的 BIMCV headline 训练批次：`s45/s46/s47` 的 X-ray supervised、CT teacher、cross-modal KD 均已跑到 50 epoch 并写出 `best_metrics.json`。
- 当前可用 best 结果摘要（旧 3090 merged manifest：1182 rows / 481 patients；negative=368、positive=113）：
  - `bimcv_xray_cross_modal_kd_s47`: balanced_accuracy `0.6809`, roc_auc `0.7297`
  - `bimcv_xray_cross_modal_kd_s45`: balanced_accuracy `0.6606`, roc_auc `0.7006`
  - `bimcv_xray_cross_modal_kd_s46`: balanced_accuracy `0.6442`, roc_auc `0.7100`
  - `bimcv_xray_supervised_s47`: balanced_accuracy `0.6305`
  - `bimcv_xray_supervised_s46`: balanced_accuracy `0.6185`
  - `bimcv_xray_supervised_s45`: balanced_accuracy `0.6104`
- 论文回填判断：这些结果可作为远端训练完成记录和下一轮统计输入，但**暂不建议直接回填论文 headline tables**，因为它们基于 3090 旧 merged manifest（481 patients），不是 H800 刚完成的全量 merged manifest（512 patients）。

### H800 (`connect.westc.seetacloud.com:12437`)

- 当前无 positive/negative 下载、manifest、gate 或训练相关进程残留。
- BIMCV positive 直连数据源下载完成：本地目录统计 `114` subjects；下载报告目标 `113` subjects。
- BIMCV negative 下载完成：`398/398` subjects。
- 已生成 H800 全量 merged manifest：`1251 rows / 512 patients`，其中 positive `266 rows / 114 patients`，negative `985 rows / 398 patients`。
- readiness gate 已通过：`decision=START_TRAINING`，`ready_for_training=true`。
- 磁盘状态：`/root/autodl-tmp` 约 `100G total / 71G used / 30G avail`。

### 当前结论与下一步

- 已完成并可清理：H800 negative/positive 下载、manifest、merged readiness gate；3090 s45-s47 训练批次；旧的“下载未完成 / 进程运行中 / FIFO 分叉”阻塞项。
- 3090 仍需要完成的任务：把 H800 全量 merged manifest 与必要切片/数据同步或在 H800 直接开训，然后基于同一份 `512-patient` merged manifest 重新跑论文可用的 headline integration（至少 supervised、CT teacher、cross-modal KD；最好按多 seed / resampling 口径汇总）。
- 论文能否回填：当前可以回填“BIMCV 数据准备与 readiness 已完成”的进度与附录资源状态；不能把 3090 旧 manifest 上的 s45-s47 best metrics 直接写入主文 headline tables，除非明确标注为旧数据快照/工程验证。

## 历史快照（保留审计，不作为当前待办）

## 2026-05-07 21:43 UTC 全量远端进度检查快照

### R3090 (`10.147.20.176`) 四卡训练实时状态

| GPU | Config | Status | Epoch | Elapsed | Memory | PID |
|-----|--------|--------|-------|---------|--------|-----|
| GPU0 | bimcv_xray_supervised_s42 | **RUNNING** | - | 56:42 | 1945 MB | 2932822 |
| GPU1 | bimcv_teacher_ct_s42 | **COMPLETED** | 50/50 ✓ | - | 1 MB | (finished) |
| GPU2 | bimcv_xray_cross_modal_kd_s42 | **RUNNING** | 11/50 | 52:41 | 2045 MB | 2956136 |
| GPU3 | bimcv_xray_supervised_s43 | **RUNNING** | 11/50 | 52:38 | 1945 MB | 2956560 |

- **GPU1 完成情况**：已跑完 50 epoch，最终 epoch=50 metrics：`loss=0.3945, acc=0.5979, f1=0.5801, auc=0.7268`。目前在加载最优检查点阶段。
- **GPU0/2/3 进度**：GPU0 已运行 56 分钟（推进中），GPU2/3 约 52-53 分钟，均在有序推进。
- **日志确认**：
  - GPU1: 52 行输出（完整 50 epoch）
  - GPU2: 13 行输出（正在 epoch 11）
  - GPU3: 11 行输出（正在 epoch 11）

### H800 (`connect.westc.seetacloud.com:12437`) 下载进度突破 97.5%

| 指标 | 数值 | 进度 |
|------|------|------|
| **负样本对数** | 388/398 | **97.5%** ✓ 大幅提升 |
| **下载进程** | PID 920 | **运行中** |
| **监控进程** | PID 1173 | **运行中** |
| **磁盘容量** | 56G / 45G avail | 56% 使用 |
| **当前任务** | covid19_neg_subjects_partdb.tar.gz | 正在解包 |

- **距离完成**：仅剩 10 subjects（进度从 380→388，在短时间内跳跃了 8 个）。
- **下载日志末尾**：
  ```
  Downloading covid19_neg_subjects_partcy.tar.gz (8 new paired subjects) ...
    Download complete (5,012,451,877 bytes). Extracting ...
    Extracted 8 subjects.
  
  Downloading covid19_neg_subjects_partdb.tar.gz (2 new paired subjects) ...
  ```
- **磁盘充足**：45G 可用空间，足以完成剩余 10 subjects（预计需 5-10GB）。

### 本轮结论

1. **四卡并行进展超预期**：GPU1 已完成首个 50-epoch 任务，GPU0/2/3 均稳定推进中，无进程崩溃或卡死迹象。
2. **H800 负样本采集激进突破**：从 380/398 → 388/398，仅差 10 subjects，预计几小时内达成 398/398 目标。
3. **系统健康度**：
   - R3090: 4 卡分配均衡，无冲突；GPU 内存均在 2GB 以内，显存充足。
   - H800: 下载+监控进程均活跃，磁盘余量充足，下载队列持续推进（无卡死）。
4. **后续优先级**：
   - **紧急**：观察 H800 是否能在 24 小时内到达 398/398（触发自动 manifest + readiness gate）。
   - **常规**：监控 GPU1 后续流程（是否需要触发下一个任务入队）；GPU0/2/3 继续推进。

## 2026-05-07 本地+远端同步复核（与 progress_BIMCV_May5-6 对齐）

- 本地工作区：
  - `docs/progress_BIMCV_May5-6.md` 已有本轮更新（May 7 状态段）。
  - `docs/progress.md` 正在同步追加本条总日志，保持两份文档一致。
- R3090（`10.147.20.176`）实时状态：
  - `bimcv_paired`（positive）=`113/113`（100%）。
  - `bimcv_neg_paired`（negative）=`368/398`（92.5%）。
  - 训练进程在线：`python3 -m jdcnet_exp.train --config configs/bimcv_headline/bimcv_xray_supervised_s42.json`（PID `2886056`）。
  - FIFO 状态：`/data/JDCNET/src/ops/job_pool/job_pool_status.sh` 显示 `RUNNING_PID=none`、`QUEUE_LENGTH=0`；历史日志中可见 `bimcv_xray_cross_modal_kd_s42` 已跑到 50 epoch。
- H800（`connect.westc.seetacloud.com:12437`）实时状态：
  - `bimcv_neg_paired`（negative）=`380/398`（95.5%）。
  - 下载进程在线：`python3 -u -m jdcnet_exp.download_bimcv_neg_paired ... --share-token BIMCV-COVID19-cIter_1_2-Negative`（PID `920`）。
  - 磁盘：`/root/autodl-tmp` 约 `100G total / 58G used / 43G avail`。
  - 最新日志仍在推进（已进入 `covid19_neg_subjects_partct.tar.gz` 解包阶段）。
- 本轮结论：
  - 数据侧：H800 下载持续推进，3090 positive 已满、negative 高比例完成。
  - 训练侧：3090 当前有 active 训练进程；FIFO 队列为空，后续任务需按需重新入队。
  - 文档侧：本条已与 `docs/progress_BIMCV_May5-6.md` 的 May 7 状态保持同步。

## 2026-05-07 3090 单进程 + FIFO 强一致化收口

- 执行动作（R3090）：
  - 重置 `job_pool` 运行态文件：清空 `queue.txt`，删除 `running.pid`/`running.job`。
  - 重启统一 worker：`screen -S jdcnet_pool -X quit` 后重新 `screen -dmS jdcnet_pool /data/JDCNET/src/ops/job_pool/job_pool_worker.sh`。
  - 仅通过统一入口入队 1 个训练任务：`/data/JDCNET/src/ops/job_pool/job_pool_enqueue.sh /data/JDCNET/src/ops/job_pool/tasks/task_bimcv_xray_supervised_s42.sh`。
- 收口后状态（已验证）：
  - `RUNNING_PID=2932812`
  - `RUNNING_JOB=/data/JDCNET/src/ops/job_pool/tasks/task_bimcv_xray_supervised_s42.sh`
  - `QUEUE_LENGTH=0`（worker 已取走唯一队首任务）
  - 活跃训练进程：`python3 -m jdcnet_exp.train --config configs/bimcv_headline/bimcv_xray_supervised_s42.json`（PID `2932822`）
  - worker screen 存在：`2931849.jdcnet_pool (Detached)`
- 结论：
  - 3090 已恢复到“单训练进程 + FIFO 单入口”的一致状态。
  - 后续新增任务必须仅使用 `ops/job_pool/job_pool_enqueue.sh` 入队，避免绕过池状态造成分叉。

## 2026-05-07 3090 四卡并行训练启动（GPU0 保持不动）

- 执行目标：保留 GPU0 当前任务不动，新增 GPU1/2/3 三条并行训练。
- 启动编排：
  - GPU0（保留原任务）：`bimcv_xray_supervised_s42.json`
  - GPU1（新增）：`bimcv_teacher_ct_s42.json`（日志：`/data/logs/bimcv_teacher_ct_s42_gpu1.log`）
  - GPU2（新增）：`bimcv_xray_cross_modal_kd_s42.json`（日志：`/data/logs/bimcv_xray_cross_modal_kd_s42_gpu2.log`）
  - GPU3（新增）：`bimcv_xray_supervised_s43.json`（日志：`/data/logs/bimcv_xray_supervised_s43_gpu3.log`）
- 启动后实时进程（已验证）：
  - `2932822` → `bimcv_xray_supervised_s42.json`（GPU0）
  - `2955838` → `bimcv_teacher_ct_s42.json`（GPU1）
  - `2956136` → `bimcv_xray_cross_modal_kd_s42.json`（GPU2）
  - `2956560` → `bimcv_xray_supervised_s43.json`（GPU3）
- 启动后显存占用快照：
  - GPU0: ~1945 MiB
  - GPU1: ~1437 MiB
  - GPU2: ~2045 MiB
  - GPU3: ~1945 MiB
- 说明：
  - `bimcv_xray_supervised_s43.json` 已使用独立 `experiment_name/output_dir`，避免覆盖 GPU0 的 `s42` 产物。

一键健康检查命令（R3090）：

```powershell
plink -ssh -batch -hostkey "ssh-ed25519 255 SHA256:Jj7AizwqBqF1buL3ZBUiE5P37N9XXvel+rxwrYIPty0" -l mabo1215 -pw "***" 10.147.20.176 'echo HOST=R3090; echo GPU; nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits; echo TRAIN; pgrep -af "bimcv_xray_supervised_s42.json|bimcv_teacher_ct_s42.json|bimcv_xray_cross_modal_kd_s42.json|bimcv_xray_supervised_s43.json" || echo TRAIN_NOT_RUNNING; echo LOG_TAIL_gpu1; tail -n 5 /data/logs/bimcv_teacher_ct_s42_gpu1.log 2>/dev/null || echo NO_LOG; echo LOG_TAIL_gpu2; tail -n 5 /data/logs/bimcv_xray_cross_modal_kd_s42_gpu2.log 2>/dev/null || echo NO_LOG; echo LOG_TAIL_gpu3; tail -n 5 /data/logs/bimcv_xray_supervised_s43_gpu3.log 2>/dev/null || echo NO_LOG'
```

## 2026-05-06 本机关机前远端依赖复核

- 结论：本地机器可以关机；当前 3090 与 H800 任务均已在远端后台独立运行，不依赖本地终端或本地 SSH 会话。
- 3090：
  - 远端时间：`2026-05-06T12:28:07+00:00`。
  - `jdcnet_pool` screen worker 仍在运行；当前 FIFO job 为 `/data/JDCNET/src/ops/job_pool/tasks/task_bimcv_xray_supervised_s42.sh`。
  - 当前 job PID `2950603`，训练进程 PID `2950612`，队列剩余 2 个任务：`task_bimcv_teacher_ct_s42.sh`、`task_bimcv_xray_cross_modal_kd_s42.sh`。
  - 当前 best metrics 文件：`runs/bimcv_headline/bimcv_xray_supervised_s42/best_metrics.json`；最新 best epoch `29`，`balanced_accuracy=0.6270`，`roc_auc=0.6731`，`pr_auc=0.3362`。
  - `history.csv` 尚未出现，说明该 50-epoch run 尚未正常收尾。
- H800：
  - 远端时间：`2026-05-06T20:28:00+08:00`。
  - watchdog 进程 PID `1173`，下载进程 PID `920`，均在远端后台运行。
  - 当前 BIMCV negative count `323/398`；日志已确认 `398 unique subjects`，正在继续处理 `covid19_neg_subjects_partab.tar.gz`。
  - `/root/autodl-tmp` 当前约 `100G` total / `46G` used / `55G` available，磁盘余量充足。
- 本地工作区关机前注意：
  - 本地尚有未提交记录文件：`docs/progress.md`、`docs/progress_BIMCV_May5-6.md`。
  - 新增本地脚本：`ops/h800_resume_bimcv_neg_pipeline.sh`；已同步到 H800 `/root/autodl-tmp/h800_resume_bimcv_neg_pipeline.sh`。
  - 若换机器继续，需要同步/提交上述本地文件；若只是在本机之后开机继续，则无需额外操作。
- 开机后优先检查：
  - 3090：`cd /data/JDCNET/src && ops/job_pool/job_pool_status.sh`，再查 `runs/bimcv_headline/*/best_metrics.json` 与 `history.csv`。
  - H800：`pgrep -af 'h800_resume_bimcv_neg_pipeline|download_bimcv_neg_paired'`，`tail -80 /root/autodl-tmp/logs_neg.log`，`tail -80 /root/autodl-tmp/h800_bimcv_neg_pipeline.log`，并统计 `sub-S*` 是否到 `398/398`。
  - H800 若下载完成：确认 `data/bimcv/bimcv_neg_manifest.csv` 与 `results/bimcv_neg_readiness_gate.json` 是否已由 watchdog 生成。

## 2026-05-06 H800 扩容后已恢复下载

- H800 已重启并扩容完成；`/root/autodl-tmp` 从 `50G` 扩到 `100G`，当前约 `45G` used / `56G` available，使用率约 `45%`。
- 已恢复 BIMCV negative 下载，显式使用 share token `BIMCV-COVID19-cIter_1_2-Negative`，继续写入原目录 `/root/autodl-tmp/bimcv_neg_paired`。
- 当前下载进程：`PID 920`，命令为 `python3 -u -m jdcnet_exp.download_bimcv_neg_paired --output-dir /root/autodl-tmp/bimcv_neg_paired --share-token BIMCV-COVID19-cIter_1_2-Negative`。
- 当前 watchdog 进程：`PID 1173`，脚本为 `/root/autodl-tmp/h800_resume_bimcv_neg_pipeline.sh`；本地版本记录在 `ops/h800_resume_bimcv_neg_pipeline.sh`。
- watchdog 行为：若下载进程仍在运行则等待；若下载异常退出且未达 `398/398`，最多自动重启 20 次；达到 `398/398` 后自动运行：
  - `prepare_bimcv_neg_dataset --bimcv-root /root/autodl-tmp/bimcv_neg_paired --output-dir /root/autodl-tmp/JDCNET/src/data/bimcv --slice-dir /root/autodl-tmp/bimcv_neg_ct_slices`
  - `data_readiness_gate --manifest /root/autodl-tmp/JDCNET/src/data/bimcv/bimcv_neg_manifest.csv --dataset-name bimcv_negative_only`
- 最新日志显示已枚举出 `63 archive(s)`、`398 unique subjects`，并开始继续下载 `covid19_neg_subjects_partab.tar.gz`；当前 subject count 仍为 `323/398`，预计需等后续 archive 解包后继续上涨。
- 后续检查：
  - `pgrep -af 'download_bimcv_neg_paired|h800_resume_bimcv_neg_pipeline'`
  - `tail -80 /root/autodl-tmp/logs_neg.log`
  - `tail -80 /root/autodl-tmp/h800_bimcv_neg_pipeline.log`
  - `find /root/autodl-tmp/bimcv_neg_paired -maxdepth 1 -type d -name 'sub-S*' | wc -l`

## 2026-05-06 H800 下载已暂停（扩容前）

- 已按用户要求暂停 H800 上的 BIMCV negative 下载，便于临时关机扩容。
- 远端时间记录：`2026-05-06T20:17:15+08:00`。
- 已确认无 `python3`、`wget`、`curl`、`aria2c` 下载相关进程残留。
- 当前 BIMCV negative 已落地 subject 数：`323/398`。
- 日志文件：`/root/autodl-tmp/logs_neg.log`，暂停前大小 `56997` bytes，mtime `2026-05-06 17:57:58 +0800`。
- 磁盘状态：`/root/autodl-tmp` 为 `50G`，已用 `45G`，可用 `5.3G`，使用率 `90%`。
- 扩容后恢复前先检查：
  - `find /root/autodl-tmp/bimcv_neg_paired -maxdepth 1 -type d -name 'sub-S*' | wc -l`
  - `df -h /root/autodl-tmp`
  - `tail -40 /root/autodl-tmp/logs_neg.log`
- 恢复下载时沿用 `download_bimcv_neg_paired --output-dir /root/autodl-tmp/bimcv_neg_paired`；脚本会跳过已存在文件。

## 2026-05-06 3090 训练结果复核

- 3090 上的 `bimcv_neg_teacher_xray_main` 已完成 10 epoch，但配置使用的是 `data/bimcv/bimcv_neg_manifest.csv`，训练/验证均为 label=0 的负例数据。
- 该 run 的验证集混淆矩阵为 `[[188, 0], [0, 0]]`，`roc_auc=NaN`，`pr_auc=0.0`，accuracy/balanced accuracy/macro-F1=1.0 仅表示模型学会了全预测负例；不能作为有效 BIMCV 正负分类结果。
- 结论：不应在该 run 上继续增加 epoch。继续训练只会强化单类塌缩，不能带来论文可用效果。
- 3090 已具备正确合并数据：`data/bimcv/bimcv_merged_paired_manifest.csv`，共 1182 rows / 481 patients；train 为 732 neg + 211 pos，val 为 188 neg + 51 pos。
- 下一步应新建并运行基于合并 manifest 的 BIMCV headline integration 配置，例如 X-ray supervised baseline、CT teacher、cross-modal distillation student；优先用 50 epoch 或沿用主实验口径，并启用 `use_weighted_sampler=true` 处理类别不均衡。
- 最新刷新：3090 四张 GPU 均空闲，未见训练进程；H800 BIMCV-neg 仍为 306/398，下载进程仍在但日志自 2026-05-06 14:58 CST 后未更新，需后续判断是否重启或清理磁盘后续跑。

## 2026-05-06 BIMCV headline 训练已启动（3090）

- 已将 `src/jdcnet_exp/train.py` 的 best checkpoint 选择从 `accuracy` 改为优先 `balanced_accuracy`，避免 BIMCV 类别不均衡时选择偏负例的 checkpoint。
- 已新增本地辅助脚本 `ops/create_bimcv_headline_remote.py`，并同步到 3090 的 `/data/JDCNET/src/ops/create_bimcv_headline_remote.py`；该脚本可重复生成 BIMCV headline manifest/config/task。
- 3090 端已生成：
  - `data/bimcv/bimcv_teacher_ct_manifest.csv`
  - `data/bimcv/bimcv_same_modality_manifest.csv`
  - `configs/bimcv_headline/bimcv_xray_supervised_s42.json`
  - `configs/bimcv_headline/bimcv_teacher_ct_s42.json`
  - `configs/bimcv_headline/bimcv_xray_cross_modal_kd_s42.json`
- FIFO 已按依赖顺序入队并启动：
  1. `task_bimcv_xray_supervised_s42.sh`（正在运行，PID 2950603；训练进程 PID 2950612）
  2. `task_bimcv_teacher_ct_s42.sh`
  3. `task_bimcv_xray_cross_modal_kd_s42.sh`
- 训练日志：
  - `/data/logs/bimcv_xray_supervised_s42.log`
  - `/data/logs/bimcv_teacher_ct_s42.log`
  - `/data/logs/bimcv_xray_cross_modal_kd_s42.log`
- 输出目录：
  - `/data/JDCNET/src/runs/bimcv_headline/bimcv_xray_supervised_s42`
  - `/data/JDCNET/src/runs/bimcv_headline/bimcv_teacher_ct_s42`
  - `/data/JDCNET/src/runs/bimcv_headline/bimcv_xray_cross_modal_kd_s42`
- 当前观察：第一项训练 CPU 使用约 222%，GPU0 显存约 1.9GB；日志可能因当前任务启动时 stdout 缓冲而延迟写出。已把后续两个排队 task 改为 `python3 -u` 与 `PYTHONUNBUFFERED=1`，便于开机后实时查看 epoch 输出。
- 开机后优先检查：
  - `/data/JDCNET/src/ops/job_pool/job_pool_status.sh`
  - `tail -80 /data/logs/bimcv_xray_supervised_s42.log`
  - `tail -80 /data/logs/bimcv_teacher_ct_s42.log`
  - `tail -80 /data/logs/bimcv_xray_cross_modal_kd_s42.log`
  - `find /data/JDCNET/src/runs/bimcv_headline -maxdepth 2 -name history.csv -o -name best_metrics.json`

## 2026-05-06 关机前交接（3090/H800）

> 本节仅保留未完成项，已完成项已从本节移除，便于明早直接续跑。

### 0) 3090 当前状态快照（关机前最后记录）

- 已确认：`prepare_bimcv_neg_dataset.py`、`prepare_bimcv_dataset.py`、`data.py`、`__init__.py` 已传到 `/data/JDCNET/src/jdcnet_exp/`。
- 已触发过一次后台任务（`NEG_PID=4109268`，`POS_PID=4109269`），但当时失败：
  - `prepare_bimcv_neg_dataset` 报 `ModuleNotFoundError: No module named 'pandas'`。
  - `download_bimcv_paired` 报 `ModuleNotFoundError: No module named 'jdcnet_exp'`（需设置 `PYTHONPATH=/data/JDCNET/src`）。
- 已再次触发“链式后台引导”（bootstrap），用于自动安装依赖后再启动两任务：
  - 记录到的 bootstrap pid：`4110210`、`4110214`。
  - 主日志：`/data/logs/start_bimcv_jobs_driver.log`、`/data/logs/bootstrap_bimcv.log`。
- 明早第一优先检查（先看链式引导是否完成）：
  - `sshpass -p 'mabo1215' ssh mabo1215@10.147.20.176 'tail -n 50 /data/logs/start_bimcv_jobs_driver.log 2>/dev/null; echo "---"; tail -n 50 /data/logs/bootstrap_bimcv.log 2>/dev/null'`
  - `sshpass -p 'mabo1215' ssh mabo1215@10.147.20.176 'pgrep -af "prepare_bimcv_neg_dataset|download_bimcv_paired|start_bimcv_jobs.sh"'`

### 一、3090 明早先检查（优先级最高）

- [ ] 确认关键脚本已到位：
  - `sshpass -p 'mabo1215' ssh mabo1215@10.147.20.176 'ls -l /data/JDCNET/src/jdcnet_exp/prepare_bimcv_neg_dataset.py /data/JDCNET/src/jdcnet_exp/prepare_bimcv_dataset.py'`
- [ ] 配置 Kaggle 凭据并检查权限：
  - `sshpass -p 'mabo1215' ssh mabo1215@10.147.20.176 'mkdir -p ~/.kaggle && echo '"'"'{"username":"mabo1215","key":"KGAT_736ec39e9254a69ff354954720b63e54"}'"'"' > ~/.kaggle/kaggle.json && chmod 600 ~/.kaggle/kaggle.json && ls -l ~/.kaggle/kaggle.json'`
- [ ] 以 `nohup` 启动负例 manifest 生成（断连后继续）：
  - `sshpass -p 'mabo1215' ssh mabo1215@10.147.20.176 'mkdir -p /data/logs /data/JDCNET/src/data/bimcv /data/bimcv_neg_ct_slices && cd /data/JDCNET/src && nohup python3 -m jdcnet_exp.prepare_bimcv_neg_dataset --bimcv-root /data/bimcv_neg_paired --output-dir /data/JDCNET/src/data/bimcv --slice-dir /data/bimcv_neg_ct_slices > /data/logs/prepare_neg_manifest.log 2>&1 & echo PID:$!'`
- [ ] 以 `nohup` 启动 BIMCV-COVID19+ 下载（断连后继续）：
  - `sshpass -p 'mabo1215' ssh mabo1215@10.147.20.176 'mkdir -p /data/bimcv_paired /data/logs && cd /data/JDCNET/src && nohup python3 -m jdcnet_exp.download_bimcv_paired --output-dir /data/bimcv_paired > /data/logs/bimcv_pos_download.log 2>&1 & echo PID:$!'`
- [ ] 检查两个后台任务日志是否持续更新：
  - `sshpass -p 'mabo1215' ssh mabo1215@10.147.20.176 'tail -n 20 /data/logs/prepare_neg_manifest.log; echo "---"; tail -n 20 /data/logs/bimcv_pos_download.log'`

### 二、H800 明早检查（并行）

- [ ] 查看 BIMCV-neg 下载是否仍在运行及进度：
  - `ssh h800 'ps -fp 1014; ls -d /root/autodl-tmp/bimcv_neg_paired/sub-* 2>/dev/null | wc -l'`
- [ ] 如进程已退出，读取最终报告：
  - `ssh h800 'cat /root/autodl-tmp/bimcv_neg_paired/download_report_neg.json 2>/dev/null || echo "report not ready"'`

## E3/E4 多种子对比表（2026-05-04）

E3 = ResNet18 ImageNet-pretrained linear-probe（paired cohort, 50 epochs）  
E4 = BiomedCLIP frozen-feature linear-probe（paired cohort, 50 epochs）  
验证集共 4 样本（1 neg / 3 pos），饱和信号下指标须谨慎解读。

### 逐 seed 明细

| 模型 | seed | Acc | Bal-Acc | Macro-F1 | MCC | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|---|---|---|---|---|
| E3 ResNet18 | 42 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.097 |
| E3 ResNet18 | 43 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.039 |
| E3 ResNet18 | 44 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.084 |
| E3 ResNet18 | 45 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.052 |
| E4 BiomedCLIP | 42 | 0.750 | 0.500 | 0.429 | 0.000 | 0.000 | 0.639 | 0.308 |
| E4 BiomedCLIP | 43 | 0.750 | 0.500 | 0.429 | 0.000 | 0.667 | 0.917 | 0.149 |
| E4 BiomedCLIP | 44 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.160 |
| E4 BiomedCLIP | 45 | 0.500 | 0.667 | 0.500 | 0.333 | 1.000 | 1.000 | 0.337 |

### 4-seed 均值汇总

| 模型 | Acc | Bal-Acc | Macro-F1 | MCC | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|---|---|---|---|
| E3 ResNet18 | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** | **0.068** |
| E4 BiomedCLIP | 0.750 | 0.667 | 0.589 | 0.333 | 0.667 | 0.889 | 0.239 |

**结论**：E3 ResNet18 在所有 4 个种子下完美收敛（验证集全正确预测）；E4 BiomedCLIP 冻结特征存在明显种子间方差（MCC 0–1.0），mean ROC-AUC=0.667 为弱正相关，总体低于 E3。小样本（n=4 val）导致方差极大，结论仅为方向性参考。

## 2026-05-04 工作区核对与继续推进

> 本节基于当前 Windows 工作区实测状态（`C:\source\JDCNET`）补充，优先保证“可执行性”而非“理想状态”。

### 已立即推进（今天已落地）

- 本小节已归档清理；仅在上方“关机前交接”保留未完成任务。

### 当前可继续推进（不依赖新训练）

- [ ] **资源可见性核对**：当前工作区未检索到 `paper/figs/generated/*.tex` 与 `paper/figs/*.png`，且 `paper/` 目录为空；先确认是否在另一分支/另一机器产出，必要时回传到当前仓库。
- [ ] **NLST dry-run 先行**：在拿到 TCIA/NBIA 首批目录后先跑 dry-run，先拿“可配对样本量”再决定训练预算。
- [ ] **BIMCV-neg 样本量门槛检查**：下载后先只生成 manifest 和 summary，达到最小阈值再开 10-resample 训练。

### 资源需求清单（按优先级）

1. **P0 数据访问凭据**
  - Kaggle API（用于 BIMCV-neg 下载）。
  - TCIA/NBIA 访问与下载权限（用于 NLST）。
2. **P0 存储与路径约定**
  - 推荐准备：`/data/bimcv_neg_paired`、`/data/nlst`、`src/data/bimcv`、`src/data/nlst`。
  - 需要可持续空间：原始 DICOM + 中间切片 + 训练产物。
3. **P1 计算资源**
  - H800/H100 级 GPU 窗口（E1/M2/M10 主体训练）。
  - CPU 即可完成 dry-run、manifest 构建、样本统计。
4. **P1 环境依赖**
  - Python 包：`pydicom`（已写入 requirements）、`kaggle`、`torch`、`fvcore`。

### 下一步执行顺序（建议直接照此推进）

1. 数据访问开通后先执行 BIMCV-neg 下载与 manifest 生成（只做数据侧，不开训练）。
2. 并行执行 NLST dry-run，拿到 paired CT+CXR 的真实可用规模。
3. 依据两条 summary 的样本量决定是否进入 E1/M10 训练窗口，并在本文件回填“可训练/不可训练”结论。

### 开训门槛（执行判定规则，2026-05-04 新增）

- 判定脚本：`python -m jdcnet_exp.data_readiness_gate`
- 默认门槛（可通过命令行覆盖）：
  - `min_total_patients = 50`
  - `min_pos_patients = 20`
  - `min_neg_patients = 20`
  - `min_val_neg_patients = 5`
  - `min_val_total_patients = 20`
  - `target_resamples = 10`（若设为 `>=30`，脚本会额外检查 negative 规模稳定性）
- 输出：`START_TRAINING` 或 `HOLD_DATA_EXPANSION`，并给出阻塞原因列表。

### H800 无GPU模式调试链路（先跑数据侧）

1. BIMCV-neg 下载与 manifest：
  - `python -m jdcnet_exp.download_bimcv_neg_paired --output-dir /data/bimcv_neg_paired`
  - `python -m jdcnet_exp.prepare_bimcv_neg_dataset --bimcv-root /data/bimcv_neg_paired --output-dir src/data/bimcv --merge-with src/data/bimcv/bimcv_paired_manifest.csv`
2. BIMCV 开训门槛判定：
  - `python -m jdcnet_exp.data_readiness_gate --manifest src/data/bimcv/bimcv_combined_manifest.csv --dataset-name bimcv_combined --output src/results/bimcv_readiness_gate.json`
3. NLST dry-run 与门槛判定：
  - `python -m jdcnet_exp.prepare_nlst_dataset --nlst-root /data/nlst --output-dir src/data/nlst --dry-run`
  - `python -m jdcnet_exp.data_readiness_gate --manifest src/data/nlst/nlst_paired_manifest.csv --dataset-name nlst_paired --output src/results/nlst_readiness_gate.json`

### 2026-05-04 远端继续推进（H800 无卡模式已开启）

- 状态确认：远端 H800 当前以无 GPU 任务模式运行，可继续执行数据下载、manifest 构建、dry-run、门槛判定与日志核对。
- 本轮目标：在不开训的前提下，先把 BIMCV-neg/NLST 两条数据链路跑通并产出可审计 summary。

#### A. 远端无卡调试最小闭环（按顺序）

1. 环境与脚本可执行性检查：
  - `cd /root/autodl-tmp/JDCNET/src`
  - `python -m jdcnet_exp.download_bimcv_neg_paired --help`
  - `python -m jdcnet_exp.prepare_bimcv_neg_dataset --help`
  - `python -m jdcnet_exp.prepare_nlst_dataset --help`
  - `python -m jdcnet_exp.data_readiness_gate --help`
2. BIMCV-neg 数据链路（仅数据侧）：
  - `python -m jdcnet_exp.download_bimcv_neg_paired --output-dir /data/bimcv_neg_paired`
  - `python -m jdcnet_exp.prepare_bimcv_neg_dataset --bimcv-root /data/bimcv_neg_paired --output-dir src/data/bimcv --merge-with src/data/bimcv/bimcv_paired_manifest.csv`
  - `python -m jdcnet_exp.data_readiness_gate --manifest src/data/bimcv/bimcv_combined_manifest.csv --dataset-name bimcv_combined --output src/results/bimcv_readiness_gate.json`
3. NLST 数据链路（先 dry-run）：
  - `python -m jdcnet_exp.prepare_nlst_dataset --nlst-root /data/nlst --output-dir src/data/nlst --dry-run`
  - `python -m jdcnet_exp.data_readiness_gate --manifest src/data/nlst/nlst_paired_manifest.csv --dataset-name nlst_paired --output src/results/nlst_readiness_gate.json`

#### B. 本轮完成判定（必须全部满足）

- `src/results/bimcv_readiness_gate.json` 已生成且可读。
- `src/results/nlst_readiness_gate.json` 已生成且可读。
- 两个 manifest 文件（BIMCV combined / NLST paired）均存在并可统计总样本、正负样本、val 负样本。
- 在本文件回填 gate 输出结论：`START_TRAINING` 或 `HOLD_DATA_EXPANSION`，并附阻塞原因。

#### C. 若遇到常见阻塞（无卡模式优先排障）

- Kaggle 认证失败：先校验 `~/.kaggle/kaggle.json` 权限，再重试下载。
- NLST 路径为空或结构不匹配：先执行 dry-run，只回传样本量估计与缺失字段。
- manifest 生成成功但 gate 未达标：保持 `HOLD_DATA_EXPANSION`，不进入任何训练任务。

#### D. 2026-05-04 连通性实测记录（本次会话）

- 已读取 `c:\source\.env` 的 H800 连接信息并尝试自动登录验证。
- 当前会话下（WSL + 本机网络栈）到 `connect.westb.seetacloud.com:39830` 的连通性表现为 timeout/failed，导致自动化 SSH 链路未完成。
- 结论：本轮阻塞属于网络连通层，不是仓库脚本缺失；`download_bimcv_neg_paired.py`、`prepare_bimcv_neg_dataset.py`、`prepare_nlst_dataset.py`、`data_readiness_gate.py` 均已在仓库内确认存在。

#### E. 你本机可立即执行的两步复核（通过即继续）

1. SSH 通道复核：
  - `ssh h800`
  - 或 `ssh -p 39830 root@connect.westb.seetacloud.com`
2. 进入项目后执行最小 help 自检：
  - `cd /root/autodl-tmp/JDCNET/src`
  - `python -m jdcnet_exp.download_bimcv_neg_paired --help`
  - `python -m jdcnet_exp.prepare_bimcv_neg_dataset --help`
  - `python -m jdcnet_exp.prepare_nlst_dataset --help`
  - `python -m jdcnet_exp.data_readiness_gate --help`

> 只要上述 help 自检通过，即可按本节 A/B 的无卡链路继续推进并产出 gate json。

## 2026-05-04 H800 无卡模式 dry-run 执行结果

### 执行环境确认

- H800 SSH：`connect.westc.seetacloud.com:12437`，`root@h800` alias 有效。
- Python：`/root/miniconda3/bin/python3.12`，torch 2.8.0+cu128 已安装。
- 项目路径：`/root/autodl-tmp/JDCNET/src/`，35 个 Python 脚本 rsync 完成（EXIT:0）。
- pip 依赖：`kaggle nibabel pydicom scipy` 安装成功（PIP_DONE PIP_EXIT:0）。
- PYTHONPATH：`/root/autodl-tmp/JDCNET/src`，四个核心模块 `--help` 全部通过（HELP_CHECK_OK）。

### BIMCV-neg dry-run 结果

- **状态：HOLD_DATA_EXPANSION — 数据集不存在**
- **根本原因**：`rafiko1/bimcv-covid19-neg-a-0`（以及 b/c/d-0）在 Kaggle 上根本不存在。
  - `kaggle datasets list -s "bimcv-covid19-neg"` → `No datasets found`
  - 错误类型：`403 Forbidden`（非认证失败）
  - Kaggle 认证本身正常（`bimcv-covid19` 正例臂 `rafiko1/bimcv-covid19-a/b/c/d-0` 可正常枚举）。
- **`download_bimcv_neg_paired.py` 中的数据集名称假设不正确。**
- **BIMCV-COVID19- 负例臂实际位置**：未在 Kaggle 发布，需从 BIMCV 官方门户或其他途径获取。
  - 官方参考：https://bimcv.cipf.es/bimcv-projects/bimcv-covid19/
- **阻塞项**：无法继续 E1/M2 BIMCV 集成，直到找到正确的负例数据集来源并修改脚本。
- **修复建议**：
  1. 在 BIMCV 官方门户确认 COVID19- 负例臂是否有 Kaggle 镜像（名称可能不同）。
  2. 或改用直接 BIMCV 官方下载（需注册）。
  3. 修改 `download_bimcv_neg_paired.py` 中的 `BIMCV_NEG_PARTS` 列表。

### NLST dry-run 结果

- **状态：HOLD_DATA_EXPANSION — 数据未下载**
- dry-run 完成（`NLST_DRYRUN_DONE`），`/data/nlst` 目录为空。
- 脚本输出：`WARN: Neither CSV manifests nor CT/CXR directories found under /data/nlst.`
- 符合预期：NLST 需从 TCIA/NBIA 先申请访问权限再下载；dry-run 只是验证脚本本身可运行。
- **下步**：在 TCIA 提交/确认 NLST 访问权限，配置 NBIA Data Retriever，完成首批下载后重新执行。

### Gate 判定

| 数据集 | 门槛状态 | 阻塞原因 |
|---|---|---|
| BIMCV-neg | `HOLD_DATA_EXPANSION` | Kaggle 数据集 `rafiko1/bimcv-covid19-neg-*` 不存在，数据未下载 |
| NLST | `HOLD_DATA_EXPANSION` | `/data/nlst` 为空，需 TCIA 申请 + NBIA 下载 |

**结论：两条数据链路均处于 HOLD_DATA_EXPANSION 状态，不进入任何训练任务。**

## 2026-05-04 B2Drop 修复 dry-run（第二轮）

### 背景

上轮阻塞：`download_bimcv_neg_paired.py` 使用 Kaggle API（`rafiko1/bimcv-covid19-neg-*`），数据集不存在（403 Forbidden）。用户提供正确下载链接：`https://b2drop.bsc.es/index.php/s/BIMCV-COVID19`（BSC B2Drop 公开分享）。

### 脚本重写

`src/jdcnet_exp/download_bimcv_neg_paired.py` 完整重写：
- **移除** Kaggle API 依赖（`KaggleApi`、`zipfile`、`shutil` 无必要导入）
- **改用** B2Drop WebDAV（PROPFIND 列目录）+ HTTP GET 下载 `.tar-tvf.txt` manifest 和 `.tar.gz` 档案
- **修复** manifest 下载 ZIP 包裹问题：`index.php/s/{token}/download?path=/&files=FILE` 会重定向到 `?accept=zip` 端点，响应为 ZIP 二进制，导致文本解析得 0 subjects；改用 WebDAV 直接 GET 返回纯文本
- **新增** 请求间隔（1s）和 429 自动重试（最多 3 次，退避 5/10/15s）
- **保留** 全部原有主体逻辑：subject regex、CT/CXR 检测、最大 CT 选择、`sub-S*/ct/cxr/` 目录结构、`--dry-run`、`--min-ct-bytes`、JSON 报告
- **新增** `--share-token`（默认 `BIMCV-COVID19`）和 `--archives`（按需子集下载）

### dry-run v2 执行结果（H800，screen dryrun3）

- **Share token**：`BIMCV-COVID19`
- **WebDAV 列目录**：35 个 `.tar.gz` 档案（`bimcv_covid19_posi_subjects_1–34.tgz` + `bimcv_covid19_posi_head_iter1.tgz`）
- **Manifest 解析**：WebDAV 直接 GET 正常，文本解析成功（每档约 33–40 subjects）
- **配对结果**：32 / 35 档案含配对主体，共 **113 个 unique paired subjects**（CT+CXR，`min_ct_bytes=1M`）
- 报告写入：`/data/bimcv_neg_paired/download_report_neg.json`，`EXIT:0`

### 重要发现：share 内容为 COVID-19 **阳性臂**

| 项 | 观察 |
|---|---|
| 档案命名 | 全部为 `bimcv_covid19_**posi**_subjects_*.tgz` |
| 期望 | BIMCV-COVID19- 阴性臂（`neg`，label=0 non-COVID） |
| 实际 | `BIMCV-COVID19` share = 阳性臂 iter1（COVID+ 患者，113 paired subjects） |
| 阳性臂迭代 1+2+3 | 另在 `BIMCV-COVID19-cIter_1_2_3` share（571 档案），更完整 |

**结论**：用户提供的 `BIMCV-COVID19` share 为 COVID-19 **阳性臂** iter1 而非阴性臂。

### 当前状态（更新）

| 数据集 | 状态 | 说明 |
|---|---|---|
| BIMCV-neg（label=0）| **HOLD** — share URL 有误 | 阴性臂 share token 未知，需用户确认 |
| BIMCV-posi iter1（label=1）| 可下载，113 subjects | `BIMCV-COVID19` share，脚本就绪 |
| NLST | HOLD — 数据未下载 | 需 TCIA/NBIA 访问 |

---

## 2026-05-04 B2Drop 阴性臂 dry-run（第三轮，正确 share）

### 背景

用户提供正确阴性臂 URL：`https://b2drop.bsc.es/index.php/s/BIMCV-COVID19-cIter_1_2-Negative`

通过 WebDAV PROPFIND 验证：该 share 含 64 个 subject archives（`covid19_neg_subjects_part*.tar.gz`）+ 3 个辅助 archives（derivative / metadata / sessions）。

### 脚本修复（两处）

`src/jdcnet_exp/download_bimcv_neg_paired.py` 做了两处更新：

1. **默认 share token** 从 `BIMCV-COVID19` 更新为 `BIMCV-COVID19-cIter_1_2-Negative`
2. **Manifest 文件名推导**：阴性臂 manifest 命名为 `archive.tar.gz.tar-tvf.txt`（双扩展名），而非阳性臂的 `archive.tgz → archive.tar-tvf.txt`；修复为 `archive_name + ".tar-tvf.txt"`
3. **`_enumerate_archives` 过滤**：新增 `_NON_SUBJECT_PREFIXES` 跳过 `covid19_neg_derivative` / `covid19_neg_metadata` / `covid19_neg_sessions` 等非主体档案

### dry-run v4 执行结果（H800，screen dryrun_neg4）

- **Share token**：`BIMCV-COVID19-cIter_1_2-Negative`
- **WebDAV 列目录**：64 个 subject archives（`covid19_neg_subjects_part{ab..dt}.tar.gz`）
- **Manifest 解析**：每档案 32–87 subjects，配对比例约 6–15%
- **配对结果**：63 / 64 档案含配对主体，共 **398 unique paired subjects**（CT+CXR，`min_ct_bytes=1M`）
- 报告写入：`/data/bimcv_neg_paired/download_report_neg.json`，`EXIT:0`

### 当前状态

| 数据集 | 状态 | 说明 |
|---|---|---|
| BIMCV-neg（label=0）| **READY** — dry-run 通过 | 398 paired subjects，可启动完整下载 |
| BIMCV-posi iter1（label=1）| 可下载，113 subjects | `BIMCV-COVID19` share，脚本就绪 |
| NLST | HOLD — 数据未下载 | 需 TCIA/NBIA 访问 |

### 下一步

1. **完整下载 BIMCV-neg**（不带 `--dry-run`），约 64 档案，估计数 GB 磁盘空间
2. 验证磁盘：`df -h /data`（当前约 40 GB 可用）
3. 运行 `prepare_bimcv_neg_dataset.py` 生成 manifest（label=0）
4. 运行 `data_readiness_gate.py` 评估两数据集合并后是否满足训练阈值

---

## 2026-05-04/05 BIMCV-neg prepare 脚本 OOM 修复（进行中）

### 背景与阶段总结

下载阶段（Option A，受 50 GB 磁盘限制，选 4 个档案）已完成：
- **23 subjects** 下载至 `/root/autodl-tmp/bimcv_neg_paired/sub-S*/`（ct + cxr 各一份）
- 档案示例：`partab, partae, partaf, partah`（共 4 个，约 3.5 GB）

`prepare_bimcv_neg_dataset.py` 反复 EXIT:137（OOM kill），根本原因为 H800 **cgroup 内存上限仅 2 GB**：

| 修复轮次 | 修改内容 | 结果 |
|---|---|---|
| v1（float32）| `get_fdata(dtype=np.float32)` 替换 float64 | 仍 EXIT:137 |
| v2（dataobj int16）| `np.asarray(canonical.dataobj)`，仅对 2D slab 转 float32 | 仍 EXIT:137 — 829 MB .nii.gz 解压后 ~2.5 GB int16 |
| **v3（streaming mmap）** | gzip 流式解压 → 临时 .nii（数据盘） + `nib.load(mmap=True)` 仅读5片 | **正在运行** |

### v3 技术方案

```python
# 1. 流式解压（1 MB chunks，不占 RAM）
with gzip.open(nii_path, "rb") as gz, open(tmp_nii, "wb") as out:
    shutil.copyfileobj(gz, out, length=1 << 20)

# 2. mmap 加载（只分页所需切片，~2.5 MB vs 2.5 GB）
img = nib.load(tmp_nii, mmap=True)
raw_slab = np.array(img.dataobj[slicer], dtype=np.float32)  # 仅 5 切片

# 3. 用完立即删除临时文件
tmp_path.unlink()
```

峰值内存预估：解压写盘（streaming，无 RAM 压力）+ mmap 5片（~5 MB）+ Python overhead ≪ 2 GB

### 当前 H800 执行状态（本地关机后继续）

| 项 | 值 |
|---|---|
| Screen session | `3455.prep_neg3`（H800 后台，SSH 断开不受影响） |
| 日志文件 | `/root/autodl-tmp/prep_neg.log` |
| 预计完成时间 | 23 subjects × ~30-60s/CT = 约 15-25 分钟 |
| 磁盘（数据盘）| `/root/autodl-tmp`：50 GB 总量，~36 GB 可用（解压后 .nii 临时文件用完即删） |

### 明日检查步骤

```bash
# 1. 快速查结果（推荐先用这条）
ssh h800 "cat /root/autodl-tmp/prep_neg.log; echo SLICES=$(ls /root/autodl-tmp/bimcv_neg_ct_slices/ 2>/dev/null | wc -l)"

# 2. 若 EXIT:0，运行 data_readiness_gate
ssh h800 "cd /root/autodl-tmp/JDCNET/src && \
  PYTHONPATH=/root/autodl-tmp/JDCNET/src \
  /root/miniconda3/bin/python -m jdcnet_exp.data_readiness_gate \
  --neg-manifest /root/autodl-tmp/JDCNET/src/data/bimcv/bimcv_neg_manifest.csv"

# 3. 若仍 EXIT:137，attach screen 查实时错误
ssh h800 "screen -r prep_neg3"
# Ctrl+A, D 退出不杀进程
```

### 期望成功输出

```
Scanning BIMCV-COVID19- root: /root/autodl-tmp/bimcv_neg_paired
BIMCV-COVID19- pairs found: {'rows': N, 'patients': 23, ...}
Wrote BIMCV-negative manifest: .../bimcv_neg_manifest.csv (23 rows)
EXIT:0
SLICES=23
```

### 后续（gate 通过后）

- `data_readiness_gate.py` 当前门槛：`min_neg=20`，23 subjects 预计可通过负例门槛
- 若输出 `START_TRAINING`：进入 E1 BIMCV headline integration 训练窗口
- 若 `HOLD_DATA_EXPANSION`：查阻塞原因（通常是 val 负例不足 `min_val_neg=5`）

### 2026-05-05 本轮复核结果（未能读取远端日志）

- **状态：等待远端认证恢复**。
- 本地尝试 `ssh -o BatchMode=yes -o ConnectTimeout=15 -p 12437 root@connect.westc.seetacloud.com`，远端返回 `Permission denied (publickey,password)`；说明 host/port 可达，但当前会话没有可用的非交互认证凭据。
- 本地尝试 `ssh -o BatchMode=yes -o ConnectTimeout=15 -p 39830 root@connect.westb.seetacloud.com`，连接被拒绝；该旧端口仍不可用。
- 因此本轮未能读取 `/root/autodl-tmp/prep_neg.log`、未能确认 `3455.prep_neg3` screen 状态，也未能运行 `data_readiness_gate.py`。
- 下步仍沿用上方检查命令：恢复 SSH alias/密钥或交互登录后，先读取 `prep_neg.log` 与 slice 数；若 manifest 已生成再运行 gate，若仍是 EXIT:137 则继续修 `prepare_bimcv_neg_dataset.py` 的内存路径。

## 未修改或部分修改

> 本节只保留当前仍需推进的事项；已完成的 BIMCV 512-patient 下载/manifest/gate、H800/R3090 训练、B2Drop 审计、paper-facing stress-test wording、Tier-B-lite 原型权重扫描与论文回填均不再列入本节。

### A. 写作/表述仍需收口

- **O2 threshold / calibration 叙事统一 — PARTIAL**：确认 threshold、calibration、Youden-J、prevalence-matched/argmax 相关表述是否已与最新 BIMCV stress-test 口径完全一致；一致后关闭。
- **O5 related-work 终检 — PARTIAL**：复核 reviewer 点名文献与 2022--2024 cross-modal medical distillation 讨论是否仍有缺口；补齐后关闭。

### B. 实验/资源仍需推进

- **M1 efficiency / TCSVT deployment evidence — PARTIAL**：CPU/MACs 已有；若投稿口径仍要求部署证据，需要补 GPU latency 或 edge/embedded latency 同口径测量。
- **M4 baseline coverage — PARTIAL**：确认 Gupta 2016 named baseline、MedCLIP/GLoRIA frozen-feature、CheXNet/ConvNeXt-Tiny same-modality teacher 中哪些仍未完成；只继续未覆盖子项。
- **M5 / E3 training-practice extensions — PARTIAL**：cosine LR + warmup、224×224、RadImageNet、10-resample 统计若未全部完成，继续作为扩展项；已由现有实验覆盖的子项下一轮关闭。
- **Next decisive experiment: DRR geometric anchor + multi-slice teacher — NOT DONE**：Tier-B-lite 未能支持强正向迁移结论；下一轮若继续争取 stronger claim，应转向 DRR 解剖/几何锚点与多切片 CT teacher。
- **M10 second independent thoracic dataset — NOT DONE**：NLST/MIDRC 等第二独立 thoracic dataset 仍未落地完整同协议结果。
- **E10 non-medical paired-modality demo — NOT DONE**：仍需新数据集、协议定义与训练窗口。

## 遗留问题

> 本节只记录需要作者决策、外部访问权限或新增资源的信息；不记录已完成的运行状态。

1. **第二独立 thoracic dataset 决策/访问**：是否继续以 NLST 为主线？若是，需要 TCIA/NBIA 访问、下载路径与最小样本量确认；若改用 MIDRC/其他数据源，需要作者确认。
2. **非医学 paired-modality demo 是否保留**：E10 是否仍作为本轮投稿前必须项，还是降级为 future work，需要作者决策。
3. **下一轮强证据实验路线**：在 Tier-B-lite 未显著后，是否启动 DRR geometric anchor + multi-slice teacher，或改为继续扩大 paired cohort，需要作者确定。
4. **M4/M5/E3 扩展实验收口口径**：请确认哪些 baseline/训练实践子项已经由现有实验覆盖，哪些仍需继续跑；确认后可把对应条目从“未修改或部分修改”移除。
