# Container Recipes & Build Registry for sf-lesionflow

This directory centralizes the Dockerfiles, build recipes, and container provenance documentation for all 13 lesion segmentation algorithms integrated into `sf-lesionflow`.

---

## 1. Master Container Registry

| Pipeline Process | Directory | Current Container Image | Future GHCR Image | Build Type | Model Weights Sourcing |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SEGMENTATION_LST_AI` | [`lst_ai/`](lst_ai/) | `ms_chus/lst_ai:latest` | `ghcr.io/scilus/sf-lesionflow-lst_ai:1.1.0` | Custom Dockerfile | Auto-fetched from [GitHub Releases](https://github.com/CompImg/LST-AI/releases/download/v1.0.0/lst_data.zip) |
| `SEGMENTATION_FLAMES` | [`flames/`](flames/) | `ms_chus/flames:latest` | `ghcr.io/scilus/sf-lesionflow-flames:1.0.0` | Custom Dockerfile | Auto-fetched from [Zenodo Record 17955359](https://zenodo.org/records/17955359/files/Dataset004_WML.zip) |
| `SEGMENTATION_TRUENET` | [`truenet/`](truenet/) | `ms_chus/truenet:latest` | `ghcr.io/scilus/sf-lesionflow-truenet:1.0.0` | Custom Dockerfile | **Pre-download required** ([Google Drive](https://drive.google.com/drive/folders/1iqO-hd27NSHHfKun125Rt-2fh1l9EiuT)) |
| `SEGMENTATION_FAST_OUTLIER` | [`fast_outlier/`](fast_outlier/) | `ms_chus/fast_outlier:latest` | `ghcr.io/scilus/sf-lesionflow-fast_outlier:1.0.0` | Custom Dockerfile | None (Unsupervised FSL + Python math) |
| `SEGMENTATION_WMH_SYNTHSEG` | [`wmh_synthseg/`](wmh_synthseg/) | `ms_chus/wmh_synthseg:latest` | `ghcr.io/scilus/sf-lesionflow-wmh_synthseg:1.0.0` | Custom Dockerfile | Auto-fetched from [GitHub](https://github.com/lasopablo/freesurfer-freesurfer-dev-mri_WMHsynthseg) + [MGH FTP](https://ftp.nmr.mgh.harvard.edu/pub/dist/lcnpublic/dist/WMH-SynthSeg/WMH-SynthSeg_v10_231110.pth), on `freesurfer/freesurfer:7.4.1` (x86_64) |
| `SEGMENTATION_EMORY_ROBUST` | [`emory_robust/`](emory_robust/) | `emorycn2l/emory_robust_wmh:v1.2` | `ghcr.io/scilus/sf-lesionflow-emory_robust:1.2` | Upstream Public | Pre-baked in DockerHub image (~25 GB) |
| `SEGMENTATION_MARS_WMH` | [`mars_wmh/`](mars_wmh/) | `ghcr.io/miac-research/wmh-nnunet:latest` | `ghcr.io/scilus/sf-lesionflow-mars_wmh:1.0.0` | Upstream Public | Pre-baked in MIAC GHCR image |
| `SEGMENTATION_HYPERMAPP3R` | [`hypermapp3r/`](hypermapp3r/) | `mgoubran/hypermapper:latest` | `ghcr.io/scilus/sf-lesionflow-hypermapp3r:1.0.0` | Upstream Public | Pre-baked in DockerHub image |
| `SEGMENTATION_SAMSEG` | [`samseg/`](samseg/) | `freesurfer/freesurfer:7.4.1` | `ghcr.io/scilus/sf-lesionflow-samseg:7.4.1` | Upstream Public | Pre-baked in official FreeSurfer image |
| `SEGMENTATION_SEGCSVD` | [`segcsvd/`](segcsvd/) | `segcsvd_rc03:latest` | `ghcr.io/scilus/sf-lesionflow-segcsvd:rc03` | Pre-built / Local | Pre-baked in local host image |
| `SEGMENTATION_BAWIL` | [`bawil/`](bawil/) | `ms_chus/bawil:latest` | `ghcr.io/scilus/sf-lesionflow-bawil:1.0.0` | Custom Dockerfile | Auto-fetched from [Hugging Face](https://huggingface.co/Bawil/wmh_leverage_normal_abnormal_segmentation) |
| `SEGMENTATION_MIMOSA` | [`mimosa/`](mimosa/) | `ms_chus/mimosa:latest` | `ghcr.io/scilus/sf-lesionflow-mimosa:1.0.0` | Custom Dockerfile | Real pretrained model (`mimosa_model_No_PD_T2`) bundled in the `mimosa` R package, on `adigherman/neuroconductor-release` |
| `SEGMENTATION_SHIVAI` | [`shivai/`](shivai/) | `ms_chus/shivai:latest` | `ghcr.io/scilus/sf-lesionflow-shivai:1.0.0` | Custom Dockerfile | **Manual download required** ([cloud.efixia.com](https://cloud.efixia.com/sharing/cpb3eUvMa), no scriptable source) |

---

## 2. Build Instructions for Custom Containers

### A. FLAMeS (`ms_chus/flames:latest`)
Downloads PyTorch CPU and automatically pulls the 5-fold FLAMeS weights from Zenodo:
```bash
docker build -t ms_chus/flames:latest dockerfiles/flames/
```

### B. LST-AI (`ms_chus/lst_ai:latest`)
Downloads LST-AI v1.1.0 and pulls models/atlases directly from GitHub Releases:
```bash
docker build -t ms_chus/lst_ai:latest dockerfiles/lst_ai/
```

### C. TrueNet (`ms_chus/truenet:latest`)
TrueNet models are hosted on Google Drive. To prevent Google Drive rate-limits during automated Docker builds, download the weights into the build context first:
```bash
# 1. Install gdown if needed
pip install gdown

# 2. Download the Oxford TrueNet model weights (MWSC_FLAIR_T1, etc.)
gdown --folder https://drive.google.com/drive/folders/1iqO-hd27NSHHfKun125Rt-2fh1l9EiuT -O dockerfiles/truenet/models

# 3. Build the Docker image
docker build -t ms_chus/truenet:latest dockerfiles/truenet/
```
*(Note: `dockerfiles/truenet/models/` is git-ignored so weights are never committed).*

### D. FAST Outlier (`ms_chus/fast_outlier:latest`)
Unsupervised physics-based segmentation using FSL and numpy/scipy:
```bash
docker build -t ms_chus/fast_outlier:latest dockerfiles/fast_outlier/
```

### E. WMH-SynthSeg (`ms_chus/wmh_synthseg:latest`)
Builds on `freesurfer/freesurfer:7.4.1`; git-clones the upstream WMH-SynthSeg
source and fetches the pre-trained weights from the official MGH FTP server
(**not** `pablaso/wmh_synthseg:latest`: that upstream image is arm64-only and
fails with `exec format error` on x86_64 hosts; see
[`wmh_synthseg/README.md`](wmh_synthseg/)):
```bash
docker build -t ms_chus/wmh_synthseg:latest dockerfiles/wmh_synthseg/
```

### F. MIMoSA (`ms_chus/mimosa:latest`)
Real, pretrained model (the `mimosa` R package's own `mimosa_model_No_PD_T2`),
on top of `adigherman/neuroconductor-release` (R + FSL + Neuroconductor
already bundled, `mimosa` package pre-installed). No weights to fetch, no
build steps beyond pulling the base and tagging it:
```bash
docker build -t ms_chus/mimosa:latest dockerfiles/mimosa/
```

### G. BAWIL (`ms_chus/bawil:latest`)
Real, pretrained Keras model, weights auto-fetched from Hugging Face
(unauthenticated). See [`bawil/README.md`](bawil/) for why `tensorflow` and
`numpy` are pinned together deliberately:
```bash
docker build -t ms_chus/bawil:latest dockerfiles/bawil/
```

### H. SHiVAi (`ms_chus/shivai:latest`)
Real, pretrained 5-fold TensorFlow SavedModel ensemble. **Weights must be
downloaded manually first.** See [`shivai/README.md`](shivai/) for the
download link, SHA256 checksum to verify, and exact folder layout expected
under `dockerfiles/shivai/models/` before building:
```bash
docker build -t ms_chus/shivai:latest dockerfiles/shivai/
```

---

## 3. Pulling Upstream Public Images

The remaining algorithms run official, pre-compiled container images:

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

## 4. Future GitHub Container Registry (GHCR) Hosting

In future releases, all custom images will be automatically built and published to the GitHub Container Registry under the `ghcr.io/scilus/` organization:

* Tagging convention: `ghcr.io/scilus/sf-lesionflow-<algorithm>:<version>`
* Authentication:
  ```bash
  echo $CR_PAT | docker login ghcr.io -u <USERNAME> --password-stdin
  ```
* Automated GitHub Action: Any push or pull request modifying `dockerfiles/<algorithm>/**` triggers an automated build and smoke test.

---

## 5. Standard Operating Procedure (SOP): Adding a New Algorithm

When adding a 14th algorithm to `sf-lesionflow`, follow these steps:

1. **Create Subdirectory**:
   Create a folder matching the algorithm name in lowercase snake_case:
   ```bash
   mkdir -p dockerfiles/<new_algo>/
   ```

2. **Add Dockerfile & Sourcing**:
   * If creating a custom image: add `dockerfiles/<new_algo>/Dockerfile`. Ensure model weights are fetched via `wget` / `curl` from a permanent public URL (Zenodo, OSF, Hugging Face, or GitHub Releases).
   * If using a pre-existing image: add `dockerfiles/<new_algo>/README.md` documenting the registry source, size, base image, and citations.

3. **Update this Master README**:
   * Add the new process to the **Master Registry Table** in Section 1.
   * Add its `docker build` command to Section 2 or pull command to Section 3.

4. **Wire into Nextflow**:
   * Add the algorithm key to `lib/AlgorithmSelection.groovy` (in `ALL`).
   * Define the process in `modules/local/lesion_segmentation.nf` pointing to the new container.
   * Add the process routing to `nextflow.config` and `conf/base.config`.
