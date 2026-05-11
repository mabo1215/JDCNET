# 进度

## 已全部修改

- **3090 Path C 结果已回填论文**：BIMCV 512-patient balanced-validation re-split 未把 CT logit KD 推过显著性门槛；当前口径保持 evidence-bounded，不升级为 validated architecture。
- **Path C 数值结果已迁移**：3090 拉回的数值结果已从 `docs/tmp/3090_pathc/` 转移到 `src/results/bimcv_pathc_3090/`，避免继续把实验结果放在 `docs/tmp`。
- **实验计划已收口**：`docs/tmp/experiment_plan.md` 和 `docs/tmp/jdcnet_upgrade_plan.md` 已更新为“当前投稿不再追加同 cohort 微调实验；validated architecture 升级未成立；未来需要真正新增 paired cohort”。
- **两组评审意见已合并**：`docs/revision_suggestions.tex` 已整理为单一综合修改意见，重复项已合并，主线转向 evidence-bounded negative-result / protocol contribution。
- **本轮 manuscript narrative revision 已完成**：`paper/main.tex` 已把标题改为 evidence-bounded evaluation 叙事，压缩 abstract，强化 TCSVT visual-systems framing，更新 H1/H5 claim-status，重写 contributions，demote DPE/MHRA/DFPN 为 optional stress-test modules，并把 limitations/conclusion 改为“CT teacher feasible + cross-modal KD unvalidated”。
- **统计口径已降调**：主文已明确 mean±SD 为描述性统计，提示每个 resample 只有一个 negative validation patient，robust median/IQR/bootstrap 结果放在 appendix；Wilcoxon 表已标注为 uncorrected failure-mode diagnosis，不作为 family-wise positive-transfer 证明。
- **构建检查已完成**：已运行 `paper/build.bat`，`paper/main.pdf` 和 `paper/appendix.pdf` 均生成成功；剩余为既有排版/LaTeX warnings（如 appendix 大表 float too large、standalone appendix multiply-defined labels），无 fatal error。

## 未修改或部分修改

1. **主文主结果表是否彻底改成 median/IQR 口径**：当前已在 caption 中说明 mean±SD 仅为描述性统计，并引用 appendix robust statistics；但尚未把主文 Table 的数值列直接替换为 median/IQR。
   - 推进状态：部分完成。
   - 仍需作者决策：是否为了更强统计保守性，把主文主表从 mean±SD 改为 median [Q1,Q3]，把 mean±SD 完全移到 appendix？

2. **TCSVT venue-fit 最终路线**：当前 manuscript 已按 TCSVT 保留 visual-systems / deployment-only inference framing，但综合评审仍认为 TCSVT 存在 scope risk。
   - 推进状态：部分完成。
   - 仍需作者决策：继续冲 TCSVT，还是转向 IEEE TMI / MIA / IEEE JBHI / negative-results venue？

3. **Related work / BibTeX 进一步扩展**：当前 related work 已覆盖 privileged information、modality hallucination、cross-modal distillation、BiomedCLIP/MedCLIP、RadImageNet 与 evidence robustness；但尚未系统加入更多 RGB-D/action/audio-visual cross-modal distillation 与 2023 以后 KD 文献。
   - 推进状态：部分完成。
   - 仍需作者决策：是否要为下一版做一次专门 bibliography pass，加入更宽的 cross-modal / post-2023 KD 文献？

4. **Appendix 大表排版与 caption 收口**：appendix BIMCV stress-test 表仍然较大，构建时有 float-too-large warning；当前不影响 PDF 生成，但投稿前最好压缩表格或拆分解释文字。
   - 推进状态：部分完成。
   - 仍需作者决策：是否现在投入时间压缩 appendix 表格，还是投稿前最终排版阶段再处理？

5. **新 paired cohort 证据层**：MIDRC/NLST 等新 CT+X-ray paired cohort 仍是 future-work / post-submission evidence layer；当前论文不再用同一 BIMCV cohort 继续尝试把结论推成 validated architecture。
   - 推进状态：等待新数据源决策。
   - 仍需作者决策：是否继续下载/筛选 MIDRC/NLST 作为下一轮真正新增 cohort？

## 遗留问题

1. **目标 venue 决策**
   - 需要你决策：继续按 TCSVT 投稿，还是切换到更匹配 negative-result / medical-imaging methodology 的 venue？
   - A: 是

2. **主结果统计表口径**
   - 需要你决策：主文 Table 是否从 mean±SD 改成 median [Q1,Q3] + bootstrap CI？
   - A:  是，第二种

3. **Related work 扩展强度**
   - 需要你决策：是否现在做一轮系统 bibliography pass，补充更多 cross-modal distillation / post-2023 KD / biomedical foundation model 文献？
   - A: 是

4. **Appendix 排版投入时间**
   - 需要你决策：是否现在压缩 BIMCV stress-test 大表和长解释，还是最终投稿排版阶段处理？
   - A: 最终投稿排版阶段处理

5. **新 paired cohort 路线**
   - 需要你决策：MIDRC/NLST 是否作为下一轮真正新增 cohort 继续推进，还是当前投稿只保留为 future work？
   - A:  MIDRC为下一轮真正新增 cohort 继续推进 不要 NLST.
