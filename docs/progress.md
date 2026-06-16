# 进度

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
  邮箱改为 rcn4743@aut.ac.nz。
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