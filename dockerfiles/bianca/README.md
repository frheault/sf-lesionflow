# BIANCA — Evaluated, Not Integrated

## What it is
BIANCA (Brain Intensity AbNormality Classification Algorithm) is FSL's supervised
k-nearest-neighbor classifier for white matter hyperintensity segmentation.
https://fsl.fmrib.ox.ac.uk/fsl/docs/structural/bianca.html

## Why it is not wired into sf-lesionflow

Every one of the 14 ensemble members in this pipeline runs a published, pretrained
model out of the box (see the Algorithm Provenance Notice in the top-level README and
the closing line of CITATIONS.md). BIANCA cannot meet that bar as shipped:

- BIANCA is a k-NN classifier, not a model with fixed learned weights — it requires a
  training set of manually-labeled lesion masks (via `--trainingnums`/
  `--labelfeaturenum`), or a pre-trained classifier loaded via `--loadclassifierdata`.
- FSL itself ships no bundled pretrained classifier for BIANCA.
- The only pretrained classifier data referenced anywhere (derived from UK Biobank
  and Whitehall II) comes from access-restricted cohort studies. It is not publicly
  redistributable, so it cannot be baked into a public Docker image the way every
  other algorithm's weights are in this repo's dockerfiles/.
- The only ways to make BIANCA runnable on this pipeline's `data/` out of the box would
  be to (a) require the user to separately/legitimately obtain and supply their own
  trained classifier file, or (b) train it against this pipeline's own data using
  STAPLE consensus output as pseudo-labels (no manual ground truth exists in `data/`).
  Option (b) would no longer be running "the published pretrained model" — it would be
  a self-supervised proxy, and a weak one with only 2 subjects.

## Decision

Skip BIANCA; document the reasoning here rather than adding a half-integrated stub.
`TrueNet` (`SEGMENTATION_TRUENET`, Sundaresan et al. 2021) is BIANCA's own official
deep-learning successor from the same Oxford/FSL group and is already an active
ensemble member — the methodological lineage BIANCA represents is already covered.

## If this is revisited later

If you have legitimate access to a pretrained BIANCA classifier (e.g. your own trained
classifier from labeled data you're licensed to use), the integration would look like:
add `dockerfiles/bianca/Dockerfile` (FSL is already containerized elsewhere in this
repo — see `dockerfiles/fast_outlier/Dockerfile`, built on `brainlife/fsl:6.0.4-patched`,
which already has FSL's BIANCA binary), add a `--bianca_classifier_data` pipeline
parameter pointing at your classifier files, and error clearly if it isn't set rather
than silently training on pipeline data.
