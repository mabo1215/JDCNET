# 进度

## 已全部修改

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
- **构建检查已完成**：已运行 `paper/build.bat`，`paper/main.pdf` 和 `paper/appendix.pdf` 均生成成功；剩余为既有排版/LaTeX warnings（如 appendix 大表 float too large、standalone appendix labels/bib warning），无 fatal error。

## 未修改或部分修改

1. **Related work / BibTeX 进一步扩展**：用户已确认需要做 bibliography pass；当前 related work 已覆盖 privileged information、modality hallucination、cross-modal distillation、BiomedCLIP/MedCLIP、RadImageNet 与 evidence robustness，但尚未系统加入更多 RGB-D/action/audio-visual cross-modal distillation 与 2023 以后 KD 文献。
   - 推进状态：等待执行。
   - 当前不需要新的作者输入；下一步可直接补充文献和 BibTeX。

2. **MIDRC 新 paired cohort 证据层**：用户已确认下一轮以 MIDRC 作为真正新增 cohort，NLST 暂不推进；MIDRC 数据链路已经在 H800 上跑通，当前结果属于 balanced pilot / mixed-cohort parameter screen，尚不能写成最终 validated architecture 结果。
   - 推进状态：H800 已完成 126-case balanced preprocessing（63/63）、3 seeds × 4 rows short-proof runs，以及 MIDRC+BIMCV mixed 3 teachers + 33 student configs 全量参数筛选；本地结果在 `src/results/midrc_short_proof_h800/` 和 `src/results/h800_midrc_bimcv_gapkd/`。
   - 当前关键发现：H800 参数筛选显示 supervised 平均 BA `0.7253`、plain KD `0.7197`；最佳 GAP-KD 均值为 thr=`0.55`, proj=`0.00` 的 BA `0.7177`，仍低于 supervised/plain KD。没有配置满足 3 seeds 均稳定优于 baseline。该 mixed manifest 的 MIDRC 子集是 63/63 balanced，但加入 BIMCV 后全局为 124 positive / 63 negative，应按 positive-enriched diagnostic screen 解释。
   - 下一步：不启动完整 6 行矩阵；论文口径已固定为 evidence-bounded，等待 MIDRC 559 下载完成后运行 `src/ops/h800_midrc_locked_validation.sh` 的锁参 4 行验证矩阵。

3. **GAP-KD/JDCNet-v2 结果性实验**：3090 已完成 BIMCV Path-C same-cohort follow-up，H800 已完成 MIDRC balanced short-proof runs 和 MIDRC+BIMCV 参数筛选；这些结果显示 GAP-KD 有方向性尝试价值，但尚未达到论文中“框架有效性/validated architecture”的证据门槛。
   - 推进状态：3090 BIMCV Path-C 27-run threshold/projection sweep 已完成并写入 appendix；唯一三 seed 均优于 plain KD 的组合是 threshold=`0.55`、proj=`0`，mean ΔBA 约 `+0.0095`，信号太弱。
   - 当前判断：不能把本次修改方案写成已验证有效的论文主框架；已改为实现层面的 negative/diagnostic evidence。
   - 建议下一步：暂停继续烧卡；已预先锁定 conservative reliability-gated KD（threshold=`0.55`, proj=`0`），只有 MIDRC 559 下载完成并通过独立 test split 门槛后才可重新讨论 validated architecture。

## 遗留问题

1. **GAP-KD seed 43 instability — 已作为 negative/diagnostic evidence 写入论文**
   - 3090 当前结论：BIMCV Path-C 27-run threshold/projection sweep 已完成；只有 threshold=`0.55`、proj=`0` 在三 seed 上都相对 plain KD 为正，但平均 ΔBA 仅约 `+0.0095`，不足以成为 validated architecture。
   - MIDRC pilot 当前结论：GAP-KD conf+proj 平均 BA `0.623 ± 0.061`，高于 supervised/plain KD 的 `0.605`，但 seed 43 对 supervised 为 `-0.053`、对 plain KD 为 `-0.079`，稳定性门槛未过。
   - 论文处理：正文只保留总括，appendix 放诊断表；当前算法只能写成实现已验证、机制已压力测试、有效性未验证成功。
   - 下一步门槛：如要重新升级为正向算法贡献，必须在下载完成后的更大 MIDRC paired cohort 上按 `docs/VALIDATED_ARCHITECTURE_EXPERIMENT_PLAN.md` 预先锁定配置，并满足三 seed 均优于 supervised/plain KD 且 mean ΔBA 至少约 `+0.03`。

2. **MIDRC 559 下载仍在慢速推进**
   - 当前状态（2026-05-13 06:02 UTC）：3090 上 `gen3-client download-multiple` 仍在运行，screen 为 `midrc_559_combined_dl`；`/data1/midrc/raw_559cases_combined` 为 `985` files / `985` zip，约 `122G`。
   - 活跃性判断：60 秒采样中目录总 bytes 从 `130186075893` 增至 `130187102965`，增加约 `1.0MB`；active log 也在增长，说明不是完全卡死。
   - 风险：文件数长时间不变，当前主要是在几个大 zip 的 partial download 上缓慢推进，速度偏慢；继续观察即可，若连续多次采样 bytes 也不增长再重启下载进程。

3. **H800 费用控制**
   - 当前状态：H800 结果已拉回，GPU 空闲 0 MiB；若平台仍在计费，应立即在平台控制台停止实例或恢复自动关机。
   - 下次启动实验前：若要无人值守运行，需明确是否恢复脚本完成后自动 `poweroff -f || shutdown -h now || kill -TERM 1`；如果只是调参观察，应保持不自动关机并手动在平台控制台停止计费。
