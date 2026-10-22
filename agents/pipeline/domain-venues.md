# 领域 Venue 数据库与评审标准

> 适用领域：大模型（LLM）、视觉语言模型（VLM）、机器学习（ML）、机器视觉（CV）

---

## 顶级会议（Tier 1）

| 会议 | 领域 | 审稿周期 | 评分制度 | 典型接收率 | 特殊要求 |
|------|------|---------|---------|-----------|---------|
| **NeurIPS** | ML/LLM/VLM | 5-6月 | 1-10分，4位reviewer + AC + SAC | ~25% | Checklist mandatory; reproducibility statement; broader impact |
| **ICML** | ML/LLM | 5-6月 | 1-10分，3-4位reviewer + AC | ~25% | Appendix page limit relaxed; code submission encouraged |
| **ICLR** | ML/LLM/VLM | 4-5月（OpenReview） | 1-10分，3-4位reviewer | ~30% | 公开评审（OpenReview）；rebuttal public；code expected |
| **CVPR** | CV/VLM | 4-5月 | 1-6分（strong reject → strong accept） | ~25% | Supplementary material limit; anonymity strict |
| **ICCV** | CV/VLM | 5-6月 | 同CVPR | ~25% | 双年会；同CVPR标准 |
| **ECCV** | CV/VLM | 5-6月 | 同CVPR | ~27% | 欧洲主办；同CVPR标准 |
| **ACL** | NLP/LLM | 4-5月 | 1-5分 + confidence | ~23% | ARR滚动评审；responsible NLP checklist |
| **EMNLP** | NLP/LLM | 4月 | 同ACL（ARR） | ~25% | 同ACL；Findings track接收率更高 |
| **AAAI** | AI general | 3-4月 | 1-10分 | ~20% | 多track；ethics review |
| **IJCAI** | AI general | 4-5月 | 1-10分 | ~15% | 最严格接收率之一 |

## 顶级期刊（Tier 1）

| 期刊 | 领域 | 影响因子范围 | 审稿周期 | 格式 | 特殊要求 |
|------|------|------------|---------|------|---------|
| **TPAMI** | CV/ML | 20+ | 6-12月 | IEEE LaTeX | 14页正文 + references；需显著超越会议版本 |
| **IJCV** | CV/VLM | 12+ | 4-8月 | Springer LaTeX | 需显著novelty over conference version |
| **JMLR** | ML | 5+ | 3-12月（差异大） | JMLR LaTeX/JMLR style | Open access；code strongly expected |
| **TIP** | Image Processing/CV | 10+ | 3-6月 | IEEE LaTeX | 严格page limit |
| **Nature Machine Intelligence** | ML/AI | 25+ | 2-4月 | Nature格式 | Highly selective；需broad interest |
| **AI Journal** | AI general | 5+ | 4-8月 | Elsevier | 理论 + 应用均可 |

---

## 领域特定评审关注点

### LLM 方向

| 评审关注 | 必须回答的问题 | 典型弱点 |
|---------|--------------|---------|
| **Scaling 行为** | 是否在不同规模展示了结果？是否有 scaling law 分析？ | 只在一个模型大小测试 |
| **Benchmark 覆盖度** | 是否覆盖了该任务的标准 benchmark？ | 只跑了自建 benchmark |
| **Baseline 公平性** | Baseline 是否使用了相同的训练数据/compute？ | 拿弱 baseline 衬托 |
| **训练细节** | Hyperparameter、learning rate schedule、tokenizer 是否完整？ | 缺乏可复现的训练细节 |
| **Compute 成本** | 是否报告了 GPU hours / FLOPs？ | 无法判断方法的实际可行性 |
| **Safety/Alignment** | 是否讨论了安全性/对齐影响？ | NeurIPS/ICML 越来越重视 |

### VLM 方向

| 评审关注 | 必须回答的问题 | 典型弱点 |
|---------|--------------|---------|
| **跨模态对齐** | 视觉和文本特征如何对齐？对齐质量如何验证？ | 模态对齐细节不足 |
| **视觉理解深度** | 是否超越了 image captioning？能否做 reasoning？ | 只做了简单的 VQA |
| **Hallucination 评估** | VLM 幻觉率如何？是否有专门评估？ | 忽略 hallucination 问题 |
| **数据质量** | 训练数据的来源、质量、bias 如何？ | 数据清洗过程不透明 |
| **Zero-shot vs Fine-tuned** | 是否区分了 zero-shot 和 fine-tuned 结果？ | 混淆不同设置的结果 |

### ML 方向（通用）

| 评审关注 | 必须回答的问题 | 典型弱点 |
|---------|--------------|---------|
| **理论贡献** | 是否有理论保证（convergence, bound, complexity）？ | 纯实验无理论分析 |
| **统计显著性** | 多次运行的 mean ± std？置信区间？ | 单次运行报告结果 |
| **Ablation** | 每个组件的贡献是否分别验证？ | 缺少 ablation study |
| **公平比较** | 所有方法是否在相同条件下比较？ | 不公平的实验设置 |
| **复杂度分析** | 时间/空间复杂度是否讨论？实际推理速度？ | 只报告准确率不报告效率 |

### CV 方向

| 评审关注 | 必须回答的问题 | 典型弱点 |
|---------|--------------|---------|
| **可视化质量** | 定性结果是否充分展示？failure cases？ | 只挑好的结果展示 |
| **标准 Benchmark** | 是否在 ImageNet/COCO/ADE20K 等标准集上评测？ | 只用私有数据集 |
| **实时性** | FPS/延迟是否报告？适合部署吗？ | 忽略推理效率 |
| **泛化性** | 跨数据集/跨域的泛化结果？ | 只在一个数据集上测试 |
| **预训练依赖** | 是否过度依赖预训练？公平比较？ | 预训练数据不对等 |

---

## 会议 Checklist 要点

### NeurIPS Checklist（mandatory since 2023）

1. Claims — 主要 claims 是否都有理论/实验支撑？
2. Limitations — 是否充分讨论了局限性？
3. Theory — 定理的完整证明是否在附录中？假设是否清晰？
4. Experiments — 是否报告了 error bars？多次运行？
5. Compute — 是否报告了计算资源？
6. Code — 代码是否提交/承诺提交？
7. Data — 数据集的 license 和 PII 处理？
8. Broader Impact — 社会影响讨论？

### CVPR/ICCV/ECCV Supplementary 要求

- 正文 8 页（不含 references）
- Supplementary 无页数限制但需合理
- 匿名性严格：不得在 arXiv 版本中提及会议提交
- 代码/数据在 supplementary 中提交
- 视频结果鼓励

### ICLR OpenReview 特殊规则

- 评审完全公开，作者 rebuttal 公开
- 其他研究者可发表公开评论
- 评审分数在决策前可能变化
- Code 作为 supplementary 强烈建议

---

## 论文格式速查

| Venue | 模板 | 正文页数限制 | 参考文献 | 附录 |
|-------|------|------------|---------|------|
| NeurIPS | neurips_2026.sty | 9页 | 不限 | 不限 |
| ICML | icml2026.sty | 8页 | 不限 | 不限 |
| ICLR | iclr2026_conference.sty | 9页 | 不限 | 不限 |
| CVPR | cvpr.sty | 8页 | 不限 | 合理范围 |
| ACL | acl.sty (ARR) | 8页(long)/4页(short) | 不限 | 不限 |
| TPAMI | IEEEtran.cls | 14页+ref | 不限 | 不限 |
| IJCV | Springer svjour3 | 无硬性限制 | 不限 | 合理范围 |

---

## AI 使用声明要求

| Venue | 要求 | 详情 |
|-------|------|------|
| NeurIPS | Mandatory checklist item | 必须声明 AI 工具使用情况 |
| ICML | 建议声明 | 鼓励在论文中说明 |
| ICLR | 无硬性要求 | 但公开评审可能被问到 |
| CVPR/ICCV | 无硬性要求 | 行业趋势是要求声明 |
| Nature MI | Mandatory | 必须在 Methods 中声明 AI 辅助细节 |
| TPAMI | IEEE 统一要求 | 按 IEEE 最新 AI policy |

---

## Venue 官网规格抓取协议

当 `USAGE.md` 中 `目标会议或期刊` 被设定后，Stage 8 / 9 / 12 首次执行时**必须**抓取 venue 官方投稿页面，核实并更新本文件中的 venue 规格。

### 抓取流程

1. **定位官方页面**：搜索 `{venue_name} {year} call for papers` 或 `{venue_name} author guidelines`
2. **抓取投稿规范**：从 CFP / Submission Instructions / Author Kit 页面提取以下字段
3. **与本文件核对**：如果本文件中已有该 venue 的记录，逐项比对；不一致则以**官网为准**更新
4. **如果本文件无记录**：在对应 Tier 表格中新增一条完整 entry

### 必须抓取的字段

| 字段 | 说明 | 示例 |
|------|------|------|
| **LaTeX 模板** | 官方指定的 `.cls` / `.sty` 文件名及版本 | `neurips_2026.sty` |
| **正文页数限制** | 不含 / 含引用、附录分别的页数上限 | 9 页（不含 ref）|
| **附录/Supplementary 限制** | 页数、文件大小、格式要求 | 无页数限制但 ≤ 100MB |
| **双盲/单盲/开放** | 匿名性要求，含 arXiv 限制 | 双盲，arXiv 不受限 |
| **Checklist 要求** | 是否 mandatory，具体 checklist 项目 | NeurIPS Checklist mandatory |
| **Ethics Review** | 是否有专门的 ethics 审查流程 | NeurIPS 有 ethics flag |
| **代码提交要求** | mandatory / encouraged / optional | encouraged but not required |
| **数据可用性要求** | 是否需要声明数据来源和许可 | Mandatory data statement |
| **AI 使用声明** | 是否需要 AI 工具使用说明 | NeurIPS mandatory checklist item |
| **截止日期** | abstract / full paper / supplementary 截止时间 | 以官网为准 |

### 核对频率

- 每次 Pipeline 中涉及 venue 规格的 Stage（8 / 9 / 12）首次执行时自动触发
- 如果距上次抓取超过 30 天，重新抓取
- 用户手动修改 `USAGE.md` 中的 `目标会议或期刊` 时立即重新抓取

### 信息冲突处理

- 官网信息 > 本文件硬编码信息
- 如果官网暂时无法访问，使用本文件中的信息并标注 `[UNVERIFIED — 官网不可达，使用缓存规格]`
- 抓取成功后在本文件对应 entry 末尾标注 `<!-- verified: YYYY-MM-DD -->`
