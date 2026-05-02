可以，**non-COVID CT/CXR 数据**可以这样选：

## 1. CXR / Chest X-ray 非 COVID 数据集

| 数据集                               |                                                      规模/标注 | 适合任务                     | 推荐程度  |
| --------------------------------- | ---------------------------------------------------------: | ------------------------ | ----- |
| **MIMIC-CXR-JPG**                 |                            377,110 张 CXR，227,827 份报告，结构化标签 | 多标签分类、报告生成、VLM/预训练       | ⭐⭐⭐⭐⭐ |
| **CheXpert**                      | 224,316 张 CXR，65,240 患者，14 类 observation + uncertain label | 多标签分类、疾病识别               | ⭐⭐⭐⭐⭐ |
| **NIH ChestX-ray14 / ChestXray8** |                   112,120 张 frontal CXR，30,805 患者，14 类胸部疾病 | 多标签分类、弱监督定位              | ⭐⭐⭐⭐  |
| **PadChest**                      |                                   160k+ CXR，67k+ 患者，报告+多标签 | 多标签分类、report/text-image  | ⭐⭐⭐⭐  |
| **VinDr-CXR**                     |               18,000 PA CXR，17 位放射科医生，bbox + global labels | 检测/定位 + 分类               | ⭐⭐⭐⭐⭐ |
| **RSNA Pneumonia Detection**      |                          30,000 frontal CXR，pneumonia bbox | 肺炎检测 / object detection  | ⭐⭐⭐⭐  |
| **SIIM-ACR Pneumothorax**         |                                CXR + pneumothorax mask/RLE | 气胸分割                     | ⭐⭐⭐⭐  |
| **IU X-ray / Open-I**             |                                    7,470 CXR，3,955 reports | 报告生成、image-text baseline | ⭐⭐⭐   |

MIMIC-CXR-JPG 是最强通用 CXR 选择，官方说明其包含 377,110 JPG 图像和 227,827 份 free-text radiology reports 的结构化标签。([physionet.org][1]) CheXpert 是 Stanford 的大规模胸片数据集，含 224,316 张胸片和 65,240 名患者。([aimi.stanford.edu][2]) VinDr-CXR 更适合 detection/grounding，因为公开 18,000 张 CXR，并有 22 个局部 bbox 标签和 6 个全局诊断标签。([physionet.org][3]) PadChest 含 160,000+ 图像、67,000+ 患者，适合做跨机构泛化。([PubMed][4])

## 2. CT 非 COVID 数据集

| 数据集                     |                                                 规模/标注 | 适合任务                              | 推荐程度  |
| ----------------------- | ----------------------------------------------------: | --------------------------------- | ----- |
| **LIDC-IDRI**           |             1,018 thoracic CT cases，肺结节 XML 标注，多放射科医生 | 肺结节检测、分割、恶性风险分类                   | ⭐⭐⭐⭐⭐ |
| **LUNA16**              |                                          LIDC-IDRI 子集 | 肺结节检测 benchmark                   | ⭐⭐⭐⭐  |
| **NLST**                |                                        大规模低剂量 CT 肺癌筛查 | 肺癌筛查、纵向分析、预训练                     | ⭐⭐⭐⭐⭐ |
| **NSCLC-Radiomics**     |                 422 NSCLC 患者，pretreatment CT + 手工肿瘤勾画 | 肺癌 radiomics、肿瘤分割、生存预测            | ⭐⭐⭐⭐  |
| **NSCLC-Radiogenomics** |                      211 NSCLC subjects，CT + PET/CT 等 | radiogenomics / imaging biomarker | ⭐⭐⭐⭐  |
| **RIDER Lung CT**       | NSCLC lung CT，test-retest / reconstruction variations | 鲁棒性、reproducibility、肿瘤测量          | ⭐⭐⭐   |
| **DeepLesion**          |        32,735 lesions，32,120 CT slices，4,427 patients | 泛 lesion 检测，含胸部/腹部等               | ⭐⭐⭐⭐  |

LIDC-IDRI 是最常用的非 COVID 胸部 CT 数据集，包含 1,018 个 clinical thoracic CT cases，并带有多名胸部放射科医生两阶段标注结果。([PMC][5]) NLST 是低剂量 CT 肺癌筛查数据，约 54,000 参与者，适合做大规模 lung screening / pretraining。([cdas.cancer.gov][6]) NSCLC-Radiomics 含 422 名非小细胞肺癌患者的 pretreatment CT 和人工勾画。([cancerimagingarchive.net][7]) DeepLesion 有 32,735 个 CT lesion annotations，适合做泛化 lesion detection，但不是纯胸部 CT。([PMC][8])

## 3. 论文/实验里最推荐组合

**如果你做 CXR 分类/隐私保护/图像扰动：**

```text
Primary: MIMIC-CXR-JPG
External validation: CheXpert + NIH ChestX-ray14
Detection/grounding: VinDr-CXR or RSNA Pneumonia
Segmentation: SIIM-ACR Pneumothorax
```

**如果你做 CT 肺结节/肺癌：**

```text
Primary: LIDC-IDRI / LUNA16
External validation: NLST
Tumor segmentation / radiomics: NSCLC-Radiomics
Robustness: RIDER Lung CT
```

**如果只是想要“non-COVID baseline”：**

```text
CXR: MIMIC-CXR-JPG + CheXpert + NIH ChestX-ray14
CT: LIDC-IDRI + NLST + NSCLC-Radiomics
```

注意：不要把 **COVID-CT、COVIDx、BIMCV-COVID19、COVID-19 Radiography Database** 当作主要 non-COVID 数据源。它们里面可能有 normal / pneumonia / non-COVID 类别，但数据收集偏向 COVID 任务，容易被 reviewer 质疑 selection bias。

[1]: https://physionet.org/content/mimic-cxr-jpg/ "MIMIC-CXR-JPG - chest radiographs with structured labels v2.1.0"
[2]: https://aimi.stanford.edu/datasets/chexpert-chest-x-rays?utm_source=chatgpt.com "CheXpert: Chest X-rays"
[3]: https://physionet.org/content/vindr-cxr/ "VinDr-CXR: An open dataset of chest X-rays with radiologist annotations v1.0.0"
[4]: https://pubmed.ncbi.nlm.nih.gov/32877839/?utm_source=chatgpt.com "PadChest: A large chest x-ray image dataset with multi- ..."
[5]: https://pmc.ncbi.nlm.nih.gov/articles/PMC3041807/?utm_source=chatgpt.com "The Lung Image Database Consortium (LIDC) and ... - PMC"
[6]: https://cdas.cancer.gov/nlst/?utm_source=chatgpt.com "National Lung Screening Trial (NLST)"
[7]: https://www.cancerimagingarchive.net/collection/nsclc-radiomics/?utm_source=chatgpt.com "NSCLC-RADIOMICS - The Cancer Imaging Archive (TCIA)"
[8]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6052252/?utm_source=chatgpt.com "DeepLesion: automated mining of large-scale lesion ... - PMC"
