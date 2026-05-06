# 进度日志

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

## 已全部修改

- 已消化 `## 遗留问题` 中关于 BIMCV paired cohort 的作者回答；`paper/main.tex` 与 `paper/appendix.tex` 已明确写入 BIMCV-COVID19+ 作为已准备好的下一队列资源。
- 已删除旧进度中"当前没有更大 paired cohort"的过期判断。
- 已在主文中修正数据与限制表述；BIMCV 不能直接并入当前 headline tables 已在多处说明。
- 已在附录中补充可复现边界；BIMCV 准备流程、限制均已写入。
- 已处理 stronger generic feature-alignment baseline 的遗留解释。
- **cross-source non-COVID control 决策已消化**：Limitations 明确"Any future cross-source non-COVID control must be reported explicitly as a category-level control, not as same-patient evidence."
- **目标期刊确认 IEEE TCSVT，IEEEtran 模板无需切换**：已消化作者答复，`USAGE.md` 已正确设置为 IEEE TCSVT，无需修改。
- **Abstract 重构（Minor 15）**：resampling 证据前置，fixed-split 降格为次级 screen，首定义 `\emph{same-case evaluation}`。
- **same-case evaluation 定义（Minor 22）**：Section 3.3 新增括号定义句。
- **DPE/MHRA/DFPN 作者自创缩写声明（Minor 5）**：Section 3.2 末段新增说明。
- **KL 方向说明（Minor 6）**：Equation 1 后补充 teacher-to-student 方向及梯度路径。
- **Equation 1 格式修复（Typog 3）**：重写为单行公式，消除 KL scope 歧义，使用统一 `\bigl/\Bigl` 括号。
- **CT 时间配对细节（Minor 18）**：无 offset 时使用唯一 CT、axial slice 选取方法。
- **CT 预处理说明（Minor 19）**：8-bit 灰度、bilinear resize、无均衡化。
- **AT/FH 实现细节（Minor 8）**：Section 4.2 新增 attention transfer 和 feature hint 描述段。
- **Table 4 late-fusion 标注（Minor 9）**：`\textdagger` caption 脚注 + table 行标注。
- **±0.000 解释（Minor 12）**：Table 4 caption + Section 4.4 说明 trivial collapse。
- **DPE 参数量说明（Minor 14）**：Section 4.5 解释 +DPE 不增加参数原因。
- **参考文献 arXiv → 发表版（Minor 24）**：`dosovitskiy` → ICLR 2021；`romero` → ICLR 2015。
- **新增参考文献（Minor 25）**：`lin2017fpn`、`tian2020contrastive`、`nie2018medical`、`liu2021swin`。
- **Related Work 扩展（Minor 1/25）**：新增 CRD、Nie TMI、FPN、Swin 引用及背景说明；解释为何不使用 ViT/Swin 骨架。
- **Figure 1 caption 排版修复（Typog 1）**：删除 tab 字符。
- **Limitations 压缩（Minor 23）**：从 ~1100 词压缩至 ~280 词，结构化三组要点。
- **标题优化（Minor 16）**：`CT-to-X-ray Distillation Under Tiny Paired Cohorts: An Evidence-Bounded Reproducible Pilot Study` → `CT-to-X-ray Knowledge Distillation Under Patient-Level Paired Cohorts: An Evidence-Bounded Evaluation Framework`；PDF metadata 同步更新；appendix title 同步。
- **TCSVT scope 段落（M6）**：Section 1.1 Motivation 开头新增 3 句 TCSVT scope justification，说明 cross-modal distillation 与 efficient visual computing 的关联。
- **Table 2 列标题修复（Typog 2）**：`Positives` → `COVID-Pos.`；`Negatives` → `COVID-Neg.`。
- **Manifest 独立性确认（Minor 20）**：Section 4.1 新增段，明确三套 manifest 患者集合完全不相交。
- **KD 缩写词表（Minor 11/Typog 6）**：Section 3.1 开头新增 5 个缩写定义（KD / Logit KD / Same-modality KD / Plain cross-modal KD / Full JDCNet）。
- **O8 术语统一 + 版式前移整改（2026-05-05）**：`paper/main.tex` 中残留的 `cross-modality` 统一为 `cross-modal`；`tab:problem_scope` 从 Introduction 尾部前移到贡献段之前，并新增 `Discussion Preview` 小节把讨论性判断提前到 Section I；Datasets 小节中的 BIMCV next-cohort 说明迁移到 `Limitations and Future Work` 的 Data 段；主文固定 split 表由 `\resizebox` 改为 `\small + tabularx`，主 resampling 表改为 `sidewaystable`，Windows 侧 `paper/build.bat` 重新编译通过；[main.tex](c:/source/JDCNET/paper/main.tex) 编辑器诊断为无错误。
- **主文 Minor 行级改写包收口（2026-05-05）**：`paper/main.tex` 中将 "computer-aided diagnosis systems" 改为更中性的 "automated thoracic classifiers"，将 "currently supported by the data and implementation" 改为 "supported by the available paired evidence"；把 Abstract、Experimental Protocol、Table IV/common-support 行和 Figure 2 caption 中的 resampling validation support 统一为"每个 resample 固定 1 个 negative，positive 为 4--9，验证总数为 5/6/6/6/7/7/7/8/8/10"，与 appendix `tab:resample_support` 对齐；Conclusion 压缩为 evidential-floor 结论，减少与 Discussion Preview 的重复；修复固定 split `tabularx` 环境结尾与主 resampling 表 caption/support 文案，`paper/build.bat` 重新编译通过（main 24 页，appendix 12 页）。
- **Figure/Cross-ref/CLAIM 写作收口（2026-05-05）**：`paper/main.tex` 中将 Figure 1 重画为多基线 primary evidence map（`paper/figs/baseline_evidence_map.png`），原始架构图已按要求备份为 `paper/figs/jdcnet_architecture.png_.bak`；`tab:hypothesis_status` 已前移并升格为 Introduction 中的 paper-level claim-status summary；`paper/appendix.tex` 中原 `tab:module_ablation` 5 行表已改为 delta 图式说明（`fig:module_ablation_summary` / `paper/figs/module_ablation_delta.png`）；附录新增 CLAIM-style reporting checklist（`tab:claim_checklist`）并补入 `mongan2020claim` 参考文献；`paper/build.bat` 重新编译通过（main 24 页，appendix 12 页），仅保留既有 appendix power-analysis table overfull 风险。
- **Table 5/6 边界整改（2026-05-05/06）**：`paper/main.tex` 中 `tab:real_results`（Table 5）已放入 0.92 `\textwidth` 的 `minipage`，Role 列改为 `tabularx` 的 `X` 列，common-support 跨列表行改为定宽可换行单元，修复右侧边界与长行溢出；`tab:resampling_main`（Table 6）按作者偏好取消 `landscape` 单独横页，恢复为普通 `table*` 双栏宽表，使用 `minipage + tabularx + \tiny` 和可换行 common-support 行在竖页内显示；`paper/build.bat` 重新编译通过，已抽取 PDF 第 8/9 页确认 Table 5 边界闭合、Table 6 无 `landscape` 且按列内换行显示，未引入新的主文表格 overfull。
- **Appendix Table 24 / Fig. 12 空间整改（2026-05-06）**：`paper/appendix.tex` 中 `tab:power_analysis` 已从单栏长 `tabular` 改为双栏 `table* + tabularx`，缩短并换行表头，修复 “Closed-form power table (E9)” 覆盖正文的问题；Fig. 12 reliability diagram 已改用按方法族叠加的三面板 grouped 图（`paper/figs/covid_calibration_reliability_grouped.png`），原 11 面板图保留并备份为 `paper/figs/covid_calibration_reliability.png_.bak`；补齐本地 r09/r10 resampling manifest 后重新生成 calibration 图，保持 `n=70` 与正文一致；`paper/build.bat` 编译通过，日志无 Table 24 相关 overfull，已抽取 appendix PDF 第 8/10/11 页确认图表未覆盖正文。
- **Appendix AUC 一致性说明（Minor 13）**：Table A2 caption 新增说明：固定 split 用 ROC-AUC，主文 resampling table 用 PR-AUC，并解释 seeds 42/43 结果相同不是复制粘贴错误。
- **Category-level cross-source non-COVID control 实验（M3 回应）**：下载 NORMAL CXR 1583 张 + normal CT 215 张；运行 `run_noncovid_controls.py`；结果 sensitivity=1.0、specificity 均值 0.00–0.32（distribution shift 确认）；附录新增 Table A3 + subsection；主文 Limitations "Data" 段引用 Table A3。同行评审 M3 以 category-level control + distribution shift 证据作为当前数据规模下的最终回应，更大 paired cohort 仍是下一轮实验前提。
- **标题再次重命名（2026-05-03）**：`CT-to-X-ray Knowledge Distillation Under Patient-Level Paired Cohorts: An Evidence-Bounded Evaluation Framework` → `JDCNet: Cross-Modal CT-to-X-ray Knowledge Distillation with Evidence-Bounded Evaluation on Patient-Level Paired Cohorts`；`paper/main.tex` `\title` 与 `\markboth` 同步；`docs/cover_letter.txt` 标题行同步。
- **Code Ocean capsule 公开（2026-05-03）**：`https://codeocean.com/capsule/6030764/tree`；`paper/appendix.tex` 新增 `A.1 Code and Data Availability` 子节（含 `\url{}` 渲染、capsule 内容描述）；`paper/main.tex` Contributions bullet 与 Implementation/Reproducibility 子节通过 `\ref{sec:code_availability}` 双向闭环；`docs/cover_letter.txt` Reproducibility artefact 段与 manuscript details `Code/data` 行同步 capsule URL；`paper/main.tex` 启用 `\usepackage{url}`、`paper/appendix.tex` standalone preamble 同步加入 `\usepackage{url}`。
- **实验侧追加（2026-05-03，回应 revision_suggestions.tex E5/E7/E8/E9/M1/M5/M9）**：基于已完成的 10-resample 实验产物（`src/runs/covid_resampling/` 11 方法 × 10 splits）追加六项分析，无需重新训练：
  - **E7 Robust statistical reporting**：新增 `src/jdcnet_exp/robust_stats_report.py`，对每个方法按 balanced accuracy / macro-F1 计算 median + IQR + 95% bootstrap CI（BCa 优先，degenerate 时回退至 percentile bootstrap，并以 `\ddagger`/`\dagger` 在表中标记）；`appendix.tex` 新增 `A.5 Robust Statistical Reporting` 子节（`tab:robust_stats`），替代旧的 mean±SD 解读，明确说明 $n_{\text{neg}}=1$ 下 SD 退化为单 Bernoulli draw 的二项展宽。
  - **E8 / O6 Rank stability**：脚本计算 fixed-split matrix 与 10-resample 之间的方法排名对应；Spearman $\rho=0.625$、Kendall $\tau=0.571$；`appendix.tex` 新增 `A.6 Rank Stability Across Evaluation Regimes`（`tab:rank_stability`）。
  - **E5 Convergence diagnostics**：脚本聚合 110 份 `history.csv`，画八方法 × mean ± IQR-band 的 train_loss / val balanced_accuracy 双面板图；新增 `paper/figs/covid_resampling_convergence.png` 与 `appendix.tex` `A.7 Training Convergence Diagnostics`（`fig:resampling_convergence`）；明确收敛在 ~30 epoch，否决"under-training artefact"备择解释。
  - **E9 Power analysis**：闭式 sign-test 功效表（$n_{\text{val}} \in \{20, 30, 50, 80\}$），给出 critical $k$、最小可检测 $P(\Delta>0)$、近似 balanced-accuracy gap；`appendix.tex` 新增 `A.17 Power Analysis for the Next-Cohort Experiment`（`tab:power_analysis`），把 BIMCV 50 患者的 minimum decisive 论断量化。
  - **M9 Distillation loss code listing**：`appendix.tex` 新增 `A.14 Distillation Loss Reference Implementation`，逐字嵌入 `src/jdcnet_exp/distillation.py` 的 `distillation_loss`，并交叉引用 `train.py` 的 `teacher.eval()` + `with torch.no_grad():` 位置，确认 KL 方向 $\mathrm{KL}(p_T \,\|\, p_S)$ 与 PyTorch `F.kl_div(input=log\_p\_S, target=p\_T)` 实现一致、teacher 不参与梯度。
  - **M1 / M5 Deployment efficiency**：修复 `src/jdcnet_exp/efficiency_report.py`（输入通道数 1→3 与模型 stem 对齐），用 `fvcore.FlopCountAnalysis` 计 MACs，在 CPU-only WSL 上跑 4 配置；`paper/main.tex` 新增 `4.8 Deployment-Time Efficiency` 子节（`tab:efficiency`），覆盖 reviewer 关于 TCSVT 部署/效率叙事的 M1+M5 缺口；与 `tab:progressive_complexity` 区分了"训练时 teacher+student 总参数"与"部署时 student-only 参数"两种视图，量化指出 +DPE+MHRA+DFPN 让部署参数 6×、CPU 延迟 3.7×，进一步加固 H4 否定。
  - **附带订正**：`tab:implementation_details` 中 `Epochs & 5` 与实际训练（50 epochs，history.csv 共 50 行）不符，更新为 `50 (early-stopping on validation balanced accuracy; convergence reached by ~30 in every method)`。
  - **paper preamble**：`appendix.tex` standalone preamble 加入 `\usepackage{multirow}` 与 `\usepackage{amsmath}` 以支持新表的 `\multirow` 与 `$n_{\text{neg}}$` 数学排版；main 与 appendix 双双重新编译（main 21 页、appendix 10 页）。
- **未做（仍需 GPU 或新数据，沿用既有 deferred 项）**：
  - E1 BIMCV-COVID19+ headline 整合（仍需在 H800 上完成 BIMCV 阴性 same-patient 配对；目前仅准备好 manifest）。
  - E3 ImageNet/RadImageNet 预训练 + cosine LR（Task #19）。
  - E4 BiomedCLIP frozen-feature baseline（Task #20）。
  - E6 校准（reliability diagram + ECE + Youden-J）：当前只有 fixed-split 6 个 group 的 `covid_control_val_probabilities.csv`，resampling cohort 需要从 `best.pt` 重新评估输出概率，待 GPU 环境就绪后补。
  - E10 非医学跨模态示范（如 RGB↔depth）：需引入额外数据集，规划留待下一次大改。
- **M8 환境 pinning（2026-05-04 追加）**：`paper/main.tex` Implementation and Reproducibility 段新增一句明确说明：pinned `requirements.txt` 与 Docker image 在 Code Ocean capsule 内；所有实验均以 `torch.use_deterministic_algorithms(True)` 和 `torch.backends.cudnn.benchmark = False` 执行。M8 主项完全关闭。- **M3/Cls 叙事统一及 Section III 重组（2026-05-05 完成）**：
  - 所有 "Proposed-module test" 改为 "Reproducible-ablation test"（Table III 行标签 + Tier 3 标题 + 正文三处）。
  - Section III 从 "Problem Formulation" 拆分为两个子节："Notation and Glossary"（缩写定义表）+ "Task Formulation"（任务形式化）。
  - Related Work 新增段落补充 BiomedCLIP~\cite{zhang2023biomedclip}、MedCLIP~\cite{wang2022medclip}、RadImageNet~\cite{mei2022radimagenet} 的讨论，解释为何这些基础模型不直接适用于当前的 training-only cross-modal 设定。
  - 所有引文补齐：BiomedCLIP 2023、MedCLIP 2022、RadImageNet 2022、Demšar 2006、Benavoli 2017 均已在 ref.bib 中。
- **M6 per-resample 支持统计表（2026-05-04 追加）**：`paper/appendix.tex` 新增 `A.5 Per-Resample Validation Support` 子节（`tab:resample_support`），列出 r01–r10 的 train/val $n_+$/$n_-$（train: $n_+=13$–$18$, $n_-=3$ fixed；val: $n_+=4$–$9$, $n_-=1$ fixed，mean val total=7.0）。直接回应 reviewer 明确要求的"显式 $n_{\text{pos}}/n_{\text{neg}}$ 表"。M6 相关子项关闭。
- **BIMCV-neg 下载脚本（2026-05-04 追加）**：新增 `src/jdcnet_exp/download_bimcv_neg_paired.py`，对应 BIMCV-COVID19- 四部分 Kaggle 数据集，枚举配对 CT+CXR subject 并选择性下载，结构与 download_bimcv_paired.py 对齐；产出 `sub-S*/ct/` + `sub-S*/cxr/` 结构。
- **BIMCV-neg manifest 脚本（2026-05-04 追加）**：新增 `src/jdcnet_exp/prepare_bimcv_neg_dataset.py`，调用 `build_paired_manifest(..., label=0)` 生成 `src/data/bimcv/bimcv_neg_manifest.csv`；支持 `--merge-with` 与正例 manifest 合并，自动重新分配 train/val splits。
- **NLST manifest 脚本（2026-05-04 追加）**：新增 `src/jdcnet_exp/prepare_nlst_dataset.py`，支持 CSV manifest 驱动（nlst_prsn.csv + nlst_screen.csv）和目录扫描双路径；通过 pydicom 提取中间轴向切片；二元标签为肺癌 year-1 诊断；支持 `--dry-run` 在 DICOM 下载前估计配对样本量。
- **H800 GPU 就绪确认（2026-05-04）**：smoke_test.py 9/9 PASS 已在上轮验证完成。**H800 GPU 现可开启**。
- **PDF 重新编译（2026-05-04）**：main.pdf 23 页（M8 环境句 + 附录 tab:resample_support）；appendix.pdf 10 页。
- **Abstract prevalence 句增加（2026-05-04）**：在 Abstract 第 2 句添加"validation: 1 negative, 3 positive per resample"，直接回应 reviewer Minor 15。- **M6 per-resample 支持统计表（2026-05-04 追加）**：`paper/appendix.tex` 新增 `A.5 Per-Resample Validation Support` 子节（`tab:resample_support`），列出 r01–r10 的 train/val $n_+$/$n_-$（train: $n_+=13$–$18$, $n_-=3$ fixed；val: $n_+=4$–$9$, $n_-=1$ fixed，mean val total=7.0）。直接回应 reviewer 明确要求的"显式 $n_{\text{pos}}/n_{\text{neg}}$ 表"。M6 相关子项关闭。
- **BIMCV-neg 下载脚本（2026-05-04 追加）**：新增 `src/jdcnet_exp/download_bimcv_neg_paired.py`，对应 BIMCV-COVID19- 四部分 Kaggle 数据集，枚举配对 CT+CXR subject 并选择性下载，结构与 download_bimcv_paired.py 对齐；产出 `sub-S*/ct/` + `sub-S*/cxr/` 结构。
- **BIMCV-neg manifest 脚本（2026-05-04 追加）**：新增 `src/jdcnet_exp/prepare_bimcv_neg_dataset.py`，调用 `build_paired_manifest(..., label=0)` 生成 `src/data/bimcv/bimcv_neg_manifest.csv`；支持 `--merge-with` 与正例 manifest 合并，自动重新分配 train/val splits。
- **NLST manifest 脚本（2026-05-04 追加）**：新增 `src/jdcnet_exp/prepare_nlst_dataset.py`，支持 CSV manifest 驱动（nlst_prsn.csv + nlst_screen.csv）和目录扫描双路径；通过 pydicom 提取中间轴向切片；二元标签为肺癌 year-1 诊断；支持 `--dry-run` 在 DICOM 下载前估计配对样本量。
- **H800 GPU 就绪确认（2026-05-04）**：smoke_test.py 9/9 PASS 已在上轮验证完成。**H800 GPU 现可开启**。
- **PDF 重新编译（2026-05-04）**：main.pdf 23 页（M8 环境句 + 附录 tab:resample_support）；appendix.pdf 10 页。
- **Abstract prevalence 句增加（2026-05-04）**：在 Abstract 第 2 句添加"validation: 1 negative, 3 positive per resample"，直接回应 reviewer Minor 15。
- **Venue 战略决策（2026-05-03 消化）**：保持 IEEE TCSVT 正刊，按 conservative evidence-bounded protocol paper 投。叙事聚焦正向子发现（Logit KD 为最优 KD 方式、non-COVID distribution shift 检出、reproducible protocol scaffold）。DPE/MHRA/DFPN 保留为探索性模块但不作 headline positive claim。Cls. 中关于 venue 切换的子项关闭；M3 叙事调整（命名模块同时 disclaim 的矛盾）仍需处理，方向是改写为"reproducible ablation targets"而非"proposed method components"。
- **Pres. PNG → PDF（2026-05-03 消化）**：作者决定保留 PNG，不做矢量图格式转换。该项关闭。

## 未修改或部分修改

> 本节按 `docs/revision_suggestions.tex` 的章节编号（M = Major, O = Moderate, E = New experiments, Pres. = Presentation, Eth. = Ethical, Cls. = Closing）系统化对照当前 `paper/main.tex` 与 `paper/appendix.tex` 状态。"PARTIAL" 表示在主线方向已动手但 reviewer 列出的子项仍有缺口；"NOT DONE" 表示尚未着手。

### A. 可立即写作闭环（不依赖新数据/GPU）

- **M3 / Cls. 叙事矛盾 — PARTIAL**：统一 Section 3–4 对 DPE/MHRA/DFPN 的定性为"reproducible ablation targets"，清除"proposed method components"暗示。
- **O2 threshold sweep 叙事补齐 — PARTIAL**：E6 已有 calibration + Youden-J；补 prevalence-matched argmax 指标行并统一到主表叙事。
- **O5 Related-work 写作补齐 — PARTIAL**：补 reviewer 点名文献与 2022–2024 cross-modal medical distillation 讨论。

### B. 需外部资源（GPU/新数据/新实验）

- **M1 Venue fit (TCSVT) — PARTIAL**：仍缺 GPU latency、embedded/edge 测量、video-temporal 维度、coding/compression 视角证据。
- **M2 Sample size — PARTIAL**：仍缺 BIMCV 折入 headline tables、paired non-COVID arm、≥30 resamples 且 $n_{\text{neg}} \geq 5$。
- **M4 Baseline coverage — PARTIAL**：仍缺 Gupta 2016 named baseline、MedCLIP/GLoRIA frozen-feature、CheXNet/ConvNeXt-Tiny same-modality teacher 实验。
- **M5 Architecture practice gap — PARTIAL**：仍缺 cosine LR + warmup、224×224 训练、RadImageNet 对比、10-resample 统计。
- **M10 Single dataset — NOT DONE**：仍缺第二独立 thoracic dataset 的完整同协议结果。
- **E1 BIMCV-COVID19+ headline integration — NOT DONE**：待 same-patient 阴性配对与训练落地（Task #23）。
- **E3 ImageNet/RadImageNet + cosine LR — PARTIAL**：ImageNet 4 seeds 已完成；仍缺 cosine/warmup、224 训练、RadImageNet、10-resample。
- **E10 Non-medical paired-modality demo — NOT DONE**：需引入新数据集并运行额外实验。

## 排期清单（可直接执行）

### 1) 本周可完成（写作闭环）

- [ ] **M3/Cls 叙事统一包**：将 Section 3–4 中 DPE/MHRA/DFPN 统一改写为 "reproducible ablation targets"，删除/替换所有 "proposed method components" 暗示。
- [ ] **O2 主表叙事补齐**：把 prevalence-matched argmax 指标行并入主表体系，并与 E6 的 calibration + Youden-J 结果一致引用。
- [ ] **O5 引文与段落补齐**：补 reviewer 点名文献（含 2022–2024 cross-modal medical distillation）并更新 Related Work 讨论。

### 2) GPU窗口期执行（实验项）

- [ ] **E1 / M2 / M10**：在 BIMCV 完成 same-patient 阴性配对后，跑 headline integration（Task #23）并回填主文 headline tables。
- [ ] **M1 效率证据补齐**：补 GPU latency 测量（与 CPU latency 同口径），形成 TCSVT 叙事闭环证据。
- [ ] **M4 baseline 扩展**：补 Gupta 2016 named baseline、MedCLIP/GLoRIA frozen-feature、CheXNet/ConvNeXt-Tiny same-modality teacher。
- [ ] **M5 / E3 扩展**：补 cosine LR + warmup、224×224 训练、RadImageNet 权重对比，并进入 10-resample 统计。
- [ ] **E10**：若资源允许，新增非医学 paired-modality 演示实验（独立数据集 + 同协议）。

### 3) 数据申请并行推进（NLST/MIDRC）

- [ ] **NLST（主线）**：
  - 在 TCIA 提交/确认 NLST 访问权限。
  - 配置 NBIA Data Retriever 并完成首批下载。
  - 执行 `python -m jdcnet_exp.prepare_nlst_dataset --nlst-root /data/nlst --output-dir src/data/nlst`。
  - 产出 dry-run/正式样本量统计并登记到进度日志。
- [ ] **MIDRC RICORD（备线）**：
  - 提交访问申请（预估 1–2 周）。
  - 申请获批后制定最小可运行配对筛选方案（仅作为 BIMCV 风险兜底）。
- [ ] **BIMCV-neg 数据落地**：
  - 执行 `python -m jdcnet_exp.download_bimcv_neg_paired --output-dir /data/bimcv_neg_paired`。
  - 执行 `python -m jdcnet_exp.prepare_bimcv_neg_dataset --bimcv-root /data/bimcv_neg_paired --output-dir src/data/bimcv`。
  - 将产出的 manifest 与 E1 训练计划绑定（记录可用样本量与 split 可行性）。

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

## 遗留问题

> 这些不是写作层面就能闭环、需要外部资源（GPU 时间、新数据、数据集研究）。

### A. 可立即写作闭环

- 当前无（遗留问题均依赖外部资源执行）。

### B. 需外部资源（GPU/新数据/数据访问）

1. **BIMCV-COVID19- same-patient negative 下载与 manifest 准备（结构性阻塞 M2 / M10 / E1）**：
   - **推进状态**：PARTIAL — 方向与脚本已就绪（作者 A: 优先在 BIMCV 内过滤 COVID-neg pneumonia paired CT）。`src/jdcnet_exp/download_bimcv_neg_paired.py` 和 `src/jdcnet_exp/prepare_bimcv_neg_dataset.py` 已创建；待执行下载与 manifest 生成。
   - **MIDRC RICORD**：备选，申请制访问，申请约 1–2 周。
   - 下步（H800 GPU 上）：`python -m jdcnet_exp.download_bimcv_neg_paired --output-dir /data/bimcv_neg_paired` → `python -m jdcnet_exp.prepare_bimcv_neg_dataset --bimcv-root /data/bimcv_neg_paired --output-dir src/data/bimcv`

2. **额外 thoracic dataset（M10）**：
   - **推进状态**：PARTIAL — 方向与脚本已就绪（作者 A: NLST 作为第二 thoracic dataset）。`src/jdcnet_exp/prepare_nlst_dataset.py` 已创建；待完成 NBIA 数据下载并跑同协议实验。
   - 下步：(a) 在 TCIA 申请 NLST 访问并配置 NBIA Data Retriever；(b) 运行 `python -m jdcnet_exp.prepare_nlst_dataset --nlst-root /data/nlst --output-dir src/data/nlst`；(c) 按同一 10-resample 协议跑 NLST 上的 plain cross-modal logit KD baseline。

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
