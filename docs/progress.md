# 进度日志

## 已全部修改

- 已消化 `## 遗留问题` 中关于 BIMCV paired cohort 的作者回答；修改说明：`paper/main.tex` 与 `paper/appendix.tex` 已明确写入 BIMCV-COVID19+ 作为已准备好的下一队列资源，包含 638 名 COVID-positive same-patient CT+CXR 受试者和 3,080 张关联胸片。
- 已删除旧进度中“当前没有更大 paired cohort”的过期判断；修改说明：论文现在区分“更大 COVID-positive same-patient paired resource 已存在”和“当前二分类 same-patient external validation 仍缺少 matched non-COVID paired cohort”。
- 已在主文中修正数据与限制表述；修改说明：`paper/main.tex` 的 Datasets、Implementation and Reproducibility、Limitations and Future Work 现在都说明 BIMCV 不能直接并入当前 headline tables，因为它暂时只扩大阳性配对侧，不能单独支撑 binary COVID-19 versus non-COVID same-patient 外部验证。
- 已在附录中补充可复现边界；修改说明：`paper/appendix.tex` 现在说明 BIMCV 准备流程、positive-pair 支持规模、BIMCV negative CXR 不含 same-patient CT 的限制，以及如果未来使用 cross-source non-COVID control 必须显式标注其不是 same-patient paired evidence。
- 已处理 stronger generic feature-alignment baseline 的遗留解释；修改说明：主文与附录已说明 attention transfer 和 feature hint 覆盖当前最低成本 generic alignment controls，更强 representation-alignment family 只有在更大且类别更完整的 paired cohort 下才有解释价值。
- 已同步清理 `docs/progress.md`；修改说明：移除了旧的长篇遗留问题、已回答的 A 槽、局部路径细节和凭据痕迹，恢复为 `## 已全部修改`、`## 未修改或部分修改`、`## 遗留问题` 三段结构。

## 未修改或部分修改

- 真正独立的 binary same-patient external validation 仍未运行；未完成原因：现有 BIMCV 准备资源解决了 COVID-positive same-patient CT+CXR 规模问题，但尚未提供 matched same-patient non-COVID CT+CXR 对照。当前已完成的解决方式是把这一点写入主文和附录，避免把 cross-source non-COVID control 伪装成 same-patient external validation。
  - 仍需作者提供/决策：若要继续新增外部验证实验，请提供 matched same-patient non-COVID CT+CXR 数据源，或明确批准将 cross-source non-COVID CT/CXR control 作为单独的补充实验而不是 same-patient evidence。
  - 当前推进状态：等待作者数据或实验范围决策；在此之前，论文保持 evidence-bounded pilot-study 定位。

## 遗留问题

- 是否继续做 cross-source non-COVID control 作为补充实验，而不是 same-patient external validation？
  - 需要你提供/决策：
  1. 是否接受将 cross-source non-COVID control 明确标注为 category-level control，而不是 same-patient paired evidence？
     A:  是的  category-level control
  2. 若要运行该补充实验，请提供 non-COVID CT 与 non-COVID CXR 的最终数据源路径或确认继续使用现有本地资源。
Hugging Face full-text search 查了一轮，没有找到完全符合的真实临床数据集。

结论
没有发现可直接作为：

matched same-patient non-COVID CT+CXR

的数据集。

搜索中最接近的是
farrell236/DRR-RATE

它的特点：

基于 CT-RATE
CT-RATE 有 25,692 个 non-contrast chest CT volumes，来自 21,304 个 unique patients
DRR-RATE 从这些 CT 生成 frontal digitally reconstructed radiographs, 即 synthetic X-ray-like DRR
有 radiology reports 和 18 个 pathology labels
但它不满足当前论文遗留问题，因为：

DRR 是 CT-derived synthetic radiograph，不是真实临床采集的 chest X-ray/CXR
它不是 COVID-19 versus non-COVID 配对验证集
它可以算 same-patient CT + synthetic X-ray-like image，但不能写成真实 same-patient CT+CXR external validation
所以它最多适合未来作为：

synthetic CT-to-radiograph sanity check

不能替代：

real matched same-patient non-COVID CT+CXR external validation

我也把这轮 Hugging Face 搜索结果写进 docs/progress.md 了。

参考：

Hugging Face 搜索页：https://huggingface.co/search/full-text?q=CT+CXR+same+patient&type=dataset
DRR-RATE：https://huggingface.co/datasets/farrell236/DRR-RATE
CT-RATE：https://huggingface.co/datasets/ibrahimhamamci/CT-RATE

	 你可以查下 下载数据的huggingface 和 kaggle key在  C:\source\.env 你可以修改添加代码来下载  下载到 /mnt/d/work/datasets/CTXRAY/     


