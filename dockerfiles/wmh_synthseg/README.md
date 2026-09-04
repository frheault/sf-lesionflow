# WMH-SynthSeg (`SEGMENTATION_WMH_SYNTHSEG`): Custom Dockerfile (FreeSurfer-based, x86_64)

## Container Info

```
ms_chus/wmh_synthseg:latest
```

Custom image built on `freesurfer/freesurfer:7.4.1` (linux/amd64). Fully
self-contained: the model source and weights are fetched from public URLs at
build time. No local files needed.

> **Why not `pablaso/wmh_synthseg:latest`?** That's the upstream author's own
> image, but it was built for `linux/arm64/v8` only. Running it on standard
> Linux x86_64 hosts fails with `exec format error` (exit code 255). FreeSurfer
> 7.4.1 already ships the PyTorch stack WMH-SynthSeg's `inference.py` needs
> (via its own bundled `fspython`), so we reproduce the model on top of it
> instead.

- **Base image**: `freesurfer/freesurfer:7.4.1` (linux/amd64).
- **Entrypoint**: `/bin/bash`, providing `mri_WMHsynthseg` (the real upstream
  wrapper script, installed verbatim) and FreeSurfer's `fspython`.
- **Weights**: `WMH-SynthSeg_v10_231110.pth`, fetched at build time from the
  official MGH FTP server and installed under `/usr/local/freesurfer/models/`.
- **Source fetch**: a plain tarball of the repo's default branch via `wget` +
  `tar` (this base image is CentOS Stream 8 and has neither `apt-get` nor
  `git`, only `wget`/`curl`/`tar`).
- **Upstream source**: https://github.com/lasopablo/freesurfer-freesurfer-dev-mri_WMHsynthseg
- **Citation**: Laso et al., under review. https://arxiv.org/abs/2312.05119

## Build

```bash
docker build -t ms_chus/wmh_synthseg:latest dockerfiles/wmh_synthseg/
```

See `SEGMENTATION_WMH_SYNTHSEG` in `modules/local/lesion_segmentation.nf` for
the exact invocation Nextflow uses.

## Manual usage (outside Nextflow, for debugging)

```bash
DATA=/path/to/derivatives/sub-XXX

docker run --rm -v "${DATA}:/data" -e HOME=/data ms_chus/wmh_synthseg:latest \
    mri_WMHsynthseg --i /data/sub-XXX_ses-Y_FLAIR_space-MNI.nii.gz \
    --o /data/wmh_synthseg/sub-XXX_ses-Y_wmh_raw.nii.gz \
    --save_lesion_probabilities --device cpu --threads 1
```

## Technical Notes

- **RAM**: heavy on full-resolution volumes. `--crop 160` (or lower) reduces
  memory if a run OOMs.
- **CPU**: `--device cpu` is required unless the host has CUDA.
- `inference.py` usage reference (from `--help`):
  `--i I --o O [--csv_vols CSV_VOLS] [--device DEVICE] [--threads THREADS] [--save_lesion_probabilities] [--crop]`
