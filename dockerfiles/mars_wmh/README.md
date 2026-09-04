# MARS-WMH (02n_mars_wmh.sh) — GHCR Container Image

## Container Info

```
ghcr.io/miac-research/wmh-nnunet:latest
```

Hosted on GitHub Container Registry (GHCR). A 2025 nnU-Net deep learning tool for White Matter Hyperintensities of presumed vascular origin.

## Citation
Gesierich et al. (2025). *Technical and Clinical Validation of a Novel Deep Learning-Based White Matter Hyperintensity Segmentation Tool*. Cereb Circ Cogn Behav. DOI: 10.1016/j.cccb.2025.100393.

## Verified Usage Command

```bash
DATA=/path/to/derivatives/sub-XXX

docker run --rm \
    -u $(id -u):$(id -g) \
    --memory="8g" \
    --cpuset-cpus="0-3" \
    -v "${DATA}:/data" \
    ghcr.io/miac-research/wmh-nnunet:latest \
    --flair /data/sub-XXX_ses-Y_FLAIR_space-MNI.nii.gz \
    --t1 /data/sub-XXX_ses-Y_T1w_space-MNI.nii.gz \
    --fnOut /data/mars_wmh/sub-XXX_ses-Y_mars_binary.nii.gz \
    --skipRegistration \
    --omitQC \
    -x
```

## Flags Reference

| Flag | Purpose |
|------|---------|
| `-u $(id -u):$(id -g)` | **Required**: Runs container as current user to fix file permission checks |
| `--flair <file>` | Double-dash required (`--flair`, NOT `-flair`) |
| `--t1 <file>` | Double-dash required (`--t1`, NOT `-t1`) |
| `--fnOut <file>` | Absolute path to output binary lesion mask |
| `--skipRegistration` | **Required**: Skips internal registration since Phase 1 already co-registered scans into MNI space |
| `--omitQC` | Disables HTML quality control report generation |
| `-x` | Overwrite existing output file if present |

## Hardware Requirements
- **GPU**: Heavily optimized for NVIDIA GPUs (CUDA compute capability >= 5.0).
- **CPU Fallback**: Natively supports CPU inference if >8 cores are provided (`--cpuset-cpus="0-7"`).
