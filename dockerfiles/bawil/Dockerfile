# =============================================================================
# Docker image: BAWIL
# Tool:   BAWIL -- 3-class WMH segmentation (normal vs abnormal periventricular)
# Paper:  Bashiri Bawil M, Shamsi M, Shakeri Bavil A, arXiv:2506.07123
# Model:  huggingface.co/Bawil/wmh_leverage_normal_abnormal_segmentation
# Runtime: SEGMENTATION_BAWIL in modules/local/lesion_segmentation.nf
# =============================================================================
#
# DESIGN PHILOSOPHY -- "rebuild anywhere, no local files needed"
# Weights are fetched at build time from Hugging Face's unauthenticated
# resolve URL (verified: 372,598,224 bytes, a real HDF5 file, not a git-lfs
# pointer stub). No account/token needed.
#
# WHY tensorflow==2.15.1, not the paper's exact tensorflow==2.11.1
# The model was trained/exported with tensorflow==2.11.1 (paper repo's
# requirements.txt), but pip's tensorflow package has no `and-cuda` extra
# until 2.14 -- 2.11.1 can only ever run on CPU via pip alone (confirmed via
# PyPI metadata: no nvidia-* entries in requires_dist for 2.11.1/2.12/2.13).
# Bumped to 2.15.1 (same GPU-enabled version already used by
# dockerfiles/lst_ai) to get `tensorflow[and-cuda]`'s bundled CUDA/cuDNN pip
# packages. Re-verified end-to-end with validate.py in this directory: the
# real downloaded .h5 model loads and predicts with the expected
# (256, 256, 3) output shape under 2.15.1. numpy is left unpinned -- TF 2.15's
# own requires_dist resolves a compatible numpy (1.26.4 observed) automatically
# (the numpy 2.x incompatibility that required pinning was specific to the
# 2.11.1 wheel).
#
# WHAT THIS ACTUALLY RUNS
# `bin/bawil_filter.py` -- see the module docstring there for the full
# preprocessing story (per-slice z-score, 256x256 resize, axial orientation
# confirmed by visually inspecting a real training sample from the paper's
# own repo). No official NIfTI inference CLI exists upstream, so this script
# is a from-scratch, verified reimplementation of the paper's own
# preprocessing pipeline.
#
# USAGE
#   docker build -t ms_chus/bawil:latest .
#
# After building, verify the model actually loads and predicts (not run
# automatically as part of the build -- see validate.py in this directory):
#   docker run --rm -v $(pwd)/dockerfiles/bawil/validate.py:/tmp/validate.py \
#       ms_chus/bawil:latest python3 /tmp/validate.py
# =============================================================================

FROM python:3.10-slim

LABEL maintainer="ms_chus_pipeline"
LABEL tool="BAWIL"
LABEL source="https://huggingface.co/Bawil/wmh_leverage_normal_abnormal_segmentation"
LABEL paper_doi="10.48550/arXiv.2506.07123"

# 1. System dependencies (opencv needs libgl/libglib at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Python dependencies. See note above re: tensorflow version and numpy.
RUN pip install --no-cache-dir \
        "tensorflow[and-cuda]==2.15.1" \
        "opencv-python-headless==4.10.0.84" \
        "nibabel==5.2.1" \
        "scipy" \
        "scikit-image"

# 3. Download the pretrained weights from Hugging Face
RUN mkdir -p /opt/bawil \
    && wget -q --show-progress \
        "https://huggingface.co/Bawil/wmh_leverage_normal_abnormal_segmentation/resolve/main/unet/models/scenario2_multiclass_model.h5" \
        -O /opt/bawil/scenario2_multiclass_model.h5 \
    && test -s /opt/bawil/scenario2_multiclass_model.h5 \
    && echo "BAWIL weights downloaded ($(stat -c%s /opt/bawil/scenario2_multiclass_model.h5) bytes)"

# 4. procps (provides `ps`, required by Nextflow's task metrics collector)
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

# GPU vs CPU (CUDA_VISIBLE_DEVICES) is set by the Nextflow process at
# runtime, not baked in here, so the same image serves both paths.
ENV TF_CPP_MIN_LOG_LEVEL=2

# No ENTRYPOINT: Nextflow's global --entrypoint "" override makes this moot
# during pipeline runs, but declaring one anyway breaks manual `docker run
# ms_chus/bawil:latest python3 ...` invocations (bash would try to source
# "python3" as a script and fail with "cannot execute binary file").
