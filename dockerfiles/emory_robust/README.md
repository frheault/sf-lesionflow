# Emory Robust WMH (02l_emory_robust.sh) — DockerHub Image

## Container Info

```
emorycn2l/emory_robust_wmh:v1.2
```

> **⚠️ DISK SPACE WARNING**: This image is exceptionally large (**~25 GB**). Ensure at least 30 GB of free disk space before pulling.

Note: There is **no `latest` tag**. You MUST explicitly specify `v1.2`.

## Citation
Wu, J., et al. (2026). *Benchmark white matter hyperintensity segmentation methods fail on heterogeneous clinical MRI: A new dataset and deep learning-based solutions*. Journal of Imaging Informatics in Medicine.

## Usage in Pipeline

```bash
DATA=/path/to/derivatives/sub-XXX

docker run --rm \
    --memory="8g" \
    --cpuset-cpus="0-3" \
    -v "${DATA}:/data" \
    emorycn2l/emory_robust_wmh:v1.2 \
    /data/sub-XXX_ses-Y_T1w_space-MNI.nii.gz \
    /data/sub-XXX_ses-Y_FLAIR_space-MNI.nii.gz \
    /data/emory_robust/sub-XXX_ses-Y_emory_binary.nii.gz
```

## Technical Notes
- **Registry**: DockerHub (`emorycn2l/emory_robust_wmh:v1.2`).
- **Inputs**: Requires both co-registered `T1w` and `FLAIR` images.
- **Robustness**: Trained on 195 clinical examinations across 71 different MRI scanners for maximum generalization on heterogeneous clinical data.
