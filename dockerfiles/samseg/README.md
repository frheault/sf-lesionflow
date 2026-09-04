# SAMSEG — Use Existing Local FreeSurfer Image

## Official Image (Already on Your Machine)

```
freesurfer/freesurfer:7.4.1
```

You already have this image locally (20 GB). SAMSEG (`run_samseg`) is natively bundled in FreeSurfer 7.4.1 with all GMM atlas files included. No additional setup needed.

## Usage (single session)

```bash
DATA=/path/to/derivatives/sub-XXX
FS_LICENSE=/path/to/freesurfer/license.txt   # required

docker run --rm \
  -v "${DATA}:/data" \
  -v "${FS_LICENSE}:/usr/local/freesurfer/license.txt:ro" \
  freesurfer/freesurfer:7.4.1 \
  run_samseg \
  --input /data/sub-XXX_ses-Y_T1w_space-MNI.nii.gz \
          /data/sub-XXX_ses-Y_FLAIR_space-MNI.nii.gz \
  --pallidum-separate \
  --output /data/samseg/ses-Y \
  --lesion --lesion-mask-pattern 0 1
```

Then extract the lesion label (label 99 = WM lesion in SAMSEG):
```bash
docker run --rm -v "${DATA}:/data" freesurfer/freesurfer:7.4.1 \
  python3 -c "
import nibabel as nib, numpy as np
seg = nib.load('/data/samseg/ses-Y/seg.mgz')
mask = (seg.get_fdata() == 99).astype(np.uint8)
nib.save(nib.Nifti1Image(mask, seg.affine, seg.header),
         '/data/samseg/sub-XXX_ses-Y_samseg_binary.nii.gz')
"
```

## FreeSurfer License

SAMSEG requires a valid FreeSurfer license file. Get one free at:
https://surfer.nmr.mgh.harvard.edu/registration.html

Mount it at `/usr/local/freesurfer/license.txt` inside the container (read-only).

## Key Flags

| Flag | Purpose |
|------|---------|
| `--lesion --lesion-mask-pattern 0 1` | Enable WM lesion segmentation (T1=0 means hypointense, FLAIR=1 means hyperintense) |
| `--pallidum-separate` | Recommended for MS to avoid merging pallidum into other structures |
| `--threads N` | Limit CPU threads if on a shared machine |

## Technical Notes

- **Speed**: SAMSEG is CPU-only and takes ~20–40 min per session on a modern server.
- **Atlas**: The GMM atlas is bundled in the FreeSurfer installation at `$FREESURFER_HOME/average/samseg/`. Nothing to download.
- **Output**: `seg.mgz` contains multi-class segmentation. Label 99 = WM lesion.
- **Documentation**: https://surfer.nmr.mgh.harvard.edu/fswiki/Samseg
