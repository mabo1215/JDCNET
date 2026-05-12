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
- **构建检查已完成**：已运行 `paper/build.bat`，`paper/main.pdf` 和 `paper/appendix.pdf` 均生成成功；剩余为既有排版/LaTeX warnings（如 appendix 大表 float too large、standalone appendix labels/bib warning），无 fatal error。

## 未修改或部分修改

1. **Related work / BibTeX 进一步扩展**：用户已确认需要做 bibliography pass；当前 related work 已覆盖 privileged information、modality hallucination、cross-modal distillation、BiomedCLIP/MedCLIP、RadImageNet 与 evidence robustness，但尚未系统加入更多 RGB-D/action/audio-visual cross-modal distillation 与 2023 以后 KD 文献。
   - 推进状态：等待执行。
   - 当前不需要新的作者输入；下一步可直接补充文献和 BibTeX。

2. **MIDRC 新 paired cohort 证据层**：用户已确认下一轮以 MIDRC 作为真正新增 cohort，NLST 暂不推进；MIDRC 数据链路已经在 H800 上跑通，当前结果属于 balanced pilot / short-proof evidence，尚不能写成最终 validated architecture 结果。
   - 推进状态：H800 已完成 126-case balanced preprocessing（63/63）和 3 seeds × 4 rows short-proof runs；本地结果在 `src/results/midrc_short_proof_h800/logs/summary.csv`。
   - 当前关键发现：GAP-KD 平均 BA 高于 supervised/plain KD，但 seed 43 低于二者，说明方法有正向信号但稳定性不足。
   - 下一步：先解决 seed 43 instability，再决定是否启动完整 6 行矩阵。

3. **GAP-KD/JDCNet-v2 结果性实验**：3090 已完成 BIMCV Path-C same-cohort follow-up，H800 已完成 MIDRC balanced short-proof runs；这些结果显示 GAP-KD 有方向性收益但尚未达到稳定优于 supervised/plain KD 的完整矩阵启动门槛。
   - 推进状态：MIDRC 3 seeds short-proof 已完成。BA 均值：supervised `0.605`，plain KD `0.605`，GAP-KD conf+proj `0.623`；逐 seed 的 GAP-supervised 为 `+0.053, -0.053, +0.053`，GAP-plain 为 `+0.053, -0.079, +0.079`。
   - 当前判断：不应立即启动完整 6 行矩阵；需要先做小型参数筛选以修复 seed 43 不稳定。
   - 建议下一步：固定数据 split，运行 GAP-KD gate threshold `0.55/0.60/0.65` 与 projected_attention_weight `0/0.02/0.05` 的小型筛选；若 3 seeds 均稳定高于 supervised 与 plain KD，再启动完整 6 行矩阵。

## 遗留问题

1. **GAP-KD seed 43 instability — 参数筛选已在 3090 启动**
   - 当前状态：BIMCV pathC 代理扫描已于 2026-05-12 22:01 UTC 在 3090 4 卡上启动。
   - H800 当前关机（connection refused port 12437），MIDRC 559-case 数据在 H800 上；故以 BIMCV pathC 数据作代理扫描。
   - 扫描配置：gate_threshold ∈ {0.55, 0.60, 0.65} × projected_attention_weight ∈ {0.0, 0.02, 0.05} × seeds {42, 43, 44} = **27 runs**；4 GPU 并行，每卡顺序跑 6~7 个 run。
   - 脚本：`src/ops/remote_3090_gapkd_sweep.sh`（launch）、`src/ops/remote_3090_gapkd_sweep_summarize.sh`（汇总）、`src/ops/poll_3090_sweep.sh`（监控）。
   - 结果目录：`/data/JDCNET/src/runs/bimcv_gapkd_sweep/`，配置：`/data/JDCNET/src/configs/bimcv_gapkd_sweep/`。
   - 基线参考（bimcv_pathc，seeds 42/43/44）：supervised `0.624/0.623/0.608`，plain KD `0.616/0.647/0.612`。
   - 完成后拉取：运行 `wsl bash src/ops/poll_3090_sweep.sh` 监控；完成后在 3090 运行 `bash /data/JDCNET/src/ops/remote_3090_gapkd_sweep_summarize.sh` 得矩阵报告。
   - 判断门槛：若存在 thr/proj 组合使 3 seeds 均 ΔBA > 0 vs plain KD，即为稳定配置；若还满足平均 ΔBA ≥ +0.03，可考虑在 H800 重启后以 MIDRC 数据验证该配置并启动完整矩阵。

2. **H800 费用控制**
   - 当前状态：短版证明框架结果已拉回，本轮自动关机已取消以便检查和决策。
   - 下次启动实验前：若要无人值守运行，需明确是否恢复脚本完成后自动 `poweroff -f || shutdown -h now || kill -TERM 1`；如果只是调参观察，应保持不自动关机并手动在平台控制台停止计费。
