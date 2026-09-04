# BAWIL (`SEGMENTATION_BAWIL`)

## What this runs

Bashiri Bawil M, Shamsi M, Shakeri Bavil A. *Adversarial Deep Learning for
Simultaneous Segmentation of Ventricular and White Matter Hyperintensities in
Clinical MRI*. arXiv:2506.07123, 2025. https://doi.org/10.48550/arXiv.2506.07123

Weights: `Bawil/wmh_leverage_normal_abnormal_segmentation` on Hugging Face
(`unet/models/scenario2_multiclass_model.h5`, a Keras U-Net, 3-class softmax
over 256x256 axial FLAIR slices, background / normal periventricular WMH /
abnormal WMH). Freely downloadable, no account or token needed (verified: a
~373MB HDF5 file, not a git-lfs pointer stub).

> **No official NIfTI inference code exists upstream.** The paper's own repo
> (`github.com/Mahdi-Bashiri/wmh-normal-abnormal-segmentation`) is a research
> training/eval harness operating on pre-extracted 256x512 PNG slices
> (FLAIR|mask side by side), not a deployable CLI. `bin/bawil_filter.py`
> reimplements the harness's own preprocessing (per-slice z-score
> normalization, resize to 256x256) from its source code, applied slice-by-slice
> to a 3D NIfTI volume. Axial slice orientation was confirmed by downloading
> and visually inspecting one of the paper's own training samples
> (`data/train/101228_10.png`), not assumed.

## Container Info

```
ms_chus/bawil:latest
```

`python:3.10-slim` + `tensorflow==2.11.1` + `numpy==1.23.5` (pinned together
deliberately, installing `tensorflow==2.11.1` with pip's own numpy resolution
pulls numpy 2.x, which cannot load this TF build: `_ARRAY_API not found`,
confirmed by actually hitting that error) + `opencv-python-headless` (for the
same `cv2.resize` the paper's own preprocessing uses) + `nibabel`.

## Build

```bash
docker build -t ms_chus/bawil:latest dockerfiles/bawil/
```

After building, verify the model actually loads and predicts (not run
automatically as part of the build -- see validate.py in this directory):
```bash
docker run --rm -v $(pwd)/dockerfiles/bawil/validate.py:/tmp/validate.py \
    ms_chus/bawil:latest python3 /tmp/validate.py
```

## What `bin/bawil_filter.py` does

See `SEGMENTATION_BAWIL` in `modules/local/lesion_segmentation.nf` for the
exact invocation and flag defaults. The script, per axial slice:

1. Resizes the slice to 256x256 (`cv2.resize`, matching the paper's own code).
2. Z-score normalizes that slice only (mean/std computed per-slice, matching
   the paper's own per-slice normalization, not a whole-volume statistic).
3. Runs the model, takes the class-2 (abnormal WMH) softmax probability.
4. Resizes the continuous probability map back to native resolution (not the
   argmax'd label, smoother boundaries), thresholds, then drops connected
   components smaller than `--min_cluster_size`.

This was verified end-to-end (the exact bare `bawil_filter.py` invocation
Nextflow uses, under the same non-root UID Nextflow runs containers as)
against a synthetic 3D volume before being wired into the pipeline.

## Output Target
`${DERIV_DIR}/bawil/${SUBJECT_ID}_${ses}_bawil_binary.nii.gz`
