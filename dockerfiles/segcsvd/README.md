# segCSVD (02j_segcsvd.sh) — Pre-existing Local Image

## Docker Image

```
segcsvd_rc03:latest
```

This is a pre-existing 17.8 GB local Docker image available directly on the host machine (`segcsvd_rc03:latest`).

## Usage in Pipeline

```bash
DATA=/path/to/derivatives/sub-XXX

docker run --rm \
    --memory="8g" \
    --cpuset-cpus="0-3" \
    -v "${DATA}:/data" \
    -w / \
    segcsvd_rc03:latest \
    segment_wmh \
    /data/sub-XXX_ses-Y_FLAIR_space-MNI.nii.gz \
    /data/synthseg_native/sub-XXX_ses-Y_synthseg.nii.gz \
    /data/segcsvd/sub-XXX_ses-Y_segcsvd_prob.nii.gz \
    1 \
    "96,128" \
    0.5 \
    1 \
    true \
    true

# Binarize output at 0.5 threshold:
fslmaths /data/segcsvd/sub-XXX_ses-Y_segcsvd_prob.nii.gz -thr 0.5 -bin /data/segcsvd/sub-XXX_ses-Y_segcsvd_binary.nii.gz
```

## Technical Notes
- **Prerequisite**: Requires native FreeSurfer SynthSeg output (`mri_synthseg --crop 160`) generated beforehand into `synthseg_native/`.
- **Image location**: Stored locally on host daemon as `segcsvd_rc03:latest`.
