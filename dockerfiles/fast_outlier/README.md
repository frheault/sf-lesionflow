# FSL FAST Outlier (`SEGMENTATION_FAST_OUTLIER`): Custom Dockerfile

## Tool Description

Unsupervised, physics-based outlier detector: no trained model, no external weights.
`bin/fast_outlier.py` flags FLAIR voxels that are statistical outliers (>N SD above the
mean) relative to FSL's own white-matter partial-volume-estimate map.

FSL only. **No FreeSurfer/SynthSeg dependency**.

## Build

```bash
docker build -t ms_chus/fast_outlier:latest dockerfiles/fast_outlier/
```

The image provides `brainlife/fsl:6.0.4-patched` (for `fast`) plus Python +
nibabel/numpy/scipy (for `bin/fast_outlier.py`'s imports). `fast_outlier.py` itself is
**not** copied into the image. Nextflow resolves it from the pipeline's own `bin/`
directory, which it automatically adds to `PATH` for every process.

See `SEGMENTATION_FAST_OUTLIER` in `modules/local/lesion_segmentation.nf` for
the exact invocation and flag defaults.

## Output Target
`${DERIV_DIR}/fast_outlier/${SUBJECT_ID}_${ses}_fast-outlier_binary.nii.gz`
