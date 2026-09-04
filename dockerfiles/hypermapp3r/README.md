# HyperMapp3r (02i_hypermapp3r.sh) — Public Docker Image

## Docker Image

```
mgoubran/hypermapper:latest
```

Public image maintained on DockerHub (`mgoubran/hypermapper`). It is fully self-contained with deep learning models baked in for White Matter Hyperintensity (WMH) segmentation.

## Usage in Pipeline

```bash
DATA=/path/to/derivatives/sub-XXX

docker run --rm \
    --memory="8g" \
    --cpuset-cpus="0-3" \
    -v "${DATA}:/data" \
    mgoubran/hypermapper:latest \
    hypermapper seg_wmh \
    -t1 /data/sub-XXX_ses-Y_T1w_space-MNI.nii.gz \
    -fl /data/sub-XXX_ses-Y_FLAIR_space-MNI.nii.gz \
    -m /data/sub-XXX_ses-Y_T1w_space-MNI_brain_mask.nii.gz \
    -o /data/hypermapp3r/sub-XXX_ses-Y_hypermapp3r_prob.nii.gz \
    -f

# Binarize output at 0.5 threshold:
fslmaths /data/hypermapp3r/sub-XXX_ses-Y_hypermapp3r_prob.nii.gz -thr 0.5 -bin /data/hypermapp3r/sub-XXX_ses-Y_hypermapp3r_binary.nii.gz
```

## Technical Notes
- **Inputs**: Requires coregistered T1w, FLAIR, and binary brain mask in MNI space.
- **Output**: Generates a continuous probability map `_prob.nii.gz`. Binarized at 0.5 for consensus fusion.
