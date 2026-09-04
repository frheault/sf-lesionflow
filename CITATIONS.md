# Citations & Scientific Provenance

Cite the following algorithms, foundational tools, and pipeline infrastructure when using `sf-lesionflow` in academic research.

---

## 1. Published Lesion Segmentation Algorithms

1. **LST-AI**:
   * Wiltgen T, et al. *LST-AI: A deep learning ensemble for accurate MS lesion segmentation*. NeuroImage: Clinical, 42:103611, 2024. https://doi.org/10.1016/j.nicl.2024.103611. This pipeline uses the deep learning ensemble model.
2. **SAMSEG (Sequence Adaptive Multimodal SEGmentation)**:
   * Cerri S, Puonti O, Meier DS, Wuerfel J, Mühlau M, Siebner HR, Van Leemput K. *A contrast-adaptive method for simultaneous whole-brain and lesion segmentation in multiple sclerosis*. NeuroImage, 225:117471, 2021. https://doi.org/10.1016/j.neuroimage.2020.117471
3. **WMH-SynthSeg**:
   * Laso P, Cerri S, Sorby-Adams A, et al. *Quantifying white matter hyperintensity and brain volumes in heterogeneous clinical and low-field portable MRI*. IEEE International Symposium on Biomedical Imaging (ISBI), 2024. arXiv:2312.05119. https://doi.org/10.48550/arXiv.2312.05119
   * Built on: Billot B, Greve DN, Puonti O, et al. *SynthSeg: Segmentation of brain MRI scans of any contrast and resolution without retraining*. Medical Image Analysis, 86:102789, 2023. https://doi.org/10.1016/j.media.2023.102789 (underlying domain-randomization framework).
4. **FSL FAST Outlier**:
   * Zhang Y, Brady M, Smith S. *Segmentation of brain MR images through a hidden Markov random field model and the expectation-maximization algorithm*. IEEE Transactions on Medical Imaging, 20(1):45-57, 2001. https://doi.org/10.1109/42.906424
5. **FLAMeS (Fast Lesion Assessment in Multiple Sclerosis)**:
   * FLAMeS model record (Dataset004_WML, trainer `nnUNetTrainer_8000epochs`): [Zenodo record 17955359](https://zenodo.org/records/17955359). https://doi.org/10.5281/zenodo.17955359
   * Dereskewicz E, La Rosa F, dos Santos Silva J, Sizer E, Kohli A, Wynen M, et al. *A Novel Convolutional Neural Network for Automated Multiple Sclerosis Brain Lesion Segmentation*. Journal of Neuroimaging, 35(5):e70085, 2025. https://doi.org/10.1111/jon.70085
   * Built on: Isensee F, Jaeger PF, Kohl SAA, Petersen J, Maier-Hein KH. *nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation*. Nature Methods, 18:203-211, 2021. https://doi.org/10.1038/s41592-020-01008-z (underlying framework).
6. **TrueNet**:
   * Sundaresan V, Zamboni G, Rothwell PM, Jenkinson M, Griffanti L. *Triplanar ensemble U-Net model for white matter hyperintensities segmentation on MR images*. Medical Image Analysis, 73:102184, 2021. https://doi.org/10.1016/j.media.2021.102184
7. **HyperMapp3r**:
   * Source repository: [github.com/AICONSlab/HyperMapp3r](https://github.com/AICONSlab/HyperMapp3r) (Goubran M, et al.).
   * Mojiri Forooshani P, Biparva M, Ntiri EE, Ramirez J, Boone L, Holmes M, Adamo S, Gao F, Ozzoude M, Scott C, Dowlatshahi D, Lawrence-Dewar J, Kwan D, Lang A, Marcotte K, Leonard C, Rochon E, Heyn C, Bartha R, Strother S, Tardif JC, Symons S, Masellis M, Swartz R, Moody A, Black SE, Goubran M. *Deep Bayesian networks for uncertainty estimation and adversarial resistance of white matter hyperintensity segmentation*. Human Brain Mapping, 2022. https://doi.org/10.1002/hbm.25784
8. **SegCSVD (segcsvdWMH)**:
   * Gibson E, Ramirez J, et al. *segcsvdWMH: A Convolutional Neural Network-Based Tool for Quantifying White Matter Hyperintensities in Heterogeneous Patient Cohorts*. Human Brain Mapping, 2024. https://doi.org/10.1002/hbm.70104
9. **Emory Robust WMH**:
   * Wu J, et al. *Benchmark White Matter Hyperintensity Segmentation Methods Fail on Heterogeneous Clinical MRI: A New Dataset and Deep Learning-Based Solutions*. Journal of Imaging Informatics in Medicine, 2026. https://doi.org/10.1007/s10278-025-01808-9
10. **MARS-WMH**:
    * Gesierich B, Pirpamer L, Meier DS, et al. *Technical and Clinical Validation of a Novel Deep Learning-Based White Matter Hyperintensity Segmentation Tool*. Cerebral Circulation - Cognition and Behavior, 2025. https://doi.org/10.1016/j.cccb.2025.100393 ([github.com/miac-research/MARS-WMH](https://github.com/miac-research/MARS-WMH))
11. **MIMoSA**:
    * Valcarcel AM, Linn KA, Vandekar SN, Satterthwaite TD, Muschelli J, Calabresi PA, et al. *MIMoSA: An Automated Method for Intermodal Segmentation Analysis of Multiple Sclerosis Brain Lesions*. Journal of Neuroimaging, 28(4):389-398, 2018. https://doi.org/10.1111/jon.12506. The `SEGMENTATION_MIMOSA` process executes the pretrained `mimosa_model_No_PD_T2` logistic regression model from the `mimosa` package. Consult [`dockerfiles/mimosa/README.md`](dockerfiles/mimosa/) for execution details.
12. **BAWIL**:
    * Uses the Hugging Face model `Bawil/wmh_leverage_normal_abnormal_segmentation`: Bashiri Bawil M, Shamsi M, Shakeri Bavil A. *Adversarial Deep Learning for Simultaneous Segmentation of Ventricular and White Matter Hyperintensities in Clinical MRI*. arXiv:2506.07123, 2025. https://doi.org/10.48550/arXiv.2506.07123. The model is a 3-class U-Net that segments periventricular and white matter hyperintensities on axial FLAIR slices. `SEGMENTATION_BAWIL` executes the pretrained Keras model via `bin/bawil_filter.py`. Consult [`dockerfiles/bawil/README.md`](dockerfiles/bawil/) for implementation details.
13. **SHIVA-WMH**:
    * Tsuchida A, Boutinaud P, Verrecchia V, Tzourio C, Debette S, Joliot M. *Early detection of white matter hyperintensities using SHIVA-WMH detector*. Human Brain Mapping, 45(1):e26548, 2024. https://doi.org/10.1002/hbm.26548 ([github.com/pboutinaud/SHIVA_WMH](https://github.com/pboutinaud/SHIVA_WMH)). `SEGMENTATION_SHIVAI` executes the pretrained 5-fold ResUnet3D SavedModel ensemble (`v2/T1+FLAIR-WMH`). Model weights use a CC BY-NC-SA license. Consult [`dockerfiles/shivai/README.md`](dockerfiles/shivai/) for setup and execution details.

All 13 lesion segmentation algorithms execute published, pretrained models.

---

## 3. Preprocessing, Registration & Fusion Toolkits

* **STAPLE (Simultaneous Truth and Performance Level Estimation)**:
  * Warfield SK, Zou KH, Wells WM. *Simultaneous truth and performance level estimation (STAPLE): an algorithm for the validation of image segmentation*. IEEE Transactions on Medical Imaging, 23(7):903-921, 2004. https://doi.org/10.1109/TMI.2004.828354
* **ANTs (Advanced Normalization Tools)**:
  * Avants BB, Tustison NJ, Song G, Cook PA, Klein A, Gee JC. *A reproducible evaluation of ANTs similarity metric performance in brain image registration*. NeuroImage, 54(3):2033-2044, 2011. https://doi.org/10.1016/j.neuroimage.2010.09.025
* **FreeSurfer SynthStrip**:
  * Hoopes A, Mora JS, Dalca AV, Fischl B, Hoffmann M. *SynthStrip: Skull-Stripping for Any Brain Image*. NeuroImage, 260:119474, 2022. https://doi.org/10.1016/j.neuroimage.2022.119474
* **SimpleITK**:
  * Lowekamp BC, Chen DT, Ibáñez L, Blezek D. *The Design of SimpleITK*. Frontiers in Neuroinformatics, 7:45, 2013. https://doi.org/10.3389/fninf.2013.00045
* **scilpy**:
  * Renauld E, Boré A, Poirier C, Valcourt-Caron A, Karan P, Théberge A, Théaud G, Edde M, Poulin P, Girard G, Houde JC, Gagnon A, St-Onge E, Little G, Legarreta JH, Thoumyre S, Grenier G, El Yamani Z, Ocampo Pineda M, Battocchio M, Beaudoin V, Joanisse A, Petit L, Rheault F, Descoteaux M. *Tractography analysis with the scilpy toolbox*. Aperture Neuro, 6, 2026. https://doi.org/10.52294/001c.154022
* **Dipy**:
  * Garyfallidis E, Brett M, Amirbekian B, Rokem A, van der Walt S, Descoteaux M, Nimmo-Smith I. *Dipy, a library for the analysis of diffusion MRI data*. Frontiers in Neuroinformatics, 8:8, 2014. https://doi.org/10.3389/fninf.2014.00008

---

## 4. Pipeline Infrastructure

* **Nextflow**:
  * Di Tommaso P, Chatzou M, Floden EW, Barja PP, Palumbo E, Notredame C. *Nextflow enables reproducible computational workflows*. Nature Biotechnology, 35:316-319, 2017. https://doi.org/10.1038/nbt.3820
* **nf-core**:
  * Ewels PA, Peltzer A, Fillinger S, Patel H, Alneberg J, Wilm A, Garcia MU, Di Tommaso P, Nahnsen S. *The nf-core framework for community-curated bioinformatics pipelines*. Nature Biotechnology, 38(3):276-278, 2020. https://doi.org/10.1038/s41587-020-0439-x
* **nf-neuro**:
  * SCIL (Sherbrooke Connectivity Imaging Lab). *nf-neuro: Nextflow modules and subworkflows for neuroimaging analysis*. [GitHub](https://github.com/scilus/nf-neuro).
