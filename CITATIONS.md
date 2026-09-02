# Citations & Scientific Provenance

When using `sf-lesionflow` in academic research, please cite the respective algorithms, foundational tools, and pipeline infrastructure utilized below.

---

## 1. Published Lesion Segmentation Algorithms (10)

1. **LST-AI**:
   * Schmidt P, et al. *An automated tool for detection of FLAIR-hyperintense white-matter lesions in Multiple Sclerosis*. NeuroImage, 2012 / LST-AI deep learning model.
2. **SAMSEG (Sequence Adaptive Multimodal SEGmentation)**:
   * Cerri S, et al. *A contrast-adaptive method for simultaneous whole-brain and lesion segmentation in multiple sclerosis*. NeuroImage, 2021.
3. **WMH-SynthSeg**:
   * Billot B, et al. *SynthSeg: Domain Randomisation for Segmentation of Brain MRI Scans of any Contrast and Resolution*. Medical Image Analysis, 2023.
4. **FSL FAST Outlier**:
   * Zhang Y, Brady M, Smith S. *Segmentation of brain MR images through a hidden Markov random field model and the expectation-maximization algorithm*. IEEE TMI, 2001.
5. **FLAMeS (Fast Lesion Assessment in Multiple Sclerosis)**:
   * Isensee F, et al. *nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation*. Nature Methods, 2021.
6. **TrueNet**:
   * Sundaresan V, et al. *Automated White Matter Hyperintensity Segmentation Using TrueNet (Tri-planar U-Net)*. NeuroImage, 2021.
7. **HyperMapp3r**:
   * Goubran M, et al. *HyperMapp3r: Hippocampal and White Matter Hyperintensity Mapping with Deep Residual Networks*. Medical Image Analysis, 2019.
8. **SegCSVD (3D Patch CNN)**:
   * Guerrero R, et al. *White matter hyperintensity and stroke lesion segmentation and differentiation using convolutional neural networks*. NeuroImage: Clinical, 2018.
9. **Emory Robust WMH**:
   * CN2L Emory University. *Robust White Matter Hyperintensity Segmentation across multi-site protocols*, 2023.
10. **MARS-WMH**:
    * MIAC Research. *WMH Segmentation using nnU-Net with multi-sequence brain MRI*, 2024.

---

## 2. Heuristic Proxy Implementations & Provenance Notices (3)

> [!CAUTION]
> The following three modules represent heuristic feature-based proxies rather than the official trained deep learning weights or statistical models. They should be interpreted as contrast and spatial prior filters in consensus fusion:

* **BAWIL Proxy (`SEGMENTATION_BAWIL`)**:
  * Heuristic reproduction of Bawil contrast smoothing and thresholding approach. Does not load trained weights.
* **MIMoSA Proxy (`SEGMENTATION_MIMOSA`)**:
  * Inspired by Valcarcel AM, et al. (*MIMoSA: An Automated Method for Intermodal Segmentation Analysis of Multiple Sclerosis Brain Lesions*, J Neuroimaging 2018). Output is generated from hardcoded multiscale intensity logits rather than fitted regression parameters.
* **SHiVAi Proxy (`SEGMENTATION_SHIVAI`)**:
  * Inspired by Boutinaud P, et al. (*SHiVAi: 3D CNN for White Matter Hyperintensities*, 2021). Generated via multi-scale local contrast filtering rather than the published deep neural network.

---

## 3. Preprocessing, Registration & Fusion Toolkits

* **STAPLE (Simultaneous Truth and Performance Level Estimation)**:
  * Warfield SK, Zou KH, Wells WM. *Simultaneous truth and performance level estimation (STAPLE): an algorithm for the validation of image segmentation*. IEEE TMI, 2004.
* **ANTs (Advanced Normalization Tools)**:
  * Avants BB, et al. *A reproducible evaluation of ANTs similarity metric performance in 3D empirical medical image registration*. NeuroImage, 2011.
* **FreeSurfer SynthStrip**:
  * Hoopes A, et al. *SynthStrip: Skull-Stripping for Any Brain Image*. NeuroImage, 2022.
* **SimpleITK**:
  * Lowekamp BC, Chen DT, Ibáñez L, Blezek D. *The Design of SimpleITK*. Frontiers in Neuroinformatics, 2013.
* **scilpy & Dipy**:
  * Garyfallidis E, et al. *DIPY, a library for the analysis of diffusion MRI data*. Frontiers in Neuroinformatics, 2014.

---

## 4. Pipeline Infrastructure

* **Nextflow**:
  * Di Tommaso P, et al. *Nextflow enables reproducible computational workflows*. Nature Biotechnology, 2017.
* **nf-neuro**:
  * SCIL (Sherbrooke Connectivity Imaging Lab). *nf-neuro: Nextflow modules and subworkflows for neuroimaging analysis*. [GitHub](https://github.com/scilus/nf-neuro).
