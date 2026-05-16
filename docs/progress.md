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

- **2026-05-16 Method 1 (Cross-Modal Contrastive Alignment) 已完成，全部 4 cells FAIL**：在 `docs/future_methods_plan.md` 计划的 Method 1 上，新增 `src/jdcnet_exp/train_contrastive.py`（两阶段：Stage 1 InfoNCE 对 paired (X-ray, CT) 预训练 ResNet-18 双编码器 + 投影头；Stage 2 weighted-CE 微调 X-ray 编码器 + 分类头），以及 `src/ops/remote_3090_bimcv_contrastive_cv.sh` 与 `remote_3090_bimcv_contrastive_summarize.sh`。3090 远端跑 60 runs（teachers={mid, 3slice} × temperatures={0.07, 0.20} × 5 folds × 3 seeds，GPU 2/3 并行 4 concurrent；约 28 min 完成 60/60，0 failures）。结果拉回 `src/results/bimcv_contrastive_cv_3090_20260516/`。所有 4 cells 均未通过 pre-specified gate（mean ΔBA ≥ +0.03 且 CI lower > 0）：最好的 cell 是 3slice tau=0.20，ΔBA=+0.008 [-0.020, +0.037]，7/15 positive。结论：feature-space contrastive alignment 在 510-patient 规模下未把 CT teacher upper-bound 信号转化为 X-ray 学生的可验证增益。

- **2026-05-17 方法两轮重命名：PL-XKD → CG-XKD → JDCNet**：根据用户两次决策连续重命名主方法：
  1. **第一轮 (PL-XKD → CG-XKD)**：用户担心"Pseudo-Label"潜在 reviewer 误读（中文"伪标签"似伪造、英文 pseudo 似不真实），改用 Confidence-Gated 机制描述符（已在被引文献 wu2023krd、amara2022bdkd 中确立）；同步 τ_pseudo → τ_gate，L_pseudo → L_aux。
  2. **第二轮 (CG-XKD → JDCNet)**：用户希望保留 JDCNet 作为论文方法的简短可引用名，便于后续论文引用"JDCNet"。所以：
     - 新标题：`JDCNet: A Confidence-Gated Cross-Modal Distillation Framework for CT-to-X-ray Classification`（Option B）
     - 主方法名：JDCNet（即论文要引用的简称）；CG-XKD 缩写被完全删除
     - "Confidence-Gated Cross-Modal Distillation" 留作方法描述短语
     - 旧"Full JDCNet"（指失败的模块增强变体 DPE/MHRA/DFPN）改为 "Module-Augmented Logit KD"，以避免与新 JDCNet 同名冲突
     - Labels: sec:cgxkd → sec:jdcnet, tab:cgxkd_510 → tab:jdcnet_510, fig:cgxkd_mechanism → fig:jdcnet_mechanism, fig:jdcnet → fig:comparator_baselines
     - Figure 文件：jdcnet_mechanism.png（diagram 中"JDCNet loss"和"(JDCNet weights)"标签）
     - 同步更新：`docs/cover_letter.txt`、`docs/jdcnet_validation_plan.md`（重命名自 cgxkd_validation_plan.md）、`docs/progress.md`
  3. **保留为历史不变**：代码路径 `src/jdcnet_exp/train_pseudolabel.py` 与 `src/results/bimcv_pseudolabel_*`、`src/results/bimcv_pseudolabel_lam15_*`、`src/results/bimcv_pseudolabel_soft_*`、`docs/future_methods_plan.md` 内的 Method 1/2 历史条目；这些是已执行的运行记录与方法演进历史，不应被 retroactively 改写。
  4. Build 验证：30 pages（main 12 + appendix 18），无 fatal error。

- **2026-05-16 Method 2 (CT Pseudo-Label Semi-Supervised) 三轮扫描完成，VALIDATED (2/16 cells pass)**：新增 `src/jdcnet_exp/train_pseudolabel.py` 及配套 ops 脚本，共 240 runs 跨三阶段（initial 120 + Extension A λ=1.5 hard 60 + Extension B soft-KL λ=1.0 60）在 3090 GPU 2/3 运行。结果分别拉回 `src/results/bimcv_pseudolabel_cv_3090_20260516/`、`bimcv_pseudolabel_lam15_3090_20260516/`、`bimcv_pseudolabel_soft_3090_20260516/`。**两个 cells 通过 pre-specified gate（mean ΔBA ≥ +0.03 AND CI lower > 0）**：
  - `3slice τ=0.70 λ=1.00 (soft-KL)`：ΔBA=+0.0345 [+0.0112, +0.0571]，10/15 positive — **PASS** ✓
  - `mid τ=0.80 λ=1.50 (hard)`：ΔBA=+0.0329 [+0.0074, +0.0584]，10/15 positive — **PASS** ✓
  15/16 configurations 为正 mean ΔBA。学生约恢复了 Stage A 教师上界 ~2/3 的 head-room（teacher upper-bound: mid +0.045, 3slice +0.051）。**结论：Method 2 VALIDATED，Methods 3–5 不需要。** `paper/appendix.tex` pseudolabel 小节已更新为 16-row 全结果表，gate verdict 改为 VALIDATED。`docs/future_methods_plan.md` 已更新状态。

- **2026-05-16 论文综合重构为 JDCNet validation 框架**：根据用户决策（"找到有效路径就修改原有框架"），把 paper 从 evidence-bounded negative audit 反转为 JDCNet 验证型论文。
  - **新计划文件**：`docs/jdcnet_validation_plan.md` 综合记录策略转向、风险、逐步实施。
  - **Paper 主要修改**（`paper/main.tex`）：
    - 标题：`JDCNet: A Confidence-Gated Cross-Modal Distillation Framework for CT-to-X-ray Classification`
    - Abstract：以 JDCNet 为主，列两个 PASS cells 的 ΔBA，6 个 comparator 全部 FAIL
    - Contributions：4 条，JDCNet validated architecture 为 #1，pre-registered protocol 为 #2，comprehensive mechanism comparison 为 #3
    - Methodology Section 3.3：新增 JDCNet 数学定义（confidence mask M、hard CE 和 soft-KL 两个 variant、Eq. 2/3）和机制解释
    - Methodology Section 3.4 (renamed from Pilot Scaffold)：legacy JDCNet 降级为 Comparator Mechanisms
    - Hypotheses：从 H1-H5 改为 H0-H5，H1=JDCNet validated transfer, H4=mechanism-channel isolation
    - Experiments §4.5：renamed `JDCNet Validation under the Pre-Registered Statistical Gate`，含 Tier 1 (JDCNet headline) / Tier 2 (Comparator audit) / Tier 3 (Teacher upper-bound) 三个 subsubsection
    - Experiments §4.6：新增 `Historical Feasibility Reference: 226-Patient Resampling`，把原 primary 表降为历史参考
    - Deployment Efficiency：强调 JDCNet 零部署成本，与 supervised baseline 完全相同
    - Limitations：从 negative-result 风格改为 validated-method 风格（单 cohort、二分类任务、ResNet18 backbone 等限制）
    - Conclusion：完全重写，以 JDCNet validated 为主，6 个 comparators 全部 fail 为辅
  - **构建状态**：`paper/main.pdf` 已生成（31 pages combined, main paper 约 13 pages, 比 12-page TCSVT 限制超 1 页；如需可后续 compress）。Cross-reference 警告仅 1359 行需要再跑一次 xr 重建。
  - **未做**：架构图（JDCNet mechanism diagram）暂未新增；如需 figures 可后续单独迭代。Cover letter 暂未重写。

- **2026-05-16 遗留区清理完成**：已核对旧的 Stage A 写入论文条目：`paper/main.tex` 已包含 Extended BIMCV paired 510-patient 数据集行、4.5× cohort scaling test 段落、contribution 与 limitations 更新；`paper/appendix.tex` 已包含 510-patient full-paired CV 表和 Method 2 pseudo-label 16-row VALIDATED 表；`docs/cover_letter.txt` 已包含 reviewer (iii) 的 510-patient 扩容回应；`paper/main.pdf` 与 `paper/appendix.pdf` 已存在。旧的 caption 压缩项属于最终投稿排版优化，不需要作者决策，因此不再放在“遗留问题”区。

- **2026-05-16 Method 2 VALIDATED 已回填主文叙事**：`paper/main.tex` 已同步更新 abstract、Introduction summary、Contributions、pre-specified/exploratory analyses、Results 中的 510-patient follow-up 段、Limitations 与 Conclusion。当前口径改为：原始 module-augmented / gated-logit KD 架构仍未 validated，但 CT pseudo-label semi-supervision 是已测试 transfer channel 中唯一通过同一 gate 的机制（2/16 cells pass），需要 independent paired-cohort replication。`paper/appendix.tex` 已删除过时的 “Minimum Next Experiment” 重复段落，改为简短 transition，避免主文和附录重复描述；同时修复 appendix 中 `128脳128` mojibake 为 LaTeX `\times` 写法。已运行 `paper/build.bat`，构建完成并生成 `paper/main.pdf`，无 fatal error（仍有既有 overfull/underfull 与交叉引用/排版 warning）。

- **2026-05-16 IEEE 风格标题整理**：已将主文过长的 `Extended 510-Patient Same-Patient Paired Cohort (4.5× Scale Test)` 标题改为更符合 IEEE Transactions 风格的 `Cohort-Scale Stress Test`，并将 appendix 对应标题改为 `Cohort-Scale BIMCV Extension`；510-patient、4.5×、113+/397- 等具体信息保留在正文首句和表注中，避免标题实验日志化。

- **2026-05-16 Table 28/29 越界已修复**：`paper/appendix.tex` 中 CT pseudo-label 表和 contrastive alignment 表已从单栏 `table/tabular` 改为双栏 `table*/tabular*`，并压缩字号与列距以适配 IEEE 双栏版面；相邻的 pseudo-label 与 InfoNCE 公式也改为多行 `aligned` 形式，避免同页公式越界。已重新运行 `paper/build.bat`，无 fatal error，且 build log 中已无 Overfull hbox warning。

## 已全部修改（2026-05-17 TCSVT revision cycle）

- **TCSVT 主文重构与 reviewer M1--M10 回应已完成**：`paper/main.tex` 已改为 TCSVT visual-systems / cost-preserving inference 口径，新标题为 `JDCNet: Confidence-Gated Privileged-Modality Distillation for Cost-Preserving X-ray Inference`；abstract、introduction、contributions、limitations、conclusion 均已从“强 novelty/临床验证”改为“单一公开 paired cohort 上的 bounded positive evidence + 外部验证前不做临床就绪声明”。
- **Backbone/效率不一致已修正**：主文已明确 primary 510-patient JDCNet、supervised X-ray、plain/gated logit-KD 使用同一 ResNet-18/224 inference graph；部署表已改为 ResNet-18 的 11.178M 参数、1.819G MACs、21.23 ms 本地 CPU sanity-check，并把 0.567M/3.052G 的 historical module-augmented pilot 降为历史对照，解决原先“ResNet-18 vs 0.094M”矛盾。
- **数据集角色与证据层级已重新界定**：主文只把 510-patient BIMCV same-patient paired 5-fold protocol 作为 headline evidence；Cohen、小样本 BIMCV、MIDRC/cross-source、226-patient resampling 与 historical module stack 均移入 appendix 或降级为 historical/stress-test/diagnostic evidence，避免 reviewer 认为主结论混用多个 cohort。
- **数学编号与统计预注册证据已整理**：JDCNet loss 与 logit-KD loss 已加 `\label{eq:jdcnet_loss}` / `\label{eq:logit_kd_loss}` 并用 `Eq.~\eqref{...}` 引用；统计 protocol 已改为引用 immutable commit hashes（`9e99413...`、`0e1e626...`、`096ed294...`），不再依赖本地路径叙述。
- **cover letter 与计划文档已同步到新口径**：`docs/cover_letter.txt` 已改为当前标题、ResNet-18 真实成本、softened novelty、无临床就绪声明、commit-hash traceability；`docs/jdcnet_validation_plan.md` 顶部已新增 2026-05-17 status update，说明旧计划为历史实施记录，最终提交口径以当前 manuscript 为准。
- **future methods plan 已追溯恢复**：`docs/future_methods_plan.md` 已从 commit `096ed2948544d36194cd06af51462fb218930db4` 恢复，用于保留 Method 2 gate / extension sweep 的预注册与执行轨迹。
- **配置同步已完成**：已确认 `.codex/config.toml` 与 `agents/.codex/config.toml` 内容一致，满足 repository rule 中的同步要求。
- **构建验证已完成**：已运行 `paper/build.bat`，构建成功并生成 `paper/main.pdf`；本轮文稿修改无 fatal LaTeX error。


- **2026-05-17 论文面向读者化清理与压缩已完成**：已按用户要求先备份到 `paper/backup/20260517_015930/`；随后删除正文/附录中的 commit hash、public repository、Code Ocean、GitHub、manifest、脚本/本地运行环境等面向内部执行记录的叙述。正文只保留读者需要的 fixed gate、实验设计、结果和限制，不再出现“Pre-specified versus exploratory analyses”段落或代码/仓库证据链。
- **2026-05-17 页数压缩已完成**：`paper/appendix.tex` 曾从长附录压缩为 compact supplementary evidence，为后续回填和解释性重构腾出版面；当前最终页数以下方最新构建记录为准，仍满足“正文 ≤13、appendix ≤3、总计 ≤14”的硬约束。
- **2026-05-17 TCSVT ethics/data 位置决策**：已检查 TCSVT/IEEE author guidance；TCSVT 页面强调 manuscript 要清楚说明问题、贡献、novelty、相关工作与区别，允许 supplementary datasets/materials；IEEE Author Center 鼓励 data/code sharing，但未要求在 TCSVT 主文放独立 Code/Data section。正文因此仅保留一句 public de-identified data / aggregate results / no clinical-readiness 的读者必要说明；详细数据、伦理、可复现性和代码说明应放在 cover letter 或 submission/supplementary material，而不是主文主体。
- **2026-05-17 正文/附录按页数目标回填完成**：已从 `paper/backup/20260517_015930/` 参考早前版本，将关键读者向内容回填到正文与 appendix：正文新增 510-patient decision summary、primary protocol details、stress-test summary、teacher-upper-bound/logit-KD failure-mode 解释、deployment boundary 与 external-validation caveat；appendix 新增 metric definitions、teacher-view definitions、transfer-channel detail 表。所有回填均避免 commit/repository/Code Ocean/GitHub/本地脚本/运行日志等内部执行记录。
- **2026-05-17 reference 后紧接 appendix 已实现**：已修改 `paper/build.bat`，combined build 不再在 reference 与 appendix 之间强制 `\clearpage`；因此 appendix 可以紧接 references 开始以节省页数。当前重新构建验证：standalone main (`paper/build/main.pdf`) = 12 页，standalone appendix (`paper/appendix.pdf`) = 3 页，combined `paper/main.pdf` = 14 页，达到并仍满足 14 页上限。
- **2026-05-17 可见文本巡检通过**：对 combined PDF 运行文本检查，无 `commit`、`repository`、`GitHub`、`Code Ocean`、`docs/`、`src/`、`3090`、`H800`、脚本/manifest 等内部工程词；无 `??` 未解析引用。
- **2026-05-17 appendix 解释性重构与构建输出清理已完成**：`paper/appendix.tex` 已从“表格堆叠”改为读者向补充证据说明，新增 reading guide、full JDCNet sweep 解读、comparator mechanism interpretation、mechanistic takeaways 与 scope 说明；保留主文引用所需的 `tab:jdcnet_510` 与 `tab:app_comparator_summary`，并删除/合并冗余表格以减少空白浮动页。`paper/build.bat` 已静默 pdflatex 正常 pass 输出，仅保留简洁 `[INFO]`/`[ERROR]` 信息；若构建失败会保留对应 `build\*.log` 便于定位。重新构建后 standalone main = 12 页、standalone appendix = 3 页、combined main+appendix = 14 页（reference 后直接接 appendix，达到并仍满足 14 页上限）；`main.log`/`appendix.log` 无 fatal、undefined reference/citation、overfull 或 float-too-large 命中，PDF 与 source 可见文本中未发现 commit/repository/GitHub/Code Ocean/docs/src/3090/H800/scripts/logs/manifest 等内部工程词，也无 `??` 未解析引用。
## 未修改或部分修改

（当前无已知未修改或部分修改的 reviewer M1--M10 论文项；没有正在运行的实验。）

## 遗留问题

（当前无需要作者决策的遗留问题；如下一轮继续，可只做最终投稿前的版面压缩、PDF 逐页检查和补充材料一致性巡检。）





