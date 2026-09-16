# Container Recipes & Build Registry for sf-lesionflow

This directory contains Dockerfiles, build instructions, and provenance records for the 13 lesion segmentation algorithms integrated into `sf-lesionflow`.

---

## 1. Master Container Registry

| Pipeline Process | Directory | DockerHub Image | Build Type | Model Weights Sourcing |
| :--- | :--- | :--- | :--- | :--- |
| `SEGMENTATION_LST_AI` | [`lst_ai/`](lst_ai/) | `frheault/sf-lesionflow-lst_ai:1.1.0` | Custom Dockerfile | Auto-fetched from [GitHub Releases](https://github.com/CompImg/LST-AI/releases/download/v1.0.0/lst_data.zip) |
| `SEGMENTATION_FLAMES` | [`flames/`](flames/) | `frheault/sf-lesionflow-flames:1.0.0` | Custom Dockerfile | Auto-fetched from [Zenodo Record 17955359](https://zenodo.org/records/17955359/files/Dataset004_WML.zip) |
| `SEGMENTATION_TRUENET` | [`truenet/`](truenet/) | `frheault/sf-lesionflow-truenet:1.0.0` | Custom Dockerfile | **Pre-download required** ([Google Drive](https://drive.google.com/drive/folders/1iqO-hd27NSHHfKun125Rt-2fh1l9EiuT)) |
| `SEGMENTATION_FAST_OUTLIER` | [`fast_outlier/`](fast_outlier/) | `frheault/sf-lesionflow-fast_outlier:1.0.0` | Custom Dockerfile | None (Unsupervised FSL + Python math) |
| `SEGMENTATION_WMH_SYNTHSEG` | [`wmh_synthseg/`](wmh_synthseg/) | `frheault/sf-lesionflow-wmh_synthseg:1.0.0` | Custom Dockerfile | Auto-fetched from [GitHub](https://github.com/lasopablo/freesurfer-freesurfer-dev-mri_WMHsynthseg) + [MGH FTP](https://ftp.nmr.mgh.harvard.edu/pub/dist/lcnpublic/dist/WMH-SynthSeg/WMH-SynthSeg_v10_231110.pth), on `freesurfer/freesurfer:7.4.1` (x86_64) |
| `SEGMENTATION_EMORY_ROBUST` | [`emory_robust/`](emory_robust/) | `emorycn2l/emory_robust_wmh:v1.2` | Upstream Public | Pre-baked in DockerHub image (~25 GB) |
| `SEGMENTATION_MARS_WMH` | [`mars_wmh/`](mars_wmh/) | `ghcr.io/miac-research/wmh-nnunet:latest` | Upstream Public | Pre-baked in MIAC GHCR image |
| `SEGMENTATION_HYPERMAPP3R` | [`hypermapp3r/`](hypermapp3r/) | `mgoubran/hypermapper:latest` | Upstream Public | Pre-baked in DockerHub image |
| `SEGMENTATION_SAMSEG` | [`samseg/`](samseg/) | `freesurfer/freesurfer:7.4.1` | Upstream Public | Pre-baked in official FreeSurfer image |
| `SEGMENTATION_SEGCSVD` | [`segcsvd/`](segcsvd/) | `frheault/sf-lesionflow-segcsvd:rc03` | Custom (pre-built local source) | Pre-baked in image |
| `SEGMENTATION_BAWIL` | [`bawil/`](bawil/) | `frheault/sf-lesionflow-bawil:1.0.0` | Custom Dockerfile | Auto-fetched from [Hugging Face](https://huggingface.co/Bawil/wmh_leverage_normal_abnormal_segmentation) |
| `SEGMENTATION_MIMOSA` | [`mimosa/`](mimosa/) | `frheault/sf-lesionflow-mimosa:1.0.0` | Custom Dockerfile | Pretrained model (`mimosa_model_No_PD_T2`) bundled in `mimosa` R package, on `adigherman/neuroconductor-release` |
| `SEGMENTATION_SHIVAI` | [`shivai/`](shivai/) | `frheault/sf-lesionflow-shivai:1.0.0` | Custom Dockerfile | **Manual download required** ([cloud.efixia.com](https://cloud.efixia.com/sharing/cpb3eUvMa)) |

---

## 2. Pushing Images to DockerHub

All custom images are pushed (and re-pushed after rebuilds) using:

```bash
# One-time: login to DockerHub
docker login -u frheault

# Push all 9 custom images
dockerfiles/push_to_dockerhub.sh

# Dry-run (print commands without executing)
dockerfiles/push_to_dockerhub.sh --dry-run
```

The script tags each local image to its `frheault/sf-lesionflow-<algo>:<version>` name and pushes it. Keep the version tags in sync with the `container` directives in `modules/local/lesion_segmentation.nf`.

---

## 3. Build Instructions for Custom Containers

After building, push the updated image with `dockerfiles/push_to_dockerhub.sh`.

### A. FLAMeS (`frheault/sf-lesionflow-flames:1.0.0`)
Build the FLAMeS container. The build process installs PyTorch CPU and downloads the 5-fold model weights from Zenodo:
```bash
docker build -t frheault/sf-lesionflow-flames:1.0.0 dockerfiles/flames/
```

### B. LST-AI (`frheault/sf-lesionflow-lst_ai:1.1.0`)
Build the LST-AI container. The build process installs LST-AI v1.1.0 and downloads model assets from GitHub Releases:
```bash
docker build -t frheault/sf-lesionflow-lst_ai:1.1.0 dockerfiles/lst_ai/
```

### C. TrueNet (`frheault/sf-lesionflow-truenet:1.0.0`)
Download TrueNet weights from Google Drive into the build context before building the image:
```bash
# 1. Install gdown if needed
pip install gdown

# 2. Download Oxford TrueNet model weights
gdown --folder https://drive.google.com/drive/folders/1iqO-hd27NSHHfKun125Rt-2fh1l9EiuT -O dockerfiles/truenet/models

# 3. Build the Docker image
docker build -t frheault/sf-lesionflow-truenet:1.0.0 dockerfiles/truenet/
```
Note: `.gitignore` excludes `dockerfiles/truenet/models/` from version control.

### D. FAST Outlier (`frheault/sf-lesionflow-fast_outlier:1.0.0`)
Build the unsupervised FAST outlier container:
```bash
docker build -t frheault/sf-lesionflow-fast_outlier:1.0.0 dockerfiles/fast_outlier/
```

### E. WMH-SynthSeg (`frheault/sf-lesionflow-wmh_synthseg:1.0.0`)
Build the WMH-SynthSeg container on `freesurfer/freesurfer:7.4.1`. The build process clones source code and downloads pretrained weights from official MGH servers. Consult [`wmh_synthseg/README.md`](wmh_synthseg/) for architecture details:
```bash
docker build -t frheault/sf-lesionflow-wmh_synthseg:1.0.0 dockerfiles/wmh_synthseg/
```

### F. MIMoSA (`frheault/sf-lesionflow-mimosa:1.0.0`)
Build the MIMoSA container on `adigherman/neuroconductor-release`. The base image includes R, FSL, and the pre-installed `mimosa` package:
```bash
docker build -t frheault/sf-lesionflow-mimosa:1.0.0 dockerfiles/mimosa/
```

### G. BAWIL (`frheault/sf-lesionflow-bawil:1.0.0`)
Build the BAWIL container. The build process downloads the pretrained Keras model from Hugging Face. Consult [`bawil/README.md`](bawil/) for dependency details:
```bash
docker build -t frheault/sf-lesionflow-bawil:1.0.0 dockerfiles/bawil/
```

### H. SHiVAi (`frheault/sf-lesionflow-shivai:1.0.0`)
Download SHIVA-WMH model weights manually before building the container. Consult [`shivai/README.md`](shivai/) for the download URL, checksum verification, and directory layout under `dockerfiles/shivai/models/`:
```bash
docker build -t frheault/sf-lesionflow-shivai:1.0.0 dockerfiles/shivai/
```

### I. SegCSVD (`frheault/sf-lesionflow-segcsvd:rc03`)
SegCSVD is a pre-existing image sourced from a local Docker daemon. Once available locally:
```bash
# Retag and push to DockerHub
docker tag segcsvd_rc03:latest frheault/sf-lesionflow-segcsvd:rc03
docker push frheault/sf-lesionflow-segcsvd:rc03
```

---

## 4. Pulling Upstream Public Images

Pull official pre-compiled container images for the remaining algorithms:

```bash
# Emory Robust WMH (~25 GB)
docker pull emorycn2l/emory_robust_wmh:v1.2

# MARS-WMH
docker pull ghcr.io/miac-research/wmh-nnunet:latest

# HyperMapp3r
docker pull mgoubran/hypermapper:latest

# FreeSurfer SAMSEG
docker pull freesurfer/freesurfer:7.4.1
```

---

## 5. Standard Operating Procedure (SOP): Adding a New Algorithm

Follow these steps to integrate a new algorithm into `sf-lesionflow`:

1. **Create Subdirectory**:
   Create a directory for the algorithm using lowercase snake_case:
   ```bash
   mkdir -p dockerfiles/<new_algo>/
   ```

2. **Add Dockerfile & Sourcing**:
   * Custom container: add `dockerfiles/<new_algo>/Dockerfile`. Fetch model weights from permanent public URLs (Zenodo, OSF, Hugging Face, or GitHub Releases).
   * Existing image: add `dockerfiles/<new_algo>/README.md` documenting image source, size, base image, and citations.

3. **Build & Push to DockerHub**:
   ```bash
   docker build -t frheault/sf-lesionflow-<new_algo>:<version> dockerfiles/<new_algo>/
   # Add to IMAGES array in dockerfiles/push_to_dockerhub.sh
   dockerfiles/push_to_dockerhub.sh
   ```

4. **Update this Master README**:
   * Add the process entry to the **Master Container Registry** table in Section 1.
   * Add build commands to Section 3 or pull commands to Section 4.

5. **Wire into Nextflow**:
   * Add the algorithm identifier to `lib/AlgorithmSelection.groovy`.
   * Define the process in `modules/local/lesion_segmentation.nf` using the DockerHub image as `container`.
   * Add process routing to `nextflow.config` and `conf/base.config`.
   * Add the image to `PUBLIC_IMAGES` in `dockerfiles/build_offline_containers.sh`.
