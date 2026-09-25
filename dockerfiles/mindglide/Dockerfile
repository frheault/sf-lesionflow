# =============================================================================
# Docker image: mindGlide MS Lesion Segmentation
# Tool:   mindGlide v1.3.0 (MONAI sliding-window inference, any MRI modality)
# Paper:  Goebl et al. 2025, Nature Communications 16(1):3149
# Repo:   https://github.com/MS-PINPOINT/mindGlide
# Model:  https://huggingface.co/MS-PINPOINT/mindglide
# Runtime: SEGMENTATION_MINDGLIDE in modules/local/lesion_segmentation.nf
# =============================================================================
#
# DESIGN PHILOSOPHY -- "rebuild anywhere, no local files needed"
# Every dependency (pip packages, PyTorch CUDA wheel, model weights) is fetched
# from canonical public URLs at build time. Fully rebuildable on any machine with
# internet access.
#
# WHY THIS BASE IMAGE
# python:3.11-slim matches mindglide's "requires-python >=3.9" and aligns with the
# python:3.10-slim/python:3.12-slim conventions used across the pipeline's other
# custom containers (bawil, lst_ai, shivai).
#
# WHAT GETS DOWNLOADED AT BUILD TIME
# 1. System packages via apt:
#      - procps (provides `ps`, mandatory for Nextflow task resource monitoring)
#      - wget, curl, libgl1, libglib2.0-0
# 2. PyTorch CUDA-enabled wheel:
#      - torch==2.3.1 from https://download.pytorch.org/whl/cu118
#        Allows the same image to support both GPU (cuda) and CPU paths at runtime.
# 3. Python packages from PyPI:
#      - monai==1.4.0
#      - mindglide==1.3.0 (pulls in nibabel, huggingface_hub, scipy, scikit-image, pandas, tqdm)
# 4. Model weights:
#      - Downloaded from Hugging Face Hub (MS-PINPOINT/mindglide) pinned to revision
#        a1969821c0a4a37ae54f649a9a0c6fd1b8a48e26
#        Filename: _20240404_conjurer_trained_dice_7733.pt (~123 MB)
#      - Saved to /opt/mindglide/models/_20240404_conjurer_trained_dice_7733.pt
#      - Also cached in /opt/mindglide/hf_cache so offline execution never accesses HF.
#
# USAGE
#   docker build -t frheault/sf-lesionflow-mindglide:1.0.0 dockerfiles/mindglide/
#
# After building, verify the model loads and predicts:
#   docker run --rm -v $(pwd)/dockerfiles/mindglide/validate.py:/tmp/validate.py \
#       frheault/sf-lesionflow-mindglide:1.0.0 python3 /tmp/validate.py
#
# NOTES
# - No ENTRYPOINT is set to ensure compatibility with Nextflow's global
#   docker.runOptions and to allow flexible CLI or python invocation.
# - Offline safe: MODEL_PATH and HF_HOME are baked into ENV pointing to world-readable
#   directories in /opt/mindglide.
# =============================================================================

FROM python:3.11-slim

LABEL maintainer="frheault"
LABEL tool="mindGlide"
LABEL version="1.3.0"
LABEL source="https://github.com/MS-PINPOINT/mindGlide"
LABEL paper_doi="10.1038/s41467-025-58274-8"
LABEL model="https://huggingface.co/MS-PINPOINT/mindglide"

# 1. System dependencies (procps is required by Nextflow)
RUN apt-get update && apt-get install -y --no-install-recommends \
        procps \
        wget \
        curl \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Install PyTorch with CUDA 11.8 support
RUN pip install --no-cache-dir \
        "torch==2.3.1" \
        --index-url https://download.pytorch.org/whl/cu118

# 3. Install MONAI and mindGlide
RUN pip install --no-cache-dir \
        "monai==1.4.0" \
        "mindglide==1.3.0"

# 4. Pre-download and bake model weights into /opt/mindglide
ENV MODEL_PATH=/opt/mindglide/models/_20240404_conjurer_trained_dice_7733.pt
ENV HF_HOME=/opt/mindglide/hf_cache

RUN mkdir -p /opt/mindglide/models /opt/mindglide/hf_cache \
    && python3 -c "from huggingface_hub import hf_hub_download; import shutil; p = hf_hub_download(repo_id='MS-PINPOINT/mindglide', filename='_20240404_conjurer_trained_dice_7733.pt', revision='a1969821c0a4a37ae54f649a9a0c6fd1b8a48e26'); shutil.copy(p, '/opt/mindglide/models/_20240404_conjurer_trained_dice_7733.pt')" \
    && chmod -R a+rX /opt/mindglide \
    && test -s /opt/mindglide/models/_20240404_conjurer_trained_dice_7733.pt \
    && echo "mindGlide weights baked in successfully ($(stat -c%s /opt/mindglide/models/_20240404_conjurer_trained_dice_7733.pt) bytes)"
