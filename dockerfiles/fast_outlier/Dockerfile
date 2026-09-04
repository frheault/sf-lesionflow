# =============================================================================
# Docker image: FSL FAST Outlier Detection (Unsupervised Physics)
# Runtime: SEGMENTATION_FAST_OUTLIER in modules/local/lesion_segmentation.nf
# =============================================================================
#
# DESIGN PHILOSOPHY, "rebuild anywhere, no local files needed"
# ------------------------------------------------------------
# Built on top of brainlife/fsl:6.0.4-patched (Ubuntu base).
# Installs Python 3 + nibabel + numpy + scipy so this image can run
# bin/fast_outlier.py, that script is NOT baked into this image. Nextflow
# resolves it from the pipeline's own bin/ directory (auto-added to PATH),
# so the image only needs to provide FSL + the Python packages it imports.
#
# USAGE (via Nextflow, see SEGMENTATION_FAST_OUTLIER)
# -----------------------------------------------------
#   docker build -t ms_chus/fast_outlier:latest .
#
# The process itself runs:
#   fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -o fast_out/fast <t1_mni.nii.gz>
#   fast_outlier.py --flair <flair_mni.nii.gz> --wm_pve fast_out/fast_pve_2.nii.gz \
#       --output <id>_fast-outlier_binary.nii.gz --sigma 2.5 \
#       --pve_threshold 0.95 --dwm_thresh 0.50
#
# No FreeSurfer/SynthSeg dependency: bin/fast_outlier.py only consumes FSL's
# own WM partial-volume-estimate map (fast_pve_2.nii.gz).
# =============================================================================

FROM brainlife/fsl:6.0.4-patched

LABEL maintainer="ms_chus_pipeline"
LABEL tool="FSL FAST Outlier"
LABEL version="1.0"

# ── 1. Install Python dependencies ───────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
        nibabel \
        numpy \
        scipy

# ── 2. Environment for FSL ───────────────────────────────────────────────────
ENV FSLDIR=/usr/local/fsl
ENV PATH="${FSLDIR}/bin:${PATH}"
ENV FSLOUTPUTTYPE=NIFTI_GZ
