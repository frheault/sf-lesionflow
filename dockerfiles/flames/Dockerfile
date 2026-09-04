# =============================================================================
# Docker image: FLAMeS (nnUNetv2) MS Lesion Segmentation
# Tool:  FLAMeS, FLAIR Lesion Analysis in Multiple Sclerosis
# Paper: La Rosa et al. 2025, Journal of Neuroimaging
# Weights: Zenodo record 17955359
# =============================================================================
#
# DESIGN PHILOSOPHY, "rebuild anywhere, no local files needed"
# Every dependency (pip packages, nnUNet weights) is fetched at build time
# from canonical public URLs (PyPI + Zenodo).
#
# WHAT GETS DOWNLOADED AT BUILD TIME
# 1. PyTorch (CPU wheel, ~300MB) and nnunetv2 from PyPI
# 2. FLAMeS model weights from Zenodo record 17955359 (~several hundred MB):
#      URL: https://zenodo.org/records/17955359/files/Dataset004_WML.zip
#    Extracted to: /opt/nnunet_results/Dataset004_WML/
#    Structure after extraction:
#      Dataset004_WML/
#        nnUNetTrainer_8000epochs__nnUNetPlans__3d_fullres/
#          fold_0/ fold_1/ fold_2/ fold_3/ fold_4/
#          plans.json  dataset.json  dataset_fingerprint.json
#
# HOW nnUNetv2 FINDS ITS WEIGHTS
# nnUNetv2_predict reads the nnUNet_results environment variable.
# We set it to /opt/nnunet_results/ at build time and bake it into ENV.
# At runtime, no extra flags are needed for weight discovery.
#
# REQUIRED INPUT NAMING CONVENTION
# nnUNetv2 requires inputs to be named: <CASE_ID>_0000.nii.gz
# The caller must rename the FLAIR image before passing it:
#   ln -s sub-021_ses-1_FLAIR_space-MNI.nii.gz sub-021_ses-1_0000.nii.gz
# See USAGE section below.
#
# USAGE
#   docker build -t ms_chus/flames:latest .
#
# After building, verify all 5 weight folds are present (not run
# automatically as part of the build -- see validate.py in this directory):
#   docker run --rm --entrypoint python3 \
#       -v $(pwd)/dockerfiles/flames/validate.py:/tmp/validate.py \
#       ms_chus/flames:latest /tmp/validate.py
#
#   # Prepare input directory (nnUNet naming: <CASE_ID>_0000.nii.gz)
#   mkdir -p /tmp/flames_in /tmp/flames_out
#   ln -sf /path/to/sub-021_ses-1_FLAIR_space-MNI.nii.gz \
#           /tmp/flames_in/sub-021_ses-1_0000.nii.gz
#
#   docker run --rm \
#     -v /tmp/flames_in:/input \
#     -v /tmp/flames_out:/output \
#     ms_chus/flames:latest \
#     -i /input -o /output \
#     -d 004 -c 3d_fullres -tr nnUNetTrainer_8000epochs \
#     --disable_tta -device cpu
#
# OUTPUT: /output/<CASE_ID>.nii.gz (binary mask, copy to flames/<SUBJECT>_flames_binary.nii.gz)
#
# NOTES
# - CPU-only image. Add `-device cuda` and use a CUDA base image for GPU.
# - --disable_tta is mandatory on CPU (test-time augmentation is GPU-only).
# - RAM: ~8 GB needed for 3d_fullres inference.
# =============================================================================

FROM python:3.10-slim

LABEL maintainer="ms_chus_pipeline"
LABEL tool="FLAMeS (nnUNetv2)"
LABEL version="2025"
LABEL source="https://github.com/MIC-DKFZ/nnUNet"
LABEL weights_url="https://zenodo.org/records/17955359/files/Dataset004_WML.zip"

# 1. System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget \
        curl \
        unzip \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 2. PyTorch (CPU) and nnUNetv2
RUN pip install --no-cache-dir "typing_extensions>=4.10.0"
RUN pip install --no-cache-dir \
        "torch==2.1.0" "torchvision==0.16.0" \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir nnunetv2

# 3. Download FLAMeS weights from Zenodo.
# Zenodo record 17955359, file: Dataset004_WML.zip
# This contains the full nnUNetv2 results directory (5 folds).
ENV nnUNet_results=/opt/nnunet_results

RUN mkdir -p "${nnUNet_results}" \
    && wget -q --show-progress \
        "https://zenodo.org/records/17955359/files/Dataset004_WML.zip" \
        -O /tmp/Dataset004_WML.zip \
    && unzip -q /tmp/Dataset004_WML.zip -d "${nnUNet_results}" \
    && rm /tmp/Dataset004_WML.zip \
    && echo "FLAMeS weights extracted to ${nnUNet_results}"

# 4. Also set nnUNet preprocessing and raw dirs (required by nnUNetv2)
ENV nnUNet_preprocessed=/opt/nnunet_preprocessed
ENV nnUNet_raw=/opt/nnunet_raw
RUN mkdir -p "${nnUNet_preprocessed}" "${nnUNet_raw}"

# 5. procps (provides `ps`, required by Nextflow's task metrics collector)
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["nnUNetv2_predict"]
CMD ["--help"]
