# 进度

## 510 cohort F3 重跑准备（无卡模式，自动执行，2026-06-26 凌晨）

**目标**：在 510 headline cohort（不是 paired-216）上重跑 calibrated_gate，使 F3 温度消融可与正文 headline 直接可比。

**关键发现（为什么之前只有 216/228）**：
- 不是数据不够。H800 已有完整原始数据：`data/bimcv_paired`(17G,阳性 CT.nii+X光)+`data/bimcv_neg_paired`(49G,阴性),`bimcv_paired`/`bimcv_neg_paired` 是软链。**455 个病人有原始 `.nii`**(阳 101 + 阴 354);源 manifest `data/bimcv/bimcv_merged_paired_manifest.csv` 含 512 病人(398−/114+ = 510 cohort)。
- **228 的真因**：`prepare_bimcv_only_cv.py --mode balanced`(默认)会把阴性下采样到 `negatives[:len(positives)]` = 114+/114− = 228。510 headline 是 **imbalanced**(113+/397−)。→ 重建时要用 **`--mode full`**。
- **216 的真因**：calibrated_gate 的 `student_manifest` 要求 CT 教师**变体**图 `data/bimcv_ct_variants/bimcv_ct_{mid,3slice}/bimcv_S*.png` 存在,而变体只渲染了 216/217。

**本夜已做（无卡 CPU）**：
- 把 CT 教师变体从 216 渲染到全部 455（用 `.nii` 已在 H800）。原 `extract_ct_teacher_variants.py` 用 `get_fdata()` 整卷载入,在某个大卷上被 OOM kill(rc=137);改用**省内存渲染器** `src/ops/render_bimcv_variants_frugal.py`(`nib...dataobj[:,:,idx]` 惰性取片,RSS~64MB,只渲 mid+3slice,跳过 calibrated_gate 不用的 proj),参数与原脚本一致(HU[-1000,400], size 224, 3slice gap=round(5mm/z_spacing))。H800 上脚本 `/root/autodl-tmp/render_frugal.py`,日志 `render_frugal.log`,汇总 `logs/render_frugal_summary.json`。
- 注意:无卡模式 RAM 其实有 1007G(867 空闲),OOM 是单个病态大卷的 `get_fdata` 所致,非总内存不足。

**恢复任务（需有卡 GPU 模式，按序）**：
1. 确认变体齐:`ls data/bimcv_ct_variants/bimcv_ct_3slice/|grep -c bimcv_S` 应 ≈455。若 render 未跑完,先 `nohup python render_frugal.py`(幂等,跳已存在)。
2. **重建 510 CV manifest（imbalanced）**:`CV_MODE=full TAG=bimcv_full510 bash src/ops/h800_bimcv_5fold_cv.sh --phase prep`（或直接 `python -m jdcnet_exp.prepare_bimcv_only_cv --bimcv-manifest data/bimcv/bimcv_merged_paired_manifest.csv --output-dir bimcv_cv/bimcv_full510 --prefix bimcv_full510 --folds 5 --seed <same as orig> --mode full`）。CV_MODE/TAG 见脚本变量。
3. GPU 训练:`bash src/ops/h800_bimcv_5fold_cv.sh`（teacher+supervised+KD,新 cohort）→ 再 `bash src/ops/h800_calibrated_gate.sh`（指向新 CV_DIR + 新 SUP_RUN_ROOT），20-way+MPS 加速见 [[feedback-h800-ops-gotchas]]。
4. 用 `src/results/.../analyze_calib.py`（scratchpad 有副本）重算 within-cell ΔBA,与 paired-216 对比;若 510 上温度敏感性结论变化,更新 paper F3 段（当前写的是 within-cell ≤0.013 不敏感）。
5. 预期:510 上各 cell 绝对 ΔBA 可能恢复到 +0.03 附近（headline），温度不敏感性大概率保持。

**待用户**：H800 重开有卡模式后执行上述；F3 paper 措辞是否因 510 结果调整。

## H800 全数据重跑：A2/A3 完成、A4 待修、F3 实证为 null（2026-06-25）

**计算环境**：H800 重新可达（`ssh -p 12437 root@connect.westc.seetacloud.com`），单 GPU 0。本轮把 8-way 加速到 **20-way + CUDA MPS**（显存 28→71.5GB/80GB，吞吐 ~2.5×）。代码同步方式：本地改 → git push → H800 git pull。

### A2/A3 calibrated gate（关 F3）= 已完成，结果为 null / robustness（非"校准提升"）
- Run tag `bimcv_h800_calibrated_gate`，**90/90 完成，0 真实 FAIL**。两 pass cell（`3slice_soft` τ0.70 λ1.0 soft-KL、`mid_hard` τ0.80 λ1.5 hard）× teacher 门控温度 **T∈{0.5,1.0,2.0}**（0.5=过自信、1.0=未校准原版、2.0=软化/趋校准）× 5 折 × 3 seed。
- 指标用 **val（`best_metrics.json`）**，与 5fold/正文方法一致（5fold 各 run 无 test_eval）。supervised 同 cohort/折 val BA=0.6976、AUC=0.7104；teacher BA=0.7105。
- **核心发现（不修饰）**：
  1. **F3 校准敏感性 = null/稳健**：每个 cell 内三档温度统计上无法区分（cell 内 |ΔBA|≤0.013，全在噪声内；SD 0.04–0.10）。过自信(T=0.5)不损害、软化(T=2.0)不提升 → **门控对 teacher (mis)calibration 稳健**。正实证了正文 Limitations 现有预测（main.tex L555：校准"expected to stabilize, rather than overturn, the gate decision"）。
  2. **cohort 注意**：本轮在 paired-216 子集（CT+X光都在的病人），**非 510 headline cohort**。该子集上两 cell 都没复现 +0.0345/+0.0329：`3slice_soft` 显著为负（≈−0.09，CI 不含 0）、`mid_hard` 为 null（≈−0.018，CI 含 0）。这是 cohort 变小所致，非校准问题，**不推翻 510 headline**（不同 cohort），但温度消融须以 robustness check 报告并明示 cohort 差异，不能当作 headline ΔBA 的重算。
- 结果落盘：`src/results/bimcv_h800_calibrated_gate_20260625/`（`summary.csv` + `decision_report.md` + `aggregate_{val,test}.txt`）。分析脚本 `analyze_calib.py`（H800 `/root/autodl-tmp/`，本地副本在 scratchpad）。

### A4 external X-ray 推理（关 F1，最大风险）= 已修复并完成
- orchestrator 首跑 60 job 全 FAIL，根因：`h800_external_eval.sh` 生成 config 用 `train_split='train'`，但外部 manifest 只有 `split=test` 行 → `evaluate.py` 构建（随后丢弃）的 train loader 为空 → `ValueError: Training manifest is empty`。
- **已修**：`src/ops/h800_external_eval.sh` line 90 `train_split` 改为 `os.environ['EXT_SPLIT']`（本地已改；H800 用 sed 直接 patch 后重跑，因 H800 working copy 落后且有本地编辑，未走 git pull 以免冲突——本地需 commit 入库）。重跑 **60/60 完成**。
- **F1 结果（外部 MIDRC X 光，不修饰）**：所有模型**全部塌到随机**——supervised BA 0.492/AUC 0.486、jdcnet_3slice_softkl BA 0.498/AUC 0.509、jdcnet_mid_hard BA 0.494/AUC 0.477，三者互相无法区分。BIMCV 训练的 X 光分类器对外部域**零迁移**。这是对 F1 最直接的回答：跨域泛化对**所有模型**失败（任务/cohort 属性，非 JDCNet 特有），正面坐实审稿人 dataset-specific-bias 担忧，且契合论文 evidence-bounded-negative 基调。
- **注意（headline 前须核）**：supervised 也完全塌到随机，既可能是真实 domain shift（BIMCV 西班牙 vs MIDRC 美国），也可能外部 manifest 的 label 映射/预处理不一致——数值入正文前先 sanity check 外部 manifest 标签；定性结论（无跨域迁移）稳健。summary 里 sensitivity 列空 = 聚合 key 与 per-run `recall` 不符，需要时从 raw 重算。
- 结果落盘：`src/results/h800_external_eval_20260625/`（`external_summary.csv` + `decision_report.md`）。全部 raw metric json 备份在 `src/results/metrics_backup_20260625.tgz`（273 文件，checkpoint 释放后仍可复算）。

### H800 释放
- 用户示意"运行完暂不使用"。A2/A3 + A4 全部完成，所有指标/汇总/raw json 已拉回本地（含备份 tgz），**H800 上不再有未取数据，可安全释放/停机**。checkpoint 释放后丢失，但实验已完成、无需复算。

### 拒稿三点最新解决状态（2026-06-25）
- **F2（缺绝对指标）= 已解决**：正文 `tab:app_absolute_metrics` + 摘要绝对 BA/AUC（前轮）。
- **F3（teacher gate 未校准）= 实证完成，结论为 null/稳健**：A2/A3 已跑，证明门控对温度不敏感、过自信不破坏 student。可把正文/Limitations 的"proposed safeguard / expected to stabilize" 升级为"已做消融，gate 对 teacher 温度统计不敏感"。**待用户确认**：cohort 定位（paired-216 robustness check + 注脚 vs 在 510 cohort 重跑，后者需 510 数据在可达 GPU）。
- **F1（单 cohort、无 cross-domain）= 已有实证（负向）**：A4 完成，外部 MIDRC X 光上 supervised 与 JDCNet 全部 ≈ 随机（BA≈0.49，AUC≈0.49）。直接证明无跨域泛化（所有模型皆然），可把 Limitations 从"仅承认"升级为"已做外部验证并报告负向结果"，强化 evidence-bounded 框架。须先 sanity check 外部 manifest 标签后再把数值写正文。

### 待办
- [x] 修 `src/ops/h800_external_eval.sh`（train_split=test）→ 重跑 A4（F1）= 完成（本地已改，需 git commit 入库）。
- [ ] **git commit** 本地改动：`src/ops/h800_external_eval.sh`（A4 fix）、`src/results/`（A2/A3 + A4 结果与备份）、`docs/progress.md`。
- [ ] 用户决定 F3 在论文中的 cohort 定位（paired-216 robustness check + 注脚 vs 510 重跑）。
- [ ] sanity check A4 外部 manifest 标签/预处理（确认 supervised 塌到随机是真实 domain shift 而非 label bug）。
- [ ] 按两份 decision_report 把 F3（calibration ablation）+ F1（external validation）写入 paper（Methods/Experiments/Limitations），Windows `paper/build.bat` 重编。
- [x] H800：A2/A3 + A4 完成，指标全部拉回本地（含 `metrics_backup_20260625.tgz`），**可安全释放**。

## 拒稿点复核 + venue 定为 TOMM + 下一步计划（2026-06-23）

- **目标 venue 确认为 ACM TOMM**（用户本轮再次确认）。`USAGE.md` 第 33 行已从
  IEEE TCSVT 改为 ACM TOMM；`paper/main.tex` 本就是
  `\documentclass[manuscript,screen,review,anonymous]{acmart}` + `\acmJournal{TOMM}`
  双盲，格式一致。**14 页 TCSVT 约束作废**（TOMM 期刊无页数上限）。
- **三条拒稿点（F1/F2/F3，见 `docs/revision_suggestions.tex` / `docs/revision_roadmap.md`）
  对照 `paper/combine.pdf` 现状**：
  - **F2（缺绝对指标）= 已解决**：正文有 `tab:app_absolute_metrics`
    （baseline BA .604/AUC .661 → JDCNet 3-slice .639/.701）；本轮已把绝对 BA/AUC
    补进**摘要**（`main.tex` line 92）。
  - **F3（teacher gate 未校准）= 仅论证性解决**：有 ECE 诊断（§415）、分组可靠性图
    （`fig:calibration_reliability`）、Limitations 提出 temperature-scaling safeguard，
    但 **A2 calibrated-gate / A3 overconfidence ablation 实验从未跑过**。
  - **F1（单 cohort、无 cross-domain）= 未解决（最大风险）**：仅在 Limitations 承认，
    并给出 cross-source control（specificity≈0）作为反例；**A4 外部 X-ray 推理 /
    B1 外部 paired cohort 从未跑过**。
- **阻塞**：3090（`10.147.20.176:22`）与 H800（`connect.westc.seetacloud.com:12437`，
  DNS→`116.172.66.186`）本轮实测**均不可达**，依赖 GPU 的 A2/A3/A4 暂时无法运行。
  脚本与代码均已就绪。

### 下一步计划（未完成项 — 按优先级）

- [ ] **P0-a｜重新编译论文（Windows）**：跑 `paper/build.bat`，确认摘要绝对指标改动
      生效、无 undefined 引用/引文；产出 `main.pdf` / `combine.pdf`。WSL 无 pdflatex，
      必须在 Windows 端完成。
- [ ] **P0-b｜恢复可达 GPU**：重新拉起 H800 实例并记录新的 `host:port`，或等 3090
      ZeroTier 链路恢复。验收：`bash src/tmp_sync/ssh3090.sh 'hostname; nvidia-smi'`
      （或对应 H800 命令）成功。这是 F1/F3 实证的唯一卡点。
- [ ] **P1-a｜A4 外部 X-ray 推理（关 F1，最高优先）**：GPU 可达后运行
      `src/ops/remote_3090_external_eval.sh`，冻结学生在外部 X-ray manifest 上只推理，
      汇总绝对 BA/AUC/F1/sens/spec + bootstrap CI（inference-only，<0.5h）。
      把结果写进 Experiments 的 external-validation 段，替换当前"仅承认局限"的表述。
- [ ] **P1-b｜A2 calibrated gate + A3 overconfidence ablation（关 F3）**：运行
      `src/ops/remote_3090_calibrated_gate.sh`，两个 pass cell × T∈{1.0,0.5,2.0} ×
      5 折 × 3 seed = 90 runs（~3h）。把"提议的 safeguard"升级为"做过的 ablation"，
      正文补 calibrated-gate 结果 + 对比表。
- [ ] **P2｜（若数据可得）B1 外部 same-patient paired CT–X-ray cohort 重跑完整 gate**：
      `src/` 下已有数据下载脚手架，先调研可得性；这是对 F1 最强的正面回应。
- [ ] **P3｜论文整合与定稿**：A4/A2/A3 结果回填后，更新 Abstract / Methods（Calibration
      Safeguard）/ Experiments（external + calibration ablation）/ Limitations；同步
      `docs/cover_letter.txt`（已是 TOMM 版）逐条回应 F1/F2/F3；重新编译复核。
- [ ] **P4｜（可选，若改投会议）抓官方 CFP**：WACV 2027 Applications track 框架最契合，
      截稿约 2026 年 7–8 月，需 WebSearch 抓官网确认日期并改回会议格式。当前默认留在
      TOMM（无截稿压力）。

## paper/ 目录整理（2026-06-16）

- **拆分脚本归位**：`paper/split_main.ps1` 移入 `paper/build/split_main.ps1`，保持
  paper 根目录干净；`build.bat` 改为调用 `%BUILD_ROOT%\split_main.ps1`；脚本内路径
  改为以 `$PSScriptRoot`（=build/）的父目录为 paper 根、`main.aux` 在 build/；
  `paper/.gitignore` 增加 `!build/split_main.ps1` 例外（build/* 默认被忽略）。
- **附录单一源**：`appendix_body.tex` 内容合并进 `paper/appendix.tex` 并删除
  `appendix_body.tex`。`appendix.tex` 用 `\ifdefined\JDCappendixincluded` 守卫
  preamble/title/`\end{document}`：独立编译时走完整文档；被 `main.tex` 以
  `\def\JDCappendixincluded{}\input{appendix}` 引入时只输出正文，combine 原生解析
  全部交叉引用。根目录 .tex 仅剩 `main.tex / appendix.tex / title_page.tex`。
- **复核通过**：main 23 页、combine 27 页、appendix 4 页，无 undefined 引用/引文。

## A2/A4 实验脚本就绪 + 远端不可达 + 构建告警修复（2026-06-16）

- **构建告警根因修复**：`main.pdf` 拆分原用 poppler `pdfseparate`+`pdfunite`，在
  acmart/hyperref 的"recursive dicts"结构上会逐页重复解析，导致刷屏的
  `Syntax Warning: Found recursive dicts` 并使 `pdfseparate` 卡死/拖慢构建（多次
  残留僵尸进程）。改用单遍 `pdftocairo -pdf -f 1 -l N`（约 1.7s、零告警、扁平化结构），
  `pdfseparate`+`pdfunite` 仅作 fallback；`build.bat` 保留 `findstr /V` 过滤兜底。
  重新构建通过：main 23 页、combine 27 页、appendix 4 页。
- **A2 calibrate-then-gate 代码支持**：`jdcnet_exp/train_pseudolabel.py` 的
  `PseudoLabelConfig` 新增 `teacher_temperature`，置信度 mask 改为对
  `softmax(teacher_logits / T)` 取 max（argmax 目标不变；T=1 复现原始、T>1 软化/更校准、
  T<1 过自信）。
- **发射脚本就绪**（按既有 `remote_3090_bimcv_pseudolabel_cv.sh` 脚手架编写，`bash -n` 通过）：
  - `src/ops/remote_3090_calibrated_gate.sh`：A2+A3，仅两 pass cell ×
    温度 {1.0,0.5,2.0} × 5 折 × 3 seed = 90 runs，4×3090，screen+xargs。
  - `src/ops/remote_3090_external_eval.sh`：A4，冻结学生在外部 X-ray manifest 上
    只推理，汇总绝对指标（均值±SD）。
- **远端 3090 当前不可达**：`mabo1215@10.147.20.176` ping 100% 丢包、ssh "No route
  to host"（ZeroTier 链路或主机离线），**无法立即运行实验**。脚本与代码已就绪，
  待链路恢复后一条命令即可发射。

## main/combine 拆分与正文恢复至 23 页（2026-06-16）

- **PDF 结构调整**：`paper/main.pdf` 现在只含正文+参考文献（23 页，不含附录）；
  完整的"正文+附录"合订本输出为 `paper/combine.pdf`（27 页）；`paper/appendix.pdf`
  仍为独立附录（4 页）。
- **实现方式**：acmart 下 `\newlabel` 格式与 `xr`/手工注入都不兼容，main-only 无法
  在 LaTeX 内解析附录交叉引用。改为：`main.tex` 原生 `\input{appendix_body}` 生成
  合订本 → `build.bat` 复制为 `combine.pdf` → `paper/split_main.ps1`（PowerShell +
  poppler `pdfseparate`/`pdfunite`，本机无 python）读取 `\label{paper:appendixstart}`
  的页码，截取 1..(起始页-1) 写回 `main.pdf`。引用编号全部正确。
- **正文从 18 页恢复到 23 页**（TOMM 无页数上限）。从同谱系备份
  `backup/20260517_015930/main.tex` 恢复并新增：Related Work 的 "Transformers and
  Attention Mechanisms" 子节（+ViT/Swin 两条 bib）、更完整的 Knowledge Distillation
  段、"Data Availability and Ethics" 子节、扩写的 Limitations（新增 Reporting 与
  external-validation/calibration 段，呼应三条拒稿点）、Introduction 小样本评估
  协议段、Discussion 的 Calibration 与 "Relevance to cost-preserving multimedia
  inference systems" 段。把附录三张核心表（full JDCNet sweep、absolute metrics、
  gate coverage）上移到正文（绝对指标进正文同时回应 F2），并补 3 张图
  （seed instability、threshold sensitivity、grouped reliability diagrams）。
- **校验**：`build.bat` 通过，main 恰好 23 页；无 undefined 引用/引文；仅 1 处
  overfull box。`appendix_body.tex` 中被上移内容的引用已改写，独立 appendix.pdf
  无 undefined 引用。

## 目标期刊变更与 ACM 格式改造（2026-06-16）

- **目标 venue 变更**：由 IEEE TCSVT 改为 **ACM TOMM**（ACM Transactions on
  Multimedia Computing, Communications, and Applications）。已更新 `USAGE.md`
  的 `目标会议或期刊：...` 一行。
- **论文格式改造（`paper/`）**：`paper/main.tex` 与 `paper/appendix.tex` 从
  IEEEtran 全面改写为 **acmart**（`\documentclass[manuscript,screen]{acmart}`，
  ACM 期刊投稿要求的单栏 manuscript 格式）。
  - 题录元数据：`\acmJournal{TOMM}`、`\setcopyright`、CCS Concepts（`\ccsdesc`
    + CCSXML）、`\keywords`，参考文献样式改为 `ACM-Reference-Format`，
    `\bibliography{ref}`（移除 IEEEabrv）。
  - 作者块改为 ACM `\author/\affiliation/\email`；移除 IEEE 专用宏
    （`\IEEEPARstart`、`\markboth`、`\IEEEkeywords`、`\IEEEpeerreviewmaketitle`、
    `\ifCLASSINFOpdf`/`\ifCLASSOPTIONcaptionsoff`）及 IEEE biography 段落。
  - 正文中 "Positioning within TCSVT" 改为 "Positioning within multimedia
    computing"，"TCSVT-ready" 改为 "TOMM-ready"。
- **附录整合**：acmart 下 `xr/\externaldocument` 跨文档引用会触发
  "Missing number" 致命错误（acmart 的 .aux 与 xr 不兼容）。改为把附录正文抽到
  `paper/appendix_body.tex`，由 `main.tex` 在参考文献后用 `\appendix\input{appendix_body}`
  原生引入；`appendix.tex` 仍可独立编译（同样 `\input` 该共享正文）。所有
  附录交叉引用（如 `tab:jdcnet_510`）现已原生解析，无 undefined reference。
- **构建验证**：`paper/build.bat` 编译通过——`main.pdf` 23 页（正文+附录，ACM
  单栏 manuscript），`appendix.pdf` 6 页（独立附录）；无 undefined 引用/引文，
  仅 1 处 overfull box。TOMM 为期刊无硬性页数上限，23 页可接受。
- **双盲匿名化（2026-06-16）**：TOMM 为双盲评审。`main.tex` 与 `appendix.tex`
  documentclass 加入 `review,anonymous` 选项——作者名显示为 "Anonymous
  Author(s)"，affiliation/email/contact-info 与致谢自动隐藏，左侧加行号。正文中
  唯一可识别信息（GitHub 链接 `mabo1215/JDCNet`）改为 "repository URL withheld
  for double-blind review and provided to reviewers as anonymized supplementary
  material"。附录正文无可识别信息。
- **独立 title page（2026-06-16）**：新增 `paper/title_page.tex`（非匿名，单独
  上传，评审看不到），含完整标题、5 位作者及单位/邮箱、通讯作者（Bo Ma）、
  摘要、关键词，以及投稿信息块（目标期刊 TOMM、类别 Regular Paper、双盲）。
  编译产出 `paper/title_page.pdf`。
- **投稿类别**：选择 **Regular Paper（regular submission, no special issue）**。
  非 survey/tutorial/editorial；arXiv 预印本不算会议论文故非 Conference Extension；
  三个特刊（Foundation Models Meet 3D / Responsible & Explainable Multi-Modal
  Fusion / Multimodal Embodied Agents）均不匹配本文（本文是 training-only
  privileged-modality、单模态部署，非 multi-modal fusion）。
- **构建复核（2026-06-16，匿名后）**：`main.pdf` 23 页（匿名，行号）、
  `appendix.pdf` 6 页、`title_page.pdf` 2 页，均编译通过。
- **Cover letter 改投 TOMM（2026-06-16）**：`docs/cover_letter.txt` 已从 TCSVT
  改写为 ACM TOMM——更新抬头/EIC 称呼、投稿类别（Regular Paper）、多媒体计算
  系统相关性表述；移除 14 页 TCSVT 表述与正文 GitHub 链接，改为接收后开源 +
  双盲匿名说明（manuscript 匿名、作者信息在 title page 单独提供）；通讯作者
  邮箱改为 amabo1215@gmail.com。
- **匿名代码提交包（2026-06-16）**：把 `src/` 下可复现方法代码拷贝到
  `submit/code/`（`jdcnet_exp/`、`configs/`、`requirements.txt`、`README.md`），
  排除 `tmp_sync/`（789MB、含 sshpass 凭据）、`ops/`（远端集群脚本、含主机 IP
  10.147.20.176）、`results/`、`figures/`、checkpoints、原始数据与 `__pycache__`。
  核心代码本身无作者/单位/GitHub/邮箱/主机 IP 等可识别信息；README 顶部加双盲
  匿名说明。打包为 `submit/JDCNet_code_anonymous.zip`（48 文件、~139KB，使用
  forward-slash 路径以兼容 Linux 解压），最终匿名扫描通过。
- **遗留**：尚未按 ACM 投稿要求做内容级精简/校对。

## 当前状态（2026-05-17 close）

- **目标 venue**：ACM TOMM，transactions paper 23 页上限。
- **方法名**：JDCNet（confidence-gated CT-to-X-ray distillation，X-ray-only deployment graph）。
- **Headline 证据**：BIMCV 510-patient same-patient paired cohort，patient-level 5-fold × seeds 42–44。2/16 cells pass 固定 gate（mean ΔBA ≥ +0.03 且 bootstrap CI 排除 0）：
  - 3-slice soft-KL τ=0.70 λ=1.0：ΔBA=+0.0345 [+0.0112, +0.0571]
  - mid hard τ=0.80 λ=1.5：ΔBA=+0.0329 [+0.0074, +0.0584]
- **Comparator audit**：logit KD 变体、contrastive alignment、attention transfer、feature hints、BiomedCLIP、module-augmented pilot 全部 FAIL 同一 gate。

## 最新一轮修订（2026-05-17 revision_suggestions.tex pass）

- **R1 venue 合规**：`paper/main.tex` 与 `paper/appendix.tex` 已移除 `compsoc`；摘要从 ~211 词压到 198 词。
- **R3 近期相关工作定位**：Related Work 新增简短 `Relation to Recent Cross-Modal Privileged-Transfer Work` 段落，区分 Cahan 2025 (MICCAI CXR–CTPA)、DANTE (AAAI 2026)、K-MaT (arXiv 2026)；`paper/ref.bib` 加入 3 条对应引用。
- **R4 病人级保守不确定性**：附录新增 `Conservative Patient-Level Uncertainty` 表（fold/seed CI 与 patient-level paired bootstrap CI 并列）与 `Cohort Construction and Leakage Audit` 小节。
- **R6 部署成本细节**：deployment table 加入 median (IQR)、内存列、硬件/软件栈/精度/批量/warm-up/试次/预处理说明；edge 能耗显式标注为 not measured。
- **R7 算法编号**：加 `\usepackage{algorithm}`，把 JDCNet 训练过程从 figure 改为 algorithm 浮动体，统一 `Algorithm~\ref{alg:jdcnet}` 引用。
- **R8 可复现性**：实现化用词改为读者向开源声明（代码、split definitions、训练配置、bootstrap 工具在 `https://github.com/mabo1215/JDCNET` 开源；BIMCV 不再分发像素）。
- **页面压缩到 14 页**：删除 Transformers 子节；合并 `Privileged Information` 与 `Cross-Modal Distillation`；精简 Evidence Robustness、Introduction Motivation、Limitations、Discussion；`ref.bib` 从 58 → 30 条，对应未引用条目全部移除。

- **14页复核（2026-05-17）**：再次编译 `paper/build.bat`，确认 combined `paper/main.pdf` 为 14 页；为消除最后一页溢出，压缩 Appendix 的 gated-logit KD 温度/阈值扫描说明，移除该扫描的独立表格，并将机制总结并入同一段落；同步更新正文对该附录内容的引用。

- **Cover letter 同步（2026-05-17）**：`docs/cover_letter.txt` 已按最新 14 页 TCSVT 论文同步，更新为 JDCNet 当前标题、510-patient BIMCV headline 结果、同一 gate 下 comparator audit、部署成本表述、GitHub 开源链接和当前 appendix 内容；移除旧的 Code Ocean、commit hash、MIDRC/module-ablation 等过期描述。

- **Cover letter 简版（2026-05-17）**：`docs/cover_letter.txt` 已压缩到约 440 词，改成更自然的人工 cover letter 风格；保留标题、510-patient headline 结果、comparator audit、TCSVT 系统相关性、14 页状态、局限和 GitHub 链接，移除大段机械式分栏和过期标记。

- **伦理/知情同意表述（2026-05-17）**：建议提交表单选 `Yes`（使用人类影像数据），同时说明本研究为公开去标识化 BIMCV 数据的二次分析。`paper/main.tex` Methods 和 `docs/cover_letter.txt` 已补充 institutional research-committee approval/anonymization/no new consent 表述，重新编译 combined PDF 仍为 14 页。

- **Cover letter 初投版（2026-05-17）**：`docs/cover_letter.txt` 已从 revised/major revision 语气改为 initial submission 语气，删除 reviewer/response/revision 表述，保留简短人工风格、headline 结果、TCSVT 相关性、伦理说明和 GitHub 链接。

## 用户已确认的决策

- **不披露 arXiv pilot**：用户将自行更新 arXiv 上的预印本以与 TCSVT 稿件同步，因此不在论文中加入"Relation to prior arXiv version"段落。
- **不写 AI-content disclosure**：仅最小化语法润色，不写入 IEEE Acknowledgments。
- **不展开 latency variability / memory / edge power / patient-level bootstrap 原始结果**：数据在 4×3090 机器上存在，但 14 页约束下仅写最小化形式，待 reviewer 提出后再扩展。
- **外部 paired cohort 调研路径**：`src/` 已有数据下载脚手架，可在 Stage 10/round-2 用于外部验证。

## 构建提示

- Windows 端运行 `paper/build.bat` 生成 combined PDF；`paper/build.bat main` / `paper/build.bat appendix` 分别生成 standalone 输出。
- WSL 下无 pdflatex，编译需在 Windows 完成。