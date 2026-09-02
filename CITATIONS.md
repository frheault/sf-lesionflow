# Citations & Scientific Provenance

When using `sf-lesionflow` in academic research, please cite the respective algorithms, foundational tools, and pipeline infrastructure utilized below.

---

## 1. Published Lesion Segmentation Algorithms (10)

1. **LST-AI**:
   * Wiltgen T, et al. *LST-AI: A deep learning ensemble for accurate MS lesion segmentation*. NeuroImage: Clinical, 42:103611, 2024. (Not to be confused with the earlier, unrelated "LST" lesion-growth tool of Schmidt et al., 2012 — this pipeline uses the newer deep-learning ensemble.)
2. **SAMSEG (Sequence Adaptive Multimodal SEGmentation)**:
   * Cerri S, Puonti O, Meier DS, Wuerfel J, Mühlau M, Siebner HR, Van Leemput K. *A contrast-adaptive method for simultaneous whole-brain and lesion segmentation in multiple sclerosis*. NeuroImage, 225:117471, 2021. https://doi.org/10.1016/j.neuroimage.2020.117471
3. **WMH-SynthSeg**:
   * Laso P, Cerri S, Sorby-Adams A, et al. *Quantifying white matter hyperintensity and brain volumes in heterogeneous clinical and low-field portable MRI*. IEEE International Symposium on Biomedical Imaging (ISBI), 2024. arXiv:2312.05119
   * Built on: Billot B, et al. *SynthSeg: Domain Randomisation for Segmentation of Brain MRI Scans of any Contrast and Resolution*. Medical Image Analysis, 2023 (underlying domain-randomization framework, not the WMH-specific model itself).
4. **FSL FAST Outlier**:
   * Zhang Y, Brady M, Smith S. *Segmentation of brain MR images through a hidden Markov random field model and the expectation-maximization algorithm*. IEEE Transactions on Medical Imaging, 20(1):45-57, 2001. https://doi.org/10.1109/42.906424
5. **FLAMeS (Fast Lesion Assessment in Multiple Sclerosis)**:
   * FLAMeS model record (Dataset004_WML, trainer `nnUNetTrainer_8000epochs`): [Zenodo record 17955359](https://zenodo.org/records/17955359); model description in the associated preprint ([PMC12140514](https://pmc.ncbi.nlm.nih.gov/articles/PMC12140514/)).
   * Built on: Isensee F, et al. *nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation*. Nature Methods, 2021 (underlying framework, not the FLAMeS model itself).
6. **TrueNet**:
   * Sundaresan V, Zamboni G, Rothwell PM, Jenkinson M, Griffanti L. *Triplanar ensemble U-Net model for white matter hyperintensities segmentation on MR images*. Medical Image Analysis, 73:102184, 2021.
7. **HyperMapp3r**:
   * Source repository: [github.com/AICONSlab/HyperMapp3r](https://github.com/AICONSlab/HyperMapp3r) (Goubran M, et al.).
   * Closest associated publication: Goubran M, et al. *Hippocampal segmentation for brains with extensive atrophy using three-dimensional convolutional neural networks*. Human Brain Mapping, 41(2):291-308, 2020. (Note: this citation covers the architecture's origin; the tool's WMH-segmentation mode used by this pipeline may derive from further unpublished/preprint work by the same group — treat the paper citation as provisional pending confirmation from the tool authors, though the repository link above is a confirmed, stable source.)
8. **SegCSVD (segcsvdWMH)**:
   * Gibson E, Ramirez J, et al. *segcsvdWMH: A Convolutional Neural Network-Based Tool for Quantifying White Matter Hyperintensities in Heterogeneous Patient Cohorts*. Human Brain Mapping, 2024. https://doi.org/10.1002/hbm.70104
9. **Emory Robust WMH**:
   * Wu J, et al. *Benchmark White Matter Hyperintensity Segmentation Methods Fail on Heterogeneous Clinical MRI: A New Dataset and Deep Learning-Based Solutions*. Journal of Imaging Informatics in Medicine, 2026. https://doi.org/10.1007/s10278-025-01808-9
10. **MARS-WMH**:
    * Gesierich B, et al. Cerebral Circulation - Cognition and Behavior, 2025. https://doi.org/10.1016/j.cccb.2025.100393 ([github.com/miac-research/MARS-WMH](https://github.com/miac-research/MARS-WMH))

---

## 2. Heuristic Proxy Implementations & Provenance Notices (3)

> [!CAUTION]
> The following three modules represent heuristic feature-based proxies rather than the official trained deep learning weights or statistical models. They should be interpreted as contrast and spatial prior filters in consensus fusion:

* **BAWIL Proxy (`SEGMENTATION_BAWIL`)**:
  * Named for and inspired by the Hugging Face model `Bawil/wmh_leverage_normal_abnormal_segmentation`, corresponding to: Bashiri M, et al. *Simultaneous Segmentation of Ventricles and Normal/Abnormal White Matter Hyperintensities in Clinical MRI using Deep Learning*. arXiv:2506.07123, 2025 — a pix2pix-based method distinguishing normal periventricular hyperintensities from pathological lesions. This is a preprint, not a peer-reviewed publication. Heuristic reproduction only — does not load the model's trained weights.
* **MIMoSA Proxy (`SEGMENTATION_MIMOSA`)**:
  * Inspired by Valcarcel AM, Linn KA, Vandekar SN, Satterthwaite TD, Muschelli J, Calabresi PA, et al. *MIMoSA: An Automated Method for Intermodal Segmentation Analysis of Multiple Sclerosis Brain Lesions*. Journal of Neuroimaging, 28(4):389-398, 2018. https://doi.org/10.1111/jon.12506. Output is generated from hardcoded multiscale intensity logits rather than fitted regression parameters.
* **SHiVAi Proxy (`SEGMENTATION_SHIVAI`)**:
  * Inspired by the SHIVA-WMH detector from the SHiVAi pipeline ([github.com/pboutinaud/SHiVAi](https://github.com/pboutinaud/SHiVAi), [pboutinaud/SHIVA_WMH](https://github.com/pboutinaud/SHIVA_WMH)): Boutinaud P, et al. *Early detection of white matter hyperintensities using SHIVA-WMH detector*. Human Brain Mapping, 2024. PMID: 38050769. Generated via multi-scale local contrast filtering rather than the published deep neural network.

---

## 3. Preprocessing, Registration & Fusion Toolkits

* **STAPLE (Simultaneous Truth and Performance Level Estimation)**:
  * Warfield SK, Zou KH, Wells WM. *Simultaneous truth and performance level estimation (STAPLE): an algorithm for the validation of image segmentation*. IEEE TMI, 2004.
* **ANTs (Advanced Normalization Tools)**:
  * Avants BB, et al. *A reproducible evaluation of ANTs similarity metric performance in 3D empirical medical image registration*. NeuroImage, 2011.
* **FreeSurfer SynthStrip**:
  * Hoopes A, et al. *SynthStrip: Skull-Stripping for Any Brain Image*. NeuroImage, 2022.
* **SimpleITK**:
  * Lowekamp BC, Chen DT, Ibáñez L, Blezek D. *The Design of SimpleITK*. Frontiers in Neuroinformatics, 7:45, 2013. https://doi.org/10.3389/fninf.2013.00045
* **scilpy & Dipy**:
  * Garyfallidis E, Brett M, Amirbekian B, Rokem A, van der Walt S, Descoteaux M, Nimmo-Smith I. *Dipy, a library for the analysis of diffusion MRI data*. Frontiers in Neuroinformatics, 8:8, 2014. https://doi.org/10.3389/fninf.2014.00008

---

## 4. Pipeline Infrastructure

* **Nextflow**:
  * Di Tommaso P, et al. *Nextflow enables reproducible computational workflows*. Nature Biotechnology, 2017.
* **nf-core**:
  * Ewels PA, et al. *The nf-core framework for community-curated bioinformatics pipelines*. Nature Biotechnology, 2020.
* **nf-neuro**:
  * SCIL (Sherbrooke Connectivity Imaging Lab). *nf-neuro: Nextflow modules and subworkflows for neuroimaging analysis*. [GitHub](https://github.com/scilus/nf-neuro).
