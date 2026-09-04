# SHIVA-WMH (`SEGMENTATION_SHIVAI`): Real, Pretrained Model (manual weights)

## What this actually is

This runs the real, published SHIVA-WMH detector: Tsuchida A, Boutinaud P,
Verrecchia V, Tzourio C, Debette S, Joliot M. *Early detection of white
matter hyperintensities using SHIVA-WMH detector*. Human Brain Mapping,
45(1):e26548, 2024. https://doi.org/10.1002/hbm.26548

Model: v2/T1+FLAIR-WMH from github.com/pboutinaud/SHIVA_WMH, a 5-fold
TensorFlow SavedModel ResUnet3D ensemble. Verified directly (real model, real
prediction): input signature is a fixed `(None, 160, 214, 176, 2)` float32
tensor (T1 + FLAIR as 2 channels), output `(None, 160, 214, 176, 1)`.

## Weights: manually downloaded, not scriptable

Every other custom Dockerfile in this repo fetches weights from a scriptable
public URL. This one can't: the weights are hosted on a personal Synology NAS
share (`cloud.efixia.com/sharing/cpb3eUvMa`) with no stable unauthenticated
download endpoint, confirmed directly (the share's FileStation API requires
a real browser session, not a `wget`/`curl` one-liner).

**Before building**, download `T1.FLAIR-WMH.zip` yourself from
https://cloud.efixia.com/sharing/cpb3eUvMa, verify its integrity, and unzip
it into place:

```bash
# Verify BEFORE trusting the file (checksum from model_info_t1-flair-wmh-v2.json
# in the SHIVA_WMH repo):
sha256sum T1.FLAIR-WMH.zip
# Expected: b2fe8d18fc62f4b1a447f0ef571781cf7656d808bd76a28c4b0cf53bdd391e3b

mkdir -p dockerfiles/shivai/models
unzip T1.FLAIR-WMH.zip -d dockerfiles/shivai/models/
# Should produce: dockerfiles/shivai/models/T1.FLAIR-WMH/<5 fold_*.tf_inference dirs>
```

`dockerfiles/shivai/models/` is git-ignored (same pattern as
`dockerfiles/truenet/models/`), weights are never committed.

## Container Info

```
ms_chus/shivai:latest
```

`python:3.12-slim` + `tensorflow>=2.17` (confirmed working with TF 2.21) +
`nibabel`, with the 5 fold directories baked in via `COPY`.

## Build

```bash
docker build -t ms_chus/shivai:latest dockerfiles/shivai/
```

The build itself smoke-tests all 5 folds (loads each real SavedModel and runs
a prediction, asserting the expected `(1, 160, 214, 176, 1)` output shape)
before the image is considered built.

## What `bin/shivai_predict.py` actually does

See `SEGMENTATION_SHIVAI` in `modules/local/lesion_segmentation.nf` for the
exact invocation and flag defaults. The upstream repo ships a real, usable
`predict_one_file.py` CLI, but it requires inputs already at the model's
fixed 160x214x176 shape ("for now, you will have to do it yourself" per its
own README). This pipeline's inputs are already-skull-stripped, MNI-space
volumes at a different native shape (e.g. 193x229x193 for the 1mm MNI152
template used here), so `bin/shivai_predict.py` adds the missing piece:

1. Min-max normalize each of T1/FLAIR independently, with max = the 99th
   percentile of nonzero (brain) voxel values, the upstream README's exact
   documented recipe.
2. Center-crop (or zero-pad, if ever smaller) to 160x214x176.
3. Stack as 2 channels, run the real 5-fold SavedModel ensemble, average.
4. Threshold at `--prob_threshold` (default 0.50, the value the upstream
   README reports using successfully).
5. Paste the result back into the native shape/affine, so it aligns with
   every other algorithm's output mask for STAPLE fusion.

This was verified end-to-end (real 5-fold ensemble, real container, the
exact bare `shivai_predict.py` invocation Nextflow uses) against a synthetic
193x229x193 volume before being wired into the pipeline.

## Technical Notes

- **License**: CC BY-NC-SA (non-commercial) per the SHIVA_WMH repo, which
  also states explicitly: "inferences... should not be used for clinical
  purposes."
- **CPU vs GPU**: CPU inference works (confirmed) but the upstream README
  recommends a 9GB-VRAM GPU for speed.

## Output Target
`${DERIV_DIR}/shivai/${SUBJECT_ID}_${ses}_shivai_binary.nii.gz`
