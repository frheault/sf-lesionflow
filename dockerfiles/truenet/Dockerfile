# =============================================================================
# Docker image: TrueNet MS Lesion Segmentation
# Tool:  TrueNet — Triplanar U-Net ensemble (FLAIR + T1w)
# Paper: Sundaresan et al. 2021, Medical Image Analysis
# Repo:  https://git.fmrib.ox.ac.uk/vaanathi/truenet
# FSL:   https://fsl.fmrib.ox.ac.uk/fsl/docs/structural/truenet.html
# =============================================================================
#
# DESIGN PHILOSOPHY — "rebuild anywhere, no local files needed"
# ------------------------------------------------------------
# Everything is fetched at build time from public URLs.
#
# WHAT GETS DOWNLOADED AT BUILD TIME
# ------------------------------------
# 1. Base image: brainlife/fsl:6.0.4-patched  (~5 GB, includes FSL + fslmaths)
# 2. TrueNet source via git clone from Oxford GitLab
# 3. Python deps: torch (CPU), torchvision, nibabel, etc.
# 4. Pre-trained models from Google Drive via gdown:
#      Folder: https://drive.google.com/drive/folders/1iqO-hd27NSHHfKun125Rt-2fh1l9EiuT
#      Contains: MWSC_FLAIR_T1/ model directory
#    Saved to: /opt/truenet_models/
#
# HOW TRUENET FINDS ITS MODELS
# ------------------------------
# truenet evaluate accepts -m <model_name> which is resolved relative to
# TRUENET_PRETRAINED_MODEL_PATH environment variable, OR as an absolute path.
# We set the env var at build time to /opt/truenet_models/.
#
# INPUT NAMING CONVENTION
# ------------------------
# TrueNet expects: <subj_name>_FLAIR.nii.gz and <subj_name>_T1.nii.gz
# in the same input directory. The script renames/symlinks before calling.
#
# USAGE
# -----
#   docker build -t ms_chus/truenet:latest .
#
#   # Prepare masterfile:
#   printf "FLAIR T1\n%s %s\n" \
#     "/input/sub-021_ses-1_FLAIR.nii.gz" \
#     "/input/sub-021_ses-1_T1.nii.gz" > /tmp/truenet_in/masterfile.txt
#
#   docker run --rm \
#     -v /tmp/truenet_in:/input \
#     -v /tmp/truenet_out:/output \
#     ms_chus/truenet:latest \
#     apply -i /input/masterfile.txt -m mwsc -o /output -cpu True
#
#   # Binarize at 0.5:
#   docker run --rm -v /tmp/truenet_out:/output ms_chus/truenet:latest \
#     fslmaths /output/Predicted_probmap_truenet_sub-021_ses-1.nii.gz \
#              -thr 0.5 -bin /output/sub-021_ses-1_truenet_binary.nii.gz
#
# OUTPUT: Predicted_probmap_truenet_<subj_name>.nii.gz (probability map, thresh at 0.5)
#
# NOTES
# -----
# - CPU-only image (pass -cpu to truenet evaluate).
# - gdown may fail if Google Drive rate-limits the download. If so, download
#   the folder manually and COPY it in, or use a mirror.
# - The GitLab repo (git.fmrib.ox.ac.uk) requires no authentication for clone.
# =============================================================================

FROM brainlife/fsl:6.0.4-patched

LABEL maintainer="ms_chus_pipeline"
LABEL tool="TrueNet"
LABEL version="2021"
LABEL source="https://git.fmrib.ox.ac.uk/vaanathi/truenet"
LABEL models_url="https://drive.google.com/drive/folders/1iqO-hd27NSHHfKun125Rt-2fh1l9EiuT"

# ── 1. System dependencies ────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        wget \
        curl \
        python3 \
        python3-pip \
        python3-dev \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ── 2. Python: upgrade pip and install PyTorch CPU (Python 3.6 compatible) ──
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel
RUN pip3 install --no-cache-dir "typing_extensions<=4.1.1"
RUN pip3 install --no-cache-dir \
        "torch==1.10.2+cpu" "torchvision==0.11.3+cpu" \
        -f https://download.pytorch.org/whl/cpu/torch_stable.html

# ── 3. TrueNet Python deps ────────────────────────────────────────────────────
RUN pip3 install --no-cache-dir \
        "nibabel" \
        "numpy<2" \
        "scipy" \
        "imageio==2.15.0" \
        "scikit-image==0.17.2" \
        "pandas==1.1.5" \
        "gdown>=4.6.0"

# ── 4. Clone TrueNet from Oxford GitLab ──────────────────────────────────────
WORKDIR /opt
RUN git clone --depth 1 \
        https://git.fmrib.ox.ac.uk/vaanathi/truenet.git truenet_repo \
    && pip3 install --no-cache-dir --no-deps -e /opt/truenet_repo

# ── 5. Copy pre-trained models into the image ────────────────────────────────
ENV TRUENET_PRETRAINED_MODEL_PATH=/opt/truenet_models
COPY models /opt/truenet_models
RUN cp -r /opt/truenet_models/MWSC_FLAIR_T1/* /opt/truenet_models/ \
    && chmod -R a+rX /opt/truenet_models \
    && echo "[OK] TrueNet models installed."

# ── 6. Smoke-test: verify model directory exists ──────────────────────────────
RUN python3 - <<'EOF'
import os, sys
base = os.environ['TRUENET_PRETRAINED_MODEL_PATH']
files = []
for root, dirs, fs in os.walk(base):
    files.extend(fs)
print(f"  {len(files)} model file(s) found under {base}")
if not files:
    print("ERROR: No model files found!", file=sys.stderr)
    sys.exit(1)
print("[OK] TrueNet models verified.")
EOF

# ── 7. FSL environment ────────────────────────────────────────────────────────
# brainlife/fsl already sets FSLDIR; source the config for completeness
ENV FSLDIR=/usr/local/fsl
ENV PATH="${FSLDIR}/bin:${PATH}"

# ── 8. Entrypoint ─────────────────────────────────────────────────────────────
# truenet is the CLI entry point installed by pip
ENTRYPOINT ["truenet"]
CMD ["--help"]
