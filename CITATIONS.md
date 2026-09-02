# Citations & Scientific Provenance

When using `sf-lesionflow` in academic research, please cite the respective algorithms, foundational tools, and pipeline infrastructure utilized below.

---

## 1. Published Lesion Segmentation Algorithms (10)

1. **LST-AI**:
   * Wiltgen T, et al. *LST-AI: A deep learning ensemble for accurate MS lesion segmentation*. NeuroImage: Clinical, 42:103611, 2024. (Not to be confused with the earlier, unrelated "LST" lesion-growth tool of Schmidt et al., 2012 — this pipeline uses the newer deep-learning ensemble.)
2. **SAMSEG (Sequence Adaptive Multimodal SEGmentation)**:
   * Cerri S, et al. *A contrast-adaptive method for simultaneous whole-brain and lesion segmentation in multiple sclerosis*. NeuroImage, 2021.
3. **WMH-SynthSeg**:
   * Billot B, et al. *SynthSeg: Domain Randomisation for Segmentation of Brain MRI Scans of any Contrast and Resolution*. Medical Image Analysis, 2023.
4. **FSL FAST Outlier**:
   * Zhang Y, Brady M, Smith S. *Segmentation of brain MR images through a hidden Markov random field model and the expectation-maximization algorithm*. IEEE TMI, 2001.
5. **FLAMeS (Fast Lesion Assessment in Multiple Sclerosis)**:
   * FLAMeS model record (Dataset004_WML, trainer `nnUNetTrainer_8000epochs`): [Zenodo record 17955359](https://zenodo.org/records/17955359); model description in the associated preprint ([PMC12140514](https://pmc.ncbi.nlm.nih.gov/articles/PMC12140514/)).
   * Built on: Isensee F, et al. *nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation*. Nature Methods, 2021 (underlying framework, not the FLAMeS model itself).
6. **TrueNet**:
   * Sundaresan V, Zamboni G, Rothwell PM, Jenkinson M, Griffanti L. *Triplanar ensemble U-Net model for white matter hyperintensities segmentation on MR images*. Medical Image Analysis, 73:102184, 2021.
7. **HyperMapp3r**:
   * Goubran M, et al. *Hippocampal segmentation for brains with extensive atrophy using three-dimensional convolutional neural networks*. Human Brain Mapping, 41(2):291-308, 2020. (Note: this citation covers the architecture's origin; the tool's WMH-segmentation mode used by this pipeline may derive from further unpublished/preprint work by the same group — treat this citation as provisional pending confirmation from the tool authors.)
8. **SegCSVD (3D Patch CNN)**:
   * Guerrero R, et al. *White matter hyperintensity and stroke lesion segmentation and differentiation using convolutional neural networks*. NeuroImage: Clinical, 2018.
9. **Emory Robust WMH**:
   * Wu J, et al. *Benchmark White Matter Hyperintensity Segmentation Methods Fail on Heterogeneous Clinical MRI: A New Dataset and Deep Learning-Based Solutions*. Journal of Imaging Informatics in Medicine, 2026. https://doi.org/10.1007/s10278-025-01808-9
10. **MARS-WMH**:
    * Gesierich B, et al. Cerebral Circulation - Cognition and Behavior, 2025. https://doi.org/10.1016/j.cccb.2025.100393 ([github.com/miac-research/MARS-WMH](https://github.com/miac-research/MARS-WMH))

---

## 2. Heuristic Proxy Implementations & Provenance Notices (3)

> [!CAUTION]
> The following three modules represent heuristic feature-based proxies rather than the official trained deep learning weights or statistical models. They should be interpreted as contrast and spatial prior filters in consensus fusion:

* **BAWIL Proxy (`SEGMENTATION_BAWIL`)**:
  * Heuristic reproduction of Bawil contrast smoothing and thresholding approach. Does not load trained weights.
* **MIMoSA Proxy (`SEGMENTATION_MIMOSA`)**:
  * Inspired by Valcarcel AM, et al. (*MIMoSA: An Automated Method for Intermodal Segmentation Analysis of Multiple Sclerosis Brain Lesions*, J Neuroimaging 2018). Output is generated from hardcoded multiscale intensity logits rather than fitted regression parameters.
* **SHiVAi Proxy (`SEGMENTATION_SHIVAI`)**:
  * Inspired by the SHiVAi pipeline ([github.com/pboutinaud/SHiVAi](https://github.com/pboutinaud/SHiVAi)), an umbrella of Boutinaud et al. 3D CNN models for cerebral small vessel disease biomarkers (PVS, WMH, microbleeds, lacunes) — see e.g. Boutinaud P, et al. *3D Segmentation of Perivascular Spaces on T1-Weighted 3 Tesla MR Images With a Convolutional Autoencoder and a U-Shaped Neural Network*. Frontiers in Neuroinformatics, 15, 2021. Generated via multi-scale local contrast filtering rather than any of the published deep neural network models in that pipeline.

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
* **nf-core**:
  * Ewels PA, et al. *The nf-core framework for community-curated bioinformatics pipelines*. Nature Biotechnology, 2020.
* **nf-neuro**:
  * SCIL (Sherbrooke Connectivity Imaging Lab). *nf-neuro: Nextflow modules and subworkflows for neuroimaging analysis*. [GitHub](https://github.com/scilus/nf-neuro).
