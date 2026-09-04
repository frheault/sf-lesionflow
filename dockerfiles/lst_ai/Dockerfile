# =============================================================================
# Docker image: LST-AI MS Lesion Segmentation
# Tool:  LST-AI v1.1.0 (3D U-Net ensemble, T1w + FLAIR)
# Paper: Wiltgen et al. 2024, NeuroImage
# Repo:  https://github.com/CompImg/LST-AI
# =============================================================================
#
# DESIGN PHILOSOPHY — "rebuild anywhere, no local files needed"
# ------------------------------------------------------------
# Every dependency (pip packages, model weights, atlas, binaries) is fetched
# via explicit wget/pip from canonical public URLs. Fully rebuildable on any
# machine with internet access.
#
# WHAT GETS DOWNLOADED AT BUILD TIME
# ------------------------------------
# 1. Python packages via pip (version-pinned):
#      - numpy==1.24.3          (LST-AI requires <1.24.4)
#      - tensorflow==2.15.1     (LST-AI requires >=2.13,<2.16 — pinned to avoid
#                                pip downloading every TF candidate wheel)
#      - torch==2.1.0+cpu       (LST-AI requires <=2.1.0)
#      - + nibabel, scipy, scikit-image, pillow, requests
# 2. LST-AI source via git clone from GitHub (tag v1.1.0)
# 3. lst_data.zip from GitHub Releases v1.0.0 (~300 MB):
#      URL: https://github.com/CompImg/LST-AI/releases/download/v1.0.0/lst_data.zip
#    Extracted into /opt/LST-AI/LST_AI/ which is the data_dir LST-AI resolves
#    relative to its own __file__ (requires editable install, see note below).
#    Contains:
#      atlas/     — MNI atlas and brain mask NIfTIs
#      binaries/  — statically-linked greedy registration binary (Linux x86_64)
#      model/     — three TF 3D U-Net checkpoint .h5 files
#
# HOW LST-AI FINDS ITS DATA
# --------------------------
# LST-AI resolves its data directory as os.path.dirname(os.path.abspath(__file__))
# inside LST_AI/lst (the entrypoint script). We install with `pip install -e .`
# (editable mode) so __file__ stays at /opt/LST-AI/LST_AI/ and the data zip is
# extracted there. A regular pip install would put code in site-packages and
# break the relative path resolution.
#
# USAGE
# -----
#   docker build -t ms_chus/lst_ai:latest .
#
#   docker run --rm \
#     -v /path/to/derivatives/sub-XXX:/data \
#     ms_chus/lst_ai:latest \
#     --t1    /data/sub-XXX_ses-Y_T1w_space-MNI.nii.gz \
#     --flair /data/sub-XXX_ses-Y_FLAIR_space-MNI.nii.gz \
#     --output /data/lst_ai/ses-Y_out \
#     --segment_only --stripped
#
# OUTPUT: /data/lst_ai/ses-Y_out/space-flair_seg-lst.nii.gz  (binary mask)
#
# NOTES
# -----
# - CPU-only: CUDA_VISIBLE_DEVICES=-1 disables GPU to avoid the TF XLA
#   libdevice.10.bc crash on machines without a full CUDA stack.
#   Remove or set to "0" to enable GPU.
# - Image size: ~5 GB (TF + PyTorch CPU + LST-AI data)
# - RAM at runtime: ~8 GB
# =============================================================================

FROM python:3.10-slim

LABEL maintainer="ms_chus_pipeline"
LABEL tool="LST-AI"
LABEL version="1.1.0"
LABEL source="https://github.com/CompImg/LST-AI"
LABEL data_url="https://github.com/CompImg/LST-AI/releases/download/v1.0.0/lst_data.zip"

# ── 1. System dependencies ───────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        wget \
        curl \
        unzip \
        libgomp1 \
        libglib2.0-0 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

# ── 2. Pin and install Python dependencies BEFORE cloning LST-AI ─────────────
# All versions pinned to what is installed in the local working venv (venv_lst).
# CONSTRAINT MATRIX:
#   LST-AI:  numpy<1.24.4, tensorflow>=2.13,<2.16, torch<=2.1.0
#   nibabel: >= 5.2 requires numpy>=1.25 → CONFLICT with LST-AI numpy<1.24.4
#            = 5.1.0 only requires numpy>=1.19 → COMPATIBLE ✓
# INSTALL ORDER:
#   1. TF (large, sets protobuf/keras/etc.)
#   2. torch CPU (pulls deps but we'll override numpy after)
#   3. All remaining deps with PINNED versions — nibabel==5.1.0 is critical
#   4. numpy --force-reinstall LAST: torch silently upgrades it to 2.x,
#      so we lock it back to 1.24.3 as the very final step
RUN pip install --no-cache-dir "tensorflow==2.15.1"
RUN pip install --no-cache-dir \
        "torch==2.1.0" "torchvision==0.16.0" \
        --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir \
        "nibabel==5.1.0" \
        "Pillow" \
        "requests" \
        "scipy>=1.9.0" \
        "scikit-image>=0.21.0"
# MUST BE LAST: force numpy to LST-AI's required <1.24.4 after torch upgraded it
RUN pip install --no-cache-dir --force-reinstall "numpy==1.24.3"

# ── 3. Clone LST-AI source (pinned tag v1.1.0) ───────────────────────────────
WORKDIR /opt
RUN git clone --depth 1 --branch v1.1.0 \
        https://github.com/CompImg/LST-AI.git LST-AI

# ── 4. Install LST-AI in editable mode (no-deps: already installed above) ────
WORKDIR /opt/LST-AI
RUN pip install --no-cache-dir --no-deps -e .

# ── 5. Download weights, atlas, and binaries via wget ────────────────────────
# Single zip from GitHub Releases — contains atlas/, binaries/, model/ subdirs.
# Extracted into LST_AI/ so the tool finds them via its __file__-relative lookup.
RUN wget -q --show-progress \
        "https://github.com/CompImg/LST-AI/releases/download/v1.0.0/lst_data.zip" \
        -O /tmp/lst_data.zip \
    && unzip -q /tmp/lst_data.zip -d /opt/LST-AI/LST_AI/ \
    && rm /tmp/lst_data.zip \
    && echo "✓ LST-AI data extracted:"
RUN ls -lh /opt/LST-AI/LST_AI/atlas/ /opt/LST-AI/LST_AI/model/ 2>/dev/null | head -20

# ── 6. Make greedy binary executable and put it on PATH ──────────────────────
# LST-AI calls greedy as a bare subprocess command ('greedy ...').
# The binary lives in LST_AI/binaries/ — symlink it onto PATH.
RUN chmod +x /opt/LST-AI/LST_AI/binaries/greedy* 2>/dev/null || true \
    && ln -sf /opt/LST-AI/LST_AI/binaries/greedy /usr/local/bin/greedy

# ── 7. Smoke-test: verify all data dirs exist and are non-empty ───────────────
RUN python3 - <<'PYEOF'
import os, sys
base = "/opt/LST-AI/LST_AI"
ok = True
for d in ("atlas", "binaries", "model"):
    path = os.path.join(base, d)
    files = os.listdir(path) if os.path.isdir(path) else []
    print(f"  {d}/: {len(files)} file(s) — {files[:3]}")
    if not files:
        print(f"ERROR: {path} is empty or missing!", file=sys.stderr)
        ok = False
if not ok:
    sys.exit(1)
print("✓ All LST-AI data directories verified.")
PYEOF

# ── 8. Runtime environment variables ─────────────────────────────────────────
# Disable GPU to avoid TF XLA / libdevice.10.bc crash (safe on CPU machines).
# Remove CUDA_VISIBLE_DEVICES=-1 (or set to "0") to re-enable GPU.
ENV CUDA_VISIBLE_DEVICES=-1
ENV TF_FORCE_GPU_ALLOW_GROWTH=true
ENV TF_GPU_ALLOCATOR=cuda_malloc_async
ENV TF_CPP_MIN_LOG_LEVEL=2

# ── 9. procps (provides `ps`, required by Nextflow's task metrics collector) ──
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

# ── 10. Entrypoint ────────────────────────────────────────────────────────────
ENTRYPOINT ["lst"]
CMD ["--help"]
