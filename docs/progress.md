# 进度

## 当前状态（2026-05-17 close）

- **目标 venue**：IEEE TCSVT，transactions paper 14 页上限。
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

## ???????????2026-05-18?

- **?? Biography ??**??? `paper/main.tex` ????????? Bo Ma?Wei Qi Yan?Jinsong Wu?Hongjiang Wei?Kun Liu ????? IEEE biography???? `/mnt/d/work/paper/profile/` ?????????? `paper/figs/` ????Hongjiang Wei ? Kun Liu ?????????????
- **??????**??? Hongjiang Wei ?????? Hangzhou Hikvision Digital Technology Co., Ltd.??? Kun Liu ?????? Hebei University of Technology ? School of Artificial Intelligence and Data Science?
- **Appendix ????**???? `paper/build.bat` ?????????? appendix ??? `paper/main.pdf`?????????? `paper/main.pdf` ? `paper/appendix.pdf`???? `paper/build.bat combined` ???????????
- **????**???? `cmd /c paper\build.bat`????? `paper/main.pdf`?12 ??? biographies?? `paper/appendix.pdf`?4 ???? appendix ????LaTeX ????????????????
- **Biography ??????**???? biographies ??????? `\vspace{-12pt}` ??? spacing ????? IEEEtran/TCSVT ?? biography ??? 1 in ? 1.25 in ??????????????? 12 ????? 4 ??
