# 进度

## 已全部修改

- **Bibliography pass 已完成（2026-05-14）**：`paper/ref.bib` 新增 9 条 2022–2025 BibTeX 条目（reliability-aware KD、audio-visual cross-modal KD、RGB-D disentanglement KD、mixture-of-teachers KD、calibration-balanced KD、recent medical-imaging KD）；`paper/main.tex` Related Work 新增 KD in Medical Imaging 与 Cross-Modal Distillation 两段引用扩展。

- **MIDRC-only 5-fold CV + BIMCV+MIDRC 混合 5-fold CV 均失败，teacher upper-bound 未建立（2026-05-14）**：三轮验证（MIDRC triage × 6 variants、MIDRC-only 5-fold ct_mean_projection/ct_3slice、BIMCV+MIDRC 混合 5-fold）全部未通过稳定 teacher 上界门槛。MIDRC-only 失败根因是 fold1 supervised 崩溃产生假正信号；混合 5-fold 失败根因是 BIMCV DRR（模拟投影）与 MIDRC ct_mean_projection（真实 CT 投影）存在跨域差，supervised X-ray 泛化更好。所有结果记录在 `src/results/` 各子目录，结论记录在 `docs/tmp/report513.md`。

- **3090 BIMCV-only same-source 4-row 5-fold CV 已完成并拉回（2026-05-14）**：3090 远端 `10.147.20.176` 已完成 BIMCV-only balanced patient-level 5-fold CV，矩阵为 teacher_drr、xray_supervised、plain_kd、gated_kd_thr055_proj0000 × 5 folds × 3 seeds，共 `60/60` runs，`60/60` test_eval。结果已拉回 `src/results/bimcv_only_5fold_cv_3090_20260514/`，并已追加到 `docs/tmp/report513.md`。核心结果：teacher_drr mean BA `0.6403` 明显高于 X-ray supervised `0.5657`（paired ΔBA `+0.0746`，95% CI `[+0.0314,+0.1144]`，12/15 positive）；plain KD 低于 supervised（ΔBA `-0.0290`）；gated KD 高于 plain KD（ΔBA `+0.0435`，95% CI `[+0.0052,+0.0858]`），但对 supervised 仅 `+0.0146` 且 CI `[-0.0264,+0.0531]` 跨 0。因此 same-source DRR teacher upper-bound 与 gating-rescue 信号成立，但 GAP-KD 仍未达到 validated architecture 门槛。
- **3090 Path C 结果已回填论文**：BIMCV 512-patient balanced-validation re-split 未把 CT logit KD 推过显著性门槛；当前口径保持 evidence-bounded，不升级为 validated architecture。
- **3090 completed GAP-KD follow-up on BIMCV Path-C**：同一 balanced-validation Path-C split 上的 12 个新 follow-up runs（seed 43--45；X-ray supervised、plain CT logit KD、confidence-gated KD、confidence-gated projection/anatomy KD）已全部完成。三 seed 汇总 balanced accuracy 分别为 `0.587 ± 0.025`、`0.619 ± 0.025`、`0.605 ± 0.019`、`0.615 ± 0.015`；这说明 same-cohort exploratory evidence 已存在，但仍属 post-hoc same-cohort follow-up，不能上调为 decisive validation 或 validated architecture。
- **Path C 数值结果已迁移**：3090 拉回的数值结果已从 `docs/tmp/3090_pathc/` 转移到 `src/results/bimcv_pathc_3090/`，避免继续把实验结果放在 `docs/tmp`。
- **实验计划已收口**：`docs/tmp/experiment_plan.md` 和 `docs/tmp/jdcnet_upgrade_plan.md` 已更新为“当前投稿不再追加同 cohort 微调实验；validated architecture 升级未成立；未来需要真正新增 paired cohort”。
- **两组评审意见已合并**：`docs/revision_suggestions.tex` 已整理为单一综合修改意见，重复项已合并，主线转向 evidence-bounded negative-result / protocol contribution。
- **本轮 manuscript narrative revision 已完成**：`paper/main.tex` 已把标题改为 evidence-bounded evaluation 叙事，压缩 abstract，强化 TCSVT visual-systems framing，更新 H1/H5 claim-status，重写 contributions，demote DPE/MHRA/DFPN 为 optional stress-test modules，并把 limitations/conclusion 改为“CT teacher feasible + cross-modal KD unvalidated”。
- **统计口径已降调**：主文已明确小样本 specificity 退化问题，主结果表已切换为 median (Q1,Q3) + 95% bootstrap CI；mean±SD 仅保留在 appendix extended descriptive table。
- **目标 venue 当前决策已消费**：按用户回答，当前继续按 TCSVT visual-systems / deployment-only inference framing 推进，但保留 scope risk 的文字降调。
- **Appendix 大表排版决策已消费**：按用户回答，BIMCV stress-test 大表压缩放到最终投稿排版阶段处理；当前仅记录 existing float-too-large warning，不作为本轮算法修改阻挡项。
- **GAP-KD/JDCNet-v2 代码框架已启动**：已新增 confidence-gated KD、projection-compatible attention loss、CPU synthetic smoke test 和 H800 no-card 启动脚本；本地 CPU smoke test 通过，结果在 `src/results/gapkd_cpu_smoke_local/smoke_gapkd.json`。
- **H800 无卡 smoke 实验已完成**：已把 GAP-KD/JDCNet-v2 最小代码同步到 H800，在无卡/CPU 环境运行 synthetic smoke test 并拉回结果；`src/results/h800_gapkd_cpu_smoke/smoke_gapkd.json` 显示 5/5 checks passed。
- **MIDRC balanced pilot 与短版证明框架已完成并拉回**：H800 有卡模式下已完成 MIDRC balanced pilot（126 cases，63 negative / 63 positive，train 44+44，val 19+19，errors=0）以及 3 seeds × 4 rows short-proof runs（CT teacher、X-ray supervised、plain CT KD、GAP-KD confidence-gated + projected attention）。结果已拉回 `src/results/midrc_short_proof_h800/`；H800 自动关机已临时取消，等待是否继续实验。
- **H800 MIDRC+BIMCV GAP-KD 参数筛选已完成并拉回**：H800 已完成 3 teachers + 33 student configs（supervised、plain KD、9 个 GAP-KD thr/proj 组合 × 3 seeds）。结果已归档到 `src/results/h800_midrc_bimcv_gapkd/`，远端 GPU 已空闲（0 MiB）。关机前检查显示 mixed manifest 为 187 rows，其中 MIDRC 126 rows（63/63 balanced）+ BIMCV 61 rows（主要为 positive），最终全局标签为 positive 124 / negative 63；因此该 sweep 是 mixed-cohort positive-enriched screen，而不是严格 1:1 balanced validation。该筛选没有找到 3 seeds 均稳定优于 supervised/plain KD 的 GAP-KD 配置，因此不能升级为 validated architecture。
- **论文已按 evidence-bounded negative 口径补入现有实验**：`paper/main.tex` 已把 3090 Path-C GAP-KD follow-up、27-run threshold/projection sweep 与 MIDRC short-proof pilot 解释为“实现已验证、机制已压力测试，但有效性未验证成功”；`paper/appendix.tex` 新增 BIMCV Path-C threshold/projection sweep 表和 MIDRC pilot 表，明确唯一稳定正向组合仅为弱 gating-only 信号（mean ΔBA 约 `+0.0095`），MIDRC seed 43 仍不稳定。
- **validated architecture 后续验证方案已落地到 docs 和代码**：新增 `docs/VALIDATED_ARCHITECTURE_EXPERIMENT_PLAN.md`，更新 `docs/MIDRC_AUDIT_CHECKLIST.md` 的 Phase 3，从 6 行 post-hoc 大矩阵改为锁参 4 行验证矩阵；代码新增 class-aware/margin/entropy reliability gate 字段、训练期 gate diagnostics，以及 `src/ops/h800_midrc_locked_validation.sh` 作为 MIDRC 559 下载完成后的实际执行入口。
- **2026-05-13 新一轮实验决策已记录**：`docs/tmp/report513.md` 已追加“teacher upper bound 优先 + 混合队列扩大验证规模”计划。核心决策为：先在 H800 无卡模式下生成 BIMCV+MIDRC 可控比例 index/manifest，用 BIMCV 补阳性、MIDRC 补阴性扩大可支撑 test size；随后优先修复 CT teacher upper bound，再运行 KD。若 CT teacher 不能稳定超过 X-ray supervised，则停止 KD 主实验，继续修 teacher。
- **H800 无卡混合 CV index 与 teacher-variant 预处理已完成**：已新增并同步 `src/jdcnet_exp/prepare_mixed_bimcv_midrc_cv.py` 和 `src/jdcnet_exp/prepare_midrc_teacher_variants.py` 到 H800。远端已生成 existing-path 版本 5-fold patient-level mixed index：`/root/autodl-tmp/mixed/midrc_bimcv_cv_existing_20260513/`，本地摘要拉回 `src/results/h800_mixed_cv_nocard_20260513/`。当前可训练 patient-level index 为 147 patients（63 negative / 84 positive；MIDRC 63 positive + 63 negative，H800 当前仅有 21 个 BIMCV positive patient 的 X-ray 路径可用，BIMCV negative X-ray 不可用），5-fold 每折 test 约 28--31 patients，所有 image/teacher paths 检查为 0 missing。MIDRC teacher upper-bound 预处理也完成：3-slice、5-slice、9-slice、multi-window、mean projection、MIP 共 6 类 CT teacher 变体，每类 126 patients，errors=0。
- **MIDRC 559 下载已在 3090 完成（2026-05-14）**：`/data1/midrc/raw_559cases_combined` 已达到 manifest 对应的 `1118/1118` zip files，大小约 `138G`（`137.19 GiB`），0 zero-byte、0 partial/tmp/incomplete 文件；最新进度表 `/data1/logs/midrc/midrc_559_progress.tsv` 稳定记录 `1118  1118  138G  0  0`。自动重启下载的 `/tmp/midrc_auto_watch.sh` 已停止，避免继续反复启动 `gen3-client --skip-completed`；仅保留只读进度 watcher。
- **3090 Git 工作目录与 MIDRC teacher upper-bound 已启动（2026-05-14）**：3090 已新建干净 clone `/data/JDCNET_git`，remote 为 `https://github.com/mabo1215/JDCNET.git`，当前 `main@6360db7`；`src/data`、`src/runs`、`src/results` 已软链接到旧 `/data/JDCNET/src/` 的数据/结果目录，MIDRC metadata 与 raw root 已通过链接或环境变量可用。3090 缺失 DICOM JPEG Lossless 解码插件的问题已通过用户级 `pylibjpeg` 依赖修复。`/data1/midrc/locked_validation` paired manifest 已生成完成，`/data1/midrc/teacher_variants_20260514` 的 6 类 CT teacher 输入变体均为 `126` patients、`errors=[]`。3090 teacher upper-bound 训练已启动：物理 GPU 2 跑 `ct_3slice_lung_rgb` teacher + X-ray supervised baseline，物理 GPU 3 已完成 `ct_5slice_lung_montage`、`ct_multiwindow_mid_rgb`、`ct_mean_projection_lung` teacher-only；剩余 `ct_9slice_lung_montage` 与 `ct_mip_lung` 排在 GPU2 lane 后续。
- **3090 teacher upper-bound triage 已完成并自动汇总（2026-05-14）**：6 类 CT teacher variants 均已完成 3 seeds teacher-only；`ct_3slice_lung_rgb` 同时完成 X-ray supervised baseline。远端汇总文件已写到 `/data1/logs/midrc_teacher_upper_bound_3090/teacher_upper_bound_comparison.md` 和 `.csv`。当前最好的是 `ct_mean_projection_lung`，mean test BA `0.5333`、mean AUC `0.5100`，相对同 seed X-ray supervised mean delta 约 `+0.0500`，但仅 `2/3` seeds 为正；因此 teacher upper-bound 仍未达到稳定门槛，暂不启动 KD。
- **3090 性能探测已后台启动（2026-05-14）**：远端新增 `/data1/midrc/tools/midrc_3090_perf_probe.py` 与 `/data1/midrc/tools/run_midrc_3090_perf_probe.sh`，用于记录 3090 上 MIDRC teacher 训练的 batch size / worker 可用上限。当前在空闲物理 GPU 2/3 后台运行，batch 从 `1024` 开始降档，workers 从 `64` 开始降档（未按 400 workers 直接启动，因为该机器约 40 CPU threads，400 workers 会导致进程和磁盘 I/O 抖动而非提升吞吐）。结果会写入 `/data1/logs/midrc_3090_perf/perf_probe_gpu*.csv` 和 `perf_probe_gpu*_best.json`。
- **H800 teacher variant image count 已验证**：`/root/autodl-tmp/midrc/teacher_variants_20260513/images/` 下共 6 个子目录，每个子目录恰好 126 files，与 processed_patients 字段吻合，errors=[]，预处理完整。
- **构建检查已完成**：已运行 `paper/build.bat`，`paper/main.pdf` 和 `paper/appendix.pdf` 均生成成功；剩余为既有排版/LaTeX warnings（如 appendix 大表 float too large、standalone appendix labels/bib warning），无 fatal error。
- **3090 性能探测已完成（2026-05-14）**：GPU2/3 均测出 batch=1024/workers=64 最快（合成数据），但真实 MIDRC 训练 batch=32/workers=8 是合理选择（85 train 样本 × BS=32 = 3 batch/epoch）。实际单 run 耗时约 50s（30 epochs）；GPU VRAM 仅占 ~1GB/24GB，这是小数据集固有限制，靠 4 卡并行弥补。
- **3090 MIDRC 5-fold patient-level CV 已启动（2026-05-14）**：将 126 patients 生成 5-fold stratified split（FOLD_SEED=99），每 fold test ≈ 25-26 例（原来 10/10），train ≈ 85，val ≈ 15-16。manifest 路径：`/data1/midrc/5fold_cv_20260514/`，日志：`/data1/logs/midrc_5fold_cv_3090/`。实验矩阵：`ct_mean_projection_lung` teacher + `xray_supervised` × 5 fold × 6 seeds（42-47）= 60 runs，全部 4 张 GPU 并行（round-robin），预计 ~12 min 完成。目标：通过 out-of-fold 聚合 126 例 test 预测，稳定估计 teacher vs supervised 的 BA/AUC delta，消除单次 10/10 test 的采样方差。
- **3090 MIDRC 5-fold CV Batch1+Batch2 已完成，两者均 FAIL（2026-05-14）**：
  - Batch1（ct_mean_projection_lung，MIDRC 126pts）：fold1 teacher 大幅领先（+0.211，6/6 pos），但 fold0/3/4 显著落后（-0.045/-0.111/-0.091），总计 12/30 pos，mean_delta=-0.009 → **FAIL**。
  - Batch2（ct_3slice_lung_rgb，MIDRC 126pts）：同样 fold1 领先（+0.135），其余 fold 均为负（fold0=-0.103，fold2=-0.081，fold3=-0.076，fold4=-0.008），10/30 pos，mean_delta=-0.027 → **FAIL**。
  - **根因**：fold1 supervised 模型崩溃（4/6 seeds 预测单类，BA≈0.50-0.54）。根本原因是训练数据过少：85 train × BS=32 × 30 epochs = 仅 ~78 次梯度更新，模型在 fold1 以随机初始化概率崩溃。并非 teacher 真实超越 supervised 的信号。
  - **数据限制**：MIDRC 全量 559 patients 中仅 69 COVID+（已用 63），无法在 MIDRC 内扩充。
- **3090 BIMCV+MIDRC 混合 5-fold CV 已完成，teacher 仍 FAIL（2026-05-14）**：将 MIDRC 126 + BIMCV 226 = 352 patients（176+/176-），每 fold train≈208-216，test≈68-72。全部 60 runs 完成，rc=0。
  - fold0: teacher=0.618  sup=0.725  delta=**-0.107**  (0/6 pos)
  - fold1: teacher=0.664  sup=0.623  delta=**+0.042**  (4/6 pos)
  - fold2: teacher=0.639  sup=0.688  delta=**-0.049**  (0/6 pos)
  - fold3: teacher=0.669  sup=0.635  delta=**+0.034**  (4/6 pos)
  - fold4: teacher=0.654  sup=0.677  delta=**-0.022**  (1/6 pos)
  - **总计：9/30 pos，mean_delta=-0.020，95% bootstrap CI=[-0.043, +0.002] → FAIL**
  - Teacher mean AUC=0.653 < Supervised mean AUC=0.686
  - fold0 supervised 模型是真实强（BA=0.724，recall/spec 均合理），非崩溃；teacher 在 fold0 真实弱（BA=0.618）。
  - **根因**：BIMCV DRR（模拟 CT 投影，西班牙医院）与 MIDRC ct_mean_projection（真实 CT 投影，美国医院）存在域差，teacher 无法跨域泛化；supervised Xray 模型域迁移能力更好。
  - **结论**：三轮实验（MIDRC-only batch1/batch2 + BIMCV+MIDRC 混合）均 FAIL，CT teacher upper-bound 未通过验证。不启动 KD 实验。paper 继续 evidence-bounded negative-result framing。数据记录在 `/data1/midrc/runs/midrc_mixed_5fold_cv_3090/`，日志 `/data1/logs/midrc_mixed_5fold_cv_3090/`。

## 已全部修改（续）

- **Priority 2 Calibration Scan 已完成，无 winner cell，选择路径 B（2026-05-15）**：T × threshold 8-cell 扫描（120 runs × BIMCV-only 5-fold × 3 seeds）全部完成（120/120 test_eval done，21:34 UTC）。所有 8 格 ΔBA vs supervised 的 95% CI 均跨 0，没有通过 ΔBA≥+0.03 且 CI lower>0 的 validated gate。最接近的是 T=4.0, thr=0.50（mean ΔBA=+0.034，CI [-0.0039, +0.0727]，9/15 pos）。决策：选择路径 B——直接切换到 evidence-bounded 写作模式，不再新增实验。结果文件：`docs/tmp/calibration_scan_decision_report.md`，`docs/tmp/calibration_scan_cell_summary.csv`。

## 已全部修改（续2）

- **2026-05-16 Fixed unresolved same-patient table reference**：Fixed the appendix sentence that rendered as `Tables ??-2` by replacing the missing `tab:problem_scope` reference with explicit references to `tab:dataset_protocol` and `tab:evaluation_regimes`. Rebuilt `paper/main.pdf` and `paper/appendix.pdf`; PDF text now reads `Tables 1 and 2`, with no remaining `??` instance for this phrase.

- **2026-05-16 Fixed Methodology whitespace around Section 3.4**：Removed the abnormal vertical gap between the DPE/MHRA/DFPN acronym paragraph and Section 3.4 by moving the full-width baseline evidence-map float later in `paper/main.tex`. Rebuilt `paper/main.pdf` and verified that Section 3.4 now follows the acronym paragraph normally.

- **2026-05-15 3090 C1+C2 完成并拉回**：C1 CT variants 240/240 完成；C2 BiomedCLIP fine-tune 15/15 完成。结论：C1 gated KD 未通过门，proj teacher 本身显著强于 supervised；C2 与同 split ResNet18 supervised 平手。结果在 `src/results/` 对应目录，计划在 `docs/tmp/report515.md`。

- **2026-05-16 Stage A 510-patient BIMCV 扩容实验完成（240/240 runs），决策：转向 definitive negative result**：在 510-patient（113+/397-）同患者配对 cohort 上运行 4 teacher × 4 method × 5-fold × 3 seed，全部完成。关键结论：
  - Teacher upper bound 通过门：`mid` ΔBA +0.045 [+0.019,+0.069] **PASS**，`3slice` ΔBA +0.051 [+0.025,+0.080] **PASS**——CT 确实承载可用病患信息，reviewer M9 批评已实证回答。
  - Gated KD vs supervised：4 个 teacher 全部 FAIL；DRR gated KD catastrophic collapse（ΔBA -0.064，CI [-0.095,-0.034]）。
  - 226-patient 时的"near-pass"（+0.034）在 510 时变成系统性负值，确认为小样本 artifact。
  - **决策**：不触发 Stage B（MIDRC 559）/ Stage C（X-ray pretrain）；转为"definitive negative at 4.5× cohort scale"写作框架。
  - 结果在 `src/results/bimcv_full_paired_cv_3090_20260516/`；计划与分析在 `docs/tmp/report515.md` §7。

## 进行中（需要跟进）

（当前无运行中的实验）

## 遗留问题（需要作者决策）

### 待完成：Paper 修改（Stage A 结果写入论文）—— 最高优先级

根据 `docs/tmp/report515.md` §7.6 的规划，需要对论文做以下修改：

1. **`paper/main.tex` §IV.A Datasets**：Table 1 新增一行 `Extended BIMCV paired (510 patients, 113+/397-)`。
2. **`paper/main.tex` §IV.C Primary Same-Case Evidence**：新增"4.5× cohort scaling test"段落，给出 teacher_vs_supervised PASS（mid +0.045, 3slice +0.051）与 gated_vs_supervised FAIL（all 4 variants negative，DRR -0.064 collapse）。
3. **`paper/main.tex` §III Contributions bullet 2**：升级为"Definitive negative result at 4.5× cohort scale"，完整新文见 `docs/tmp/report515.md` §7.6。
4. **`paper/main.tex` §IV.E Limitations**：新增 1 句关于 510-patient extension 与 open question。
5. **`paper/appendix.tex`**：新增 `Stage A: 510-Patient Extended Paired Cohort CV` 节，含 16 行 decision delta 表。
6. **Cover letter**：reviewer (iii) 回应段新增 510-patient 扩容说明，见 `docs/tmp/report515.md` §7.6 完整文字。
7. 重新 build PDF 验证无 fatal error。

### 待完成：LaTeX 表格 caption 整理（次要优先级）

- `paper/appendix.tex` Table 21 / `tab:ct_variants`：caption 内 BA / Delta BA / gate / dash/bold 的说明文字需压缩，避免 float-too-large warning。
- `paper/appendix.tex` `tab:bimcv_512_stress_test`：caption 与 `Interpretation` 段需整理，和 appendix 其余节风格一致。
- 上述整理完后重建 `paper/main.pdf` 验证。
