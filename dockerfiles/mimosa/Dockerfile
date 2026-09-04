# =============================================================================
# Docker image: MIMoSA (real, pretrained -- not a heuristic proxy)
# Tool:   MIMoSA -- Method for Inter-Modal Segmentation Analysis
# Paper:  Valcarcel AM, et al. 2018, Journal of Neuroimaging
# Repo:   https://github.com/avalcarcel9/mimosa
# Runtime: SEGMENTATION_MIMOSA in modules/local/lesion_segmentation.nf
# =============================================================================
#
# WHY THIS BASE IMAGE
# --------------------
# `adigherman/neuroconductor-release` already bundles R 4.0.0, FSL 6.0.3, and
# every Neuroconductor dependency the `mimosa` R package needs (ANTsRCore,
# ANTsR, extrantsr, fslr, neurobase, oro.nifti, WhiteStripe, oasis, mmand) --
# and the `mimosa` package itself is already installed in it. Verified by
# actually running `bin/mimosa_predict.R` end-to-end inside this image against
# synthetic data before wiring it into Nextflow; no build step is needed here
# beyond pulling the base image.
#
# WHAT THIS ACTUALLY RUNS
# -------------------------
# `bin/mimosa_predict.R` uses the package's own pretrained model,
# `mimosa_model_No_PD_T2` (trained for FLAIR + T1 only, matching this
# pipeline's inputs exactly) -- a real fitted logistic regression on
# multiscale intensity/coupling features, NOT hardcoded coefficients. No
# training data is required at runtime.
#
# USAGE
# -----
#   docker pull adigherman/neuroconductor-release
#   docker tag adigherman/neuroconductor-release ms_chus/mimosa:latest
#
# (No custom build: this Dockerfile exists only to document the pin and
# provenance. If you need to add anything on top in the future, `FROM` this
# image and layer your changes.)
# =============================================================================

FROM adigherman/neuroconductor-release

LABEL maintainer="ms_chus_pipeline"
LABEL tool="MIMoSA"
LABEL source="https://github.com/avalcarcel9/mimosa"
LABEL paper_doi="10.1111/jon.12506"
