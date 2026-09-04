# =============================================================================
# Docker image: SHIVA-WMH (real, pretrained -- not a heuristic proxy)
# Tool:   SHIVA-WMH detector, v2/T1+FLAIR-WMH (5-fold ResUnet3D ensemble)
# Paper:  Tsuchida A, Boutinaud P, et al., doi:10.1002/hbm.26548
# Repo:   https://github.com/pboutinaud/SHIVA_WMH
# Runtime: SEGMENTATION_SHIVAI in modules/local/lesion_segmentation.nf
# =============================================================================
#
# WHY THIS ISN'T "REBUILD ANYWHERE, NO LOCAL FILES NEEDED"
# Every other custom Dockerfile in this repo fetches its weights from a
# scriptable public URL (GitHub Releases, Zenodo, MGH FTP, Hugging Face).
# SHIVA-WMH's weights are hosted on a personal Synology NAS share
# (cloud.efixia.com/sharing/cpb3eUvMa) with no stable, unauthenticated,
# scriptable download endpoint -- confirmed directly: the share's FileStation
# API requires a real browser session, not a `wget`/`curl` one-liner.
# The weights were downloaded manually and are expected at
# dockerfiles/shivai/models/T1.FLAIR-WMH/ (git-ignored, same pattern as
# dockerfiles/truenet/models/). If that directory is missing, download
# T1.FLAIR-WMH.zip from https://cloud.efixia.com/sharing/cpb3eUvMa (verify
# SHA256 B2FE8D18FC62F4B1A447F0EF571781CF7656D808BD76A28C4B0CF53BDD391E3B,
# from model_info_t1-flair-wmh-v2.json in the SHIVA_WMH repo), unzip it, and
# place the extracted T1.FLAIR-WMH/ folder here before building. Only copy in
# the 5 real fold_*.tf_inference directories -- nothing else (an accidental
# stray directory with restrictive permissions caused a real runtime failure
# once already; bin/shivai_predict.py now tolerates unreadable siblings, but
# don't rely on that, keep this folder clean).
#
# WHAT THIS ACTUALLY RUNS
# `bin/shivai_predict.py` -- verified directly against the real SavedModel:
# input signature is a fixed (None, 160, 214, 176, 2) float32 tensor
# (T1 + FLAIR as 2 channels), output (None, 160, 214, 176, 1). Since this
# pipeline's inputs are already-skull-stripped MNI-space volumes at a
# different native shape, the script center-crops/pads to 160x214x176,
# min-max normalizes per the upstream README's exact recipe (max = 99th
# percentile of nonzero/brain voxels), runs the real 5-fold ensemble,
# averages, thresholds, then pastes the result back into the native shape
# so it aligns with every other algorithm's output mask.
#
# USAGE
#   docker build -t ms_chus/shivai:latest .
#
# After building, verify all 5 folds actually load and predict (not run
# automatically as part of the build -- see validate.py in this directory):
#   docker run --rm -v $(pwd)/dockerfiles/shivai/validate.py:/tmp/validate.py \
#       ms_chus/shivai:latest python3 /tmp/validate.py
#
# NOTES
# - CPU inference works (confirmed: TF 2.21 loads and runs this SavedModel on
#   CPU) but is slower than GPU; the upstream README recommends a 9GB-VRAM
#   GPU. `--gpu -1` equivalent behavior here (no CUDA_VISIBLE_DEVICES set to
#   a real GPU) is the default.
# - License: CC BY-NC-SA (non-commercial) per the SHIVA_WMH repo. The repo
#   also states explicitly: "inferences... should not be used for clinical
#   purposes."
# =============================================================================

FROM python:3.12-slim

LABEL maintainer="ms_chus_pipeline"
LABEL tool="SHIVA-WMH"
LABEL source="https://github.com/pboutinaud/SHIVA_WMH"
LABEL paper_doi="10.1002/hbm.26548"
LABEL weights_sha256="B2FE8D18FC62F4B1A447F0EF571781CF7656D808BD76A28C4B0CF53BDD391E3B"

# 1. Python dependencies. scipy/scikit-image are for bin/shivai_predict.py's
# use of bin/_lesion_utils.py's filter_small_components() (--min_cluster_size).
RUN pip install --no-cache-dir \
        "tensorflow>=2.17" \
        "nibabel" \
        "scipy" \
        "scikit-image"

# 2. Copy the manually-downloaded, checksum-verified model weights
COPY models/T1.FLAIR-WMH /opt/shivai/T1.FLAIR-WMH

# 3. procps (provides `ps`, required by Nextflow's task metrics collector)
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

# No ENTRYPOINT: Nextflow's global --entrypoint "" override makes this moot
# during pipeline runs, but declaring one anyway breaks manual `docker run
# ms_chus/shivai:latest python3 ...` invocations (bash would try to source
# "python3" as a script and fail with "cannot execute binary file").
