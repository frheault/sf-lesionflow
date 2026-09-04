# =============================================================================
# Docker image: WMH-SynthSeg
# Tool:   WMH-SynthSeg (extension of SynthSeg for white matter hyperintensities)
# Paper:  Laso et al., under review, https://arxiv.org/abs/2312.05119
# Repo:   https://github.com/lasopablo/freesurfer-freesurfer-dev-mri_WMHsynthseg
# Runtime: SEGMENTATION_WMH_SYNTHSEG in modules/local/lesion_segmentation.nf
# =============================================================================
#
# DESIGN PHILOSOPHY, "rebuild anywhere, no local files needed"
# Everything is fetched at build time from public URLs, no local
# wmh_synthseg_repo/ clone or pre-downloaded weights file needed.
#
# WHY freesurfer/freesurfer:7.4.1 AND NOT pablaso/wmh_synthseg:latest
# pablaso/wmh_synthseg:latest (the upstream author's own image) was built for
# linux/arm64/v8 only; running it on x86_64 hosts fails with "exec format
# error". FreeSurfer 7.4.1 already ships the PyTorch/scientific stack that
# WMH-SynthSeg's inference.py needs via its own bundled `fspython`, so we
# reproduce the model on top of it instead of the upstream image.
#
# WHAT GETS DOWNLOADED AT BUILD TIME
# 1. WMH-SynthSeg source (inference.py + the `mri_WMHsynthseg` wrapper script)
#    via a plain tarball fetch of the upstream repo's default branch (NOT git
#    clone: this base image is CentOS Stream 8 and has neither `apt-get` nor
#    `git`, only `wget`/`curl`/`tar`, which is all this step needs).
# 2. Pre-trained weights, WMH-SynthSeg_v10_231110.pth (~754 MB), from the
#    official MGH FTP server:
#      https://ftp.nmr.mgh.harvard.edu/pub/dist/lcnpublic/dist/WMH-SynthSeg/WMH-SynthSeg_v10_231110.pth
#
# HOW mri_WMHsynthseg FINDS ITS CODE/WEIGHTS
# The upstream `mri_WMHsynthseg` wrapper (installed verbatim onto PATH here)
# execs `$FREESURFER_HOME/bin/fspython $FREESURFER_HOME/python/packages/WMHSynthSeg/inference.py "$@"`
# and requires the weights file at `$FREESURFER_HOME/models/WMH-SynthSeg_v10_231110.pth`.
# Both paths are populated below to match exactly.
#
# USAGE
#   docker build -t ms_chus/wmh_synthseg:latest .
#
#   docker run --rm -v /path/to/derivatives/sub-XXX:/data ms_chus/wmh_synthseg:latest \
#       mri_WMHsynthseg --i /data/sub-XXX_ses-Y_FLAIR_space-MNI.nii.gz \
#                        --o /data/wmh_synthseg/sub-XXX_ses-Y_wmh_raw.nii.gz \
#                        --save_lesion_probabilities --device cpu --threads 1
#
# NOTES
# - CPU-only (`--device cpu`); RAM-heavy at full resolution, `--crop 160` (or
#   lower) reduces memory if a run OOMs.
# - Image size: ~20 GB (mostly the FreeSurfer 7.4.1 base).
# =============================================================================

FROM freesurfer/freesurfer:7.4.1

LABEL maintainer="ms_chus_pipeline"
LABEL tool="WMH-SynthSeg"
LABEL source="https://github.com/lasopablo/freesurfer-freesurfer-dev-mri_WMHsynthseg"
LABEL weights_url="https://ftp.nmr.mgh.harvard.edu/pub/dist/lcnpublic/dist/WMH-SynthSeg/WMH-SynthSeg_v10_231110.pth"

# 1. Fetch WMH-SynthSeg source and install the inference code + wrapper.
# No apt-get/git on this base (CentOS Stream 8) -- wget + tar (both present)
# are all a plain tarball fetch of the repo's default branch needs.
RUN wget -q -O /tmp/wmh_synthseg_src.tar.gz \
        "https://github.com/lasopablo/freesurfer-freesurfer-dev-mri_WMHsynthseg/archive/refs/heads/main.tar.gz" \
    && mkdir -p /tmp/wmh_synthseg_src \
    && tar xzf /tmp/wmh_synthseg_src.tar.gz -C /tmp/wmh_synthseg_src --strip-components=1 \
    && mkdir -p /usr/local/freesurfer/python/packages/WMHSynthSeg \
    && cp -r /tmp/wmh_synthseg_src/WMHSynthSeg/* /usr/local/freesurfer/python/packages/WMHSynthSeg/ \
    && cp /tmp/wmh_synthseg_src/mri_WMHsynthseg /usr/local/bin/mri_WMHsynthseg \
    && chmod a+rx /usr/local/bin/mri_WMHsynthseg \
    && rm -rf /tmp/wmh_synthseg_src /tmp/wmh_synthseg_src.tar.gz

# 2. Download the pre-trained weights from the official MGH FTP server, then
# fix permissions in the SAME layer (a separate RUN here would duplicate the
# ~754MB weights file across two layers).
RUN mkdir -p /usr/local/freesurfer/models \
    && wget -q --show-progress \
        "https://ftp.nmr.mgh.harvard.edu/pub/dist/lcnpublic/dist/WMH-SynthSeg/WMH-SynthSeg_v10_231110.pth" \
        -O /usr/local/freesurfer/models/WMH-SynthSeg_v10_231110.pth \
    && chmod -R a+rX /usr/local/freesurfer/python/packages/WMHSynthSeg \
        /usr/local/freesurfer/models/WMH-SynthSeg_v10_231110.pth \
    && test -s /usr/local/freesurfer/models/WMH-SynthSeg_v10_231110.pth \
    && test -f /usr/local/freesurfer/python/packages/WMHSynthSeg/inference.py \
    && echo "WMH-SynthSeg code and weights verified."

# No ENTRYPOINT: Nextflow's global --entrypoint "" override makes this moot
# during pipeline runs, but declaring one anyway breaks manual `docker run
# ms_chus/wmh_synthseg:latest mri_WMHsynthseg ...` invocations (bash would try
# to source "mri_WMHsynthseg" as a script instead of executing it).
