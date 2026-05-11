# 进度

## 已全部修改

- **3090 Path C 结果已回填论文**：BIMCV 512-patient balanced-validation re-split 未把 CT logit KD 推过显著性门槛；当前口径保持 evidence-bounded，不升级为 validated architecture。
- **Path C 数值结果已迁移**：3090 拉回的数值结果已从 `docs/tmp/3090_pathc/` 转移到 `src/results/bimcv_pathc_3090/`，避免继续把实验结果放在 `docs/tmp`。
- **实验计划已收口**：`docs/tmp/experiment_plan.md` 和 `docs/tmp/jdcnet_upgrade_plan.md` 已更新为“当前投稿不再追加同 cohort 微调实验；validated architecture 升级未成立；未来需要真正新增 paired cohort”。
- **两组评审意见已合并**：`docs/revision_suggestions.tex` 已整理为单一综合修改意见，重复项已合并，主线转向 evidence-bounded negative-result / protocol contribution。
- **本轮 manuscript narrative revision 已完成**：`paper/main.tex` 已把标题改为 evidence-bounded evaluation 叙事，压缩 abstract，强化 TCSVT visual-systems framing，更新 H1/H5 claim-status，重写 contributions，demote DPE/MHRA/DFPN 为 optional stress-test modules，并把 limitations/conclusion 改为“CT teacher feasible + cross-modal KD unvalidated”。
- **统计口径已降调**：主文已明确小样本 specificity 退化问题，主结果表已切换为 median (Q1,Q3) + 95% bootstrap CI；mean±SD 仅保留在 appendix extended descriptive table。
- **目标 venue 当前决策已消费**：按用户回答，当前继续按 TCSVT visual-systems / deployment-only inference framing 推进，但保留 scope risk 的文字降调。
- **Appendix 大表排版决策已消费**：按用户回答，BIMCV stress-test 大表压缩放到最终投稿排版阶段处理；当前仅记录 existing float-too-large warning，不作为本轮算法修改阻挡项。
- **GAP-KD/JDCNet-v2 代码框架已启动**：已新增 confidence-gated KD、projection-compatible attention loss、CPU synthetic smoke test 和 H800 no-card 启动脚本；本地 CPU smoke test 通过，结果在 `src/results/gapkd_cpu_smoke_local/smoke_gapkd.json`。
- **H800 无卡 smoke 实验已完成**：已把 GAP-KD/JDCNet-v2 最小代码同步到 H800，在无卡/CPU 环境运行 synthetic smoke test 并拉回结果；`src/results/h800_gapkd_cpu_smoke/smoke_gapkd.json` 显示 5/5 checks passed。
- **构建检查已完成**：已运行 `paper/build.bat`，`paper/main.pdf` 和 `paper/appendix.pdf` 均生成成功；剩余为既有排版/LaTeX warnings（如 appendix 大表 float too large、standalone appendix labels/bib warning），无 fatal error。

## 未修改或部分修改

1. **Related work / BibTeX 进一步扩展**：用户已确认需要做 bibliography pass；当前 related work 已覆盖 privileged information、modality hallucination、cross-modal distillation、BiomedCLIP/MedCLIP、RadImageNet 与 evidence robustness，但尚未系统加入更多 RGB-D/action/audio-visual cross-modal distillation 与 2023 以后 KD 文献。
   - 推进状态：等待执行。
   - 当前不需要新的作者输入；下一步可直接补充文献和 BibTeX。

2. **MIDRC 新 paired cohort 证据层**：用户已确认下一轮以 MIDRC 作为真正新增 cohort，NLST 暂不推进；当前 GAP-KD/JDCNet-v2 只有代码和 CPU smoke，不应写成论文有效性结果。
   - 推进状态：等待 MIDRC 数据审计/下载/筛选。
   - 仍需作者提供或确认：MIDRC 下载继续可用、目标样本量、是否允许后续 GPU 训练预算。

3. **GAP-KD/JDCNet-v2 结果性实验**：代码框架已通过本地和 H800 CPU smoke，但还没有在真实 paired cohort 上训练/评估，因此不能解决论文 validated architecture 的证据问题。
   - 推进状态：代码就绪，实验阻塞于新 cohort。
   - 仍需作者决策：是否在 MIDRC 审计通过后，把最小矩阵设为 X-ray supervised、CT teacher、plain CT logit KD、confidence-gated KD、confidence-gated projection/anatomy KD。

## 遗留问题

1. **MIDRC 新 cohort 路线**
   - 需要你确认：继续以 MIDRC 作为下一轮真正新增 cohort，并暂停 NLST；是否允许后续在 MIDRC 审计通过后启动 GPU 训练？
   - A: MIDRC，允许后续 GPU 训练 / MIDRC，但先只做数据审计 / 暂停

2. **GAP-KD/JDCNet-v2 最小实验矩阵**
   - 需要你确认：MIDRC 审计通过后，是否采用最小矩阵：X-ray supervised、CT teacher、plain CT logit KD、confidence-gated KD、confidence-gated projection/anatomy KD？
   - A: 是的  
