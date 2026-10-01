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

## ⚠ Output-path quirk of `segment_wmh` (soft map overwritten)

`/seg/tools/segment_wmh` writes the soft probability map to `<3>` and then its own binary to
`$(echo <3> | sed "s/\/outdir\//\/outdir\/thr_/")`. If `<3>` does not contain `/outdir/`
(e.g. a bare `prob.nii.gz`, or the `/data/segcsvd/...` example above) the two paths are
identical and **the binary overwrites the soft map**. `SEGMENTATION_SEGCSVD` therefore passes
an absolute path under a directory literally named `outdir` (`$PWD/outdir/prob.nii.gz` →
binary at `$PWD/outdir/thr_prob.nii.gz`), fails if the map is not soft, and thresholds the
soft map itself at `ext.threshold` (0.35). Verified on sub-007_ses-1: 210 distinct non-zero
probability values, binary identical (2278 voxels) to the previous run.

## Technical Notes
- **Prerequisite**: Requires native FreeSurfer SynthSeg output (`mri_synthseg --crop 160`) generated beforehand into `synthseg_native/`.
- **Image location**: Stored locally on host daemon as `segcsvd_rc03:latest`.
