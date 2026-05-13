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
- **构建检查已完成**：已运行 `paper/build.bat`，`paper/main.pdf` 和 `paper/appendix.pdf` 均生成成功；剩余为既有排版/LaTeX warnings（如 appendix 大表 float too large、standalone appendix labels/bib warning），无 fatal error。

## 未修改或部分修改

1. **Related work / BibTeX 进一步扩展**：用户已确认需要做 bibliography pass；当前 related work 已覆盖 privileged information、modality hallucination、cross-modal distillation、BiomedCLIP/MedCLIP、RadImageNet 与 evidence robustness，但尚未系统加入更多 RGB-D/action/audio-visual cross-modal distillation 与 2023 以后 KD 文献。
   - 推进状态：等待执行。
   - 当前不需要新的作者输入；下一步可直接补充文献和 BibTeX。

2. **MIDRC 新 paired cohort 证据层**：用户已确认下一轮以 MIDRC 作为真正新增 cohort，NLST 暂不推进；MIDRC 数据链路已经在 H800 上跑通，当前结果属于 balanced pilot / mixed-cohort parameter screen，尚不能写成最终 validated architecture 结果。
   - 推进状态：H800 已完成 126-case balanced preprocessing（63/63）、3 seeds × 4 rows short-proof runs，以及 MIDRC+BIMCV mixed 3 teachers + 33 student configs 全量参数筛选；本地结果在 `src/results/midrc_short_proof_h800/` 和 `src/results/h800_midrc_bimcv_gapkd/`。
   - 当前关键发现：H800 参数筛选显示 supervised 平均 BA `0.7253`、plain KD `0.7197`；最佳 GAP-KD 均值为 thr=`0.55`, proj=`0.00` 的 BA `0.7177`，仍低于 supervised/plain KD。没有配置满足 3 seeds 均稳定优于 baseline。该 mixed manifest 的 MIDRC 子集是 63/63 balanced，但加入 BIMCV 后全局为 124 positive / 63 negative，应按 positive-enriched diagnostic screen 解释。
   - 下一步：不启动完整 6 行矩阵；先把论文口径固定为 evidence-bounded，并等待 3090 的 BIMCV proxy sweep 和 MIDRC 559 下载完成后决定是否还有必要做更大样本验证。

3. **GAP-KD/JDCNet-v2 结果性实验**：3090 已完成 BIMCV Path-C same-cohort follow-up，H800 已完成 MIDRC balanced short-proof runs 和 MIDRC+BIMCV 参数筛选；这些结果显示 GAP-KD 有方向性尝试价值，但尚未达到论文中“框架有效性/validated architecture”的证据门槛。
   - 推进状态：H800 mixed sweep 结果已拉回。方法均值：supervised `0.7253`，plain KD `0.7197`，GAP-KD thr=`0.55`/proj=`0.00` `0.7177`，thr=`0.60`/proj=`0.02` `0.7146`，thr=`0.65`/proj=`0.05` `0.7141`。
   - 当前判断：不能把本次修改方案写成已验证有效的论文主框架；可以写成预注册/后续工作或实现层面的 negative/diagnostic evidence。
   - 建议下一步：暂停 H800 继续烧卡；完成 3090 正在运行的下载和 BIMCV proxy sweep；同步更新 paper 和 docs，删除/降调任何“GAP-KD 已验证有效”的措辞。

## 遗留问题

1. **GAP-KD seed 43 instability — H800 参数筛选已完成，3090 proxy sweep 仍在运行**
   - H800 当前状态：3 teachers + 33 student configs 已全部完成；结果拉回 `src/results/h800_midrc_bimcv_gapkd/`。GPU 查询为 0 MiB，无训练任务需要继续占卡。
   - H800 筛选结论：部分配置改善 seed 43，但会牺牲 seed 42 或 seed 44；没有找到 3 seeds 均 ΔBA > 0 vs supervised/plain KD 的稳定配置。
   - 3090 当前状态（2026-05-13 14:45 UTC）：BIMCV pathC 代理扫描在 4 卡上运行；当前 24/27 run dirs 已创建（缺 3 个配置），完成run数检查中。MIDRC 559 下载**已停止**（无gen3进程，无下载目录，推断失活）。
   - 3090 扫描配置：gate_threshold ∈ {0.55, 0.60, 0.65} × projected_attention_weight ∈ {0.0, 0.02, 0.05} × seeds {42, 43, 44} = **27 runs**；4 GPU 并行，每卡顺序跑 6~7 个 run。
   - 脚本：`src/ops/remote_3090_gapkd_sweep.sh`（launch）、`src/ops/remote_3090_gapkd_sweep_summarize.sh`（汇总）、`src/ops/poll_3090_sweep.sh`（监控）。
   - 结果目录：`/data/JDCNET/src/runs/bimcv_gapkd_sweep/`，配置：`/data/JDCNET/src/configs/bimcv_gapkd_sweep/`。
   - 基线参考（bimcv_pathc，seeds 42/43/44）：supervised `0.624/0.623/0.608`，plain KD `0.616/0.647/0.612`。
   - 完成后拉取：运行 `wsl bash src/ops/poll_3090_sweep.sh` 监控；完成后在 3090 运行 `bash /data/JDCNET/src/ops/remote_3090_gapkd_sweep_summarize.sh` 得矩阵报告。
   - 判断门槛：若 3090 也没有出现 3 seeds 稳定优于 plain KD/supervised 的组合，则 GAP-KD 只能保留为未验证的 future work 或 negative diagnostic，不再投入 H800 完整矩阵。

2. **MIDRC 下载重启后疑似假活跃 / 卡住**
   - 当前状态：`/data1/midrc/raw_559cases_combined` 已有 979 个文件，约 121 GB；最近 10 分钟新增 0 个文件，最近 30 分钟也无新增。
   - 进程状态：`gen3-client download-multiple` 仍在运行，但现有日志检索未见稳定的 retry/timeout/error 关键词，较像假活跃或卡在个别对象/连接上，而不是持续推进。
   - 下一步：优先追最近重启日志和下载器的错误输出，再决定是重启下载进程、切换参数，还是直接把这条链路标记为 stalled。

3. **H800 费用控制**
   - 当前状态：H800 结果已拉回，GPU 空闲 0 MiB；若平台仍在计费，应立即在平台控制台停止实例或恢复自动关机。
   - 下次启动实验前：若要无人值守运行，需明确是否恢复脚本完成后自动 `poweroff -f || shutdown -h now || kill -TERM 1`；如果只是调参观察，应保持不自动关机并手动在平台控制台停止计费。
