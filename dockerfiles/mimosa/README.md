# MIMoSA (`SEGMENTATION_MIMOSA`)

## What this runs

Valcarcel AM, Linn KA, Vandekar SN, Satterthwaite TD, Muschelli J, Calabresi
PA, et al. *MIMoSA: An Automated Method for Intermodal Segmentation Analysis
of Multiple Sclerosis Brain Lesions*. Journal of Neuroimaging, 28(4):389-398,
2018. https://doi.org/10.1111/jon.12506

Uses the pretrained `mimosa_model_No_PD_T2` model shipped inside the `mimosa`
R package itself (fitted on FLAIR + T1, matching this pipeline's inputs
exactly): a fitted logistic regression on multiscale intensity/coupling
features. No training data is required at runtime.

## Container Info

```
ms_chus/mimosa:latest
```

Built directly on `adigherman/neuroconductor-release`, which already bundles
R 4.0.0, FSL 6.0.3, and every Neuroconductor dependency the `mimosa` package
needs (`ANTsRCore`, `ANTsR`, `extrantsr`, `fslr`, `neurobase`, `oro.nifti`,
`WhiteStripe`, `oasis`, `mmand`), and the `mimosa` package itself is already
installed. No custom build steps needed beyond pulling this base and tagging
it; the Dockerfile in this directory exists purely to document the pin and
provenance.

## Build

```bash
docker build -t ms_chus/mimosa:latest dockerfiles/mimosa/
```

## What `bin/mimosa_predict.R` does

See `SEGMENTATION_MIMOSA` in `modules/local/lesion_segmentation.nf` for the
exact invocation and flag defaults. The script itself does, in order, exactly
what the package's
own vignette (`mimosa.Rmd`) documents for applying a pretrained model:

1. Derive a brain mask as the union of nonzero voxels across T1/FLAIR (the
   pipeline's inputs already arrive skull-stripped, so this just recovers the
   existing brain footprint, same convention the vignette's own
   `create_brain_mask()` helper uses).
2. `mimosa_data(..., normalize = "Z")` to build the candidate-voxel feature
   `data.frame`.
3. `predict(mimosa_model_No_PD_T2, newdata = ..., type = "response")` for the
   per-voxel lesion probability.
4. `fslsmooth(..., sigma = 1.25)` to smooth the probability map.
5. Threshold at `--prob_threshold`, then drop connected components smaller
   than `--min_cluster_size`.

> **Note on the threshold default**: the package vignette only documents an
> optimal-threshold search range of `[0.25, 0.35]` for the *full*
> (FLAIR+T1+T2+PD) model trained from scratch on labeled data. There is no
> published default specifically for the pretrained FLAIR+T1-only model used
> here. `0.30` (the midpoint of that range) is used as a reasonable default.
> Treat it as a starting point to tune, not a validated optimum.

This was verified end-to-end against synthetic T1/FLAIR volumes before being
wired into the pipeline (both via a direct `Rscript` call and via the bare
`mimosa_predict.R` invocation Nextflow actually uses), producing a valid
binary NIfTI mask.

## Output Target
`${DERIV_DIR}/mimosa/${SUBJECT_ID}_${ses}_mimosa_binary.nii.gz`
