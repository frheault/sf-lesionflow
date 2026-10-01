# BAWIL (`SEGMENTATION_BAWIL`)

## What this runs

Bashiri Bawil M, Shamsi M, Shakeri Bavil A. *Incorporating normal periventricular changes for
enhanced pathological WMH segmentation: multiclass deep learning approaches*. Biomedical
Engineering Online, 2026. PMC13202883 (the paper of the loaded 3-class U-Net; related earlier
work: arXiv:2506.07123).

Weights: `Bawil/wmh_leverage_normal_abnormal_segmentation` on Hugging Face
(`unet/models/scenario2_multiclass_model.h5`, a Keras U-Net, 3-class softmax
over 256x256 axial FLAIR slices, background / normal periventricular WMH /
abnormal WMH). Freely downloadable, no account or token needed (verified: a
~373MB HDF5 file, not a git-lfs pointer stub).

> **No official NIfTI inference code exists upstream.** The paper's own repo
> (`github.com/Mahdi-Bashiri/wmh-normal-abnormal-segmentation`) is a research
> training/eval harness operating on pre-extracted 256x512 PNG slices
> (FLAIR|mask side by side), not a deployable CLI. `bin/bawil_filter.py`
> reimplements the harness's own preprocessing (per-slice z-score
> normalization, resize to 256x256) from its source code, applied slice-by-slice
> to a 3D NIfTI volume. Axial slice orientation was confirmed by downloading
> and visually inspecting one of the paper's own training samples
> (`data/train/101228_10.png`), not assumed.

## Container Info

```
frheault/sf-lesionflow-bawil:1.0.0
```

`python:3.10-slim` + TensorFlow + `opencv-python-headless` + `nibabel` + `scipy` + `scikit-image`,
weights baked in at build time. **Note:** the image currently published/used reports
`tensorflow 2.11.1` (probed with `bin/probe_versions.sh`; weights sha256 `ecf057dcc7b1…`),
i.e. it was built from an earlier revision of the Dockerfile, which now pins 2.15.1 for GPU
support. Rebuilding changes the TF version; re-check predictions after a rebuild.

## Build

```bash
docker build -t frheault/sf-lesionflow-bawil:1.0.0 dockerfiles/bawil/
```

After building, verify the model actually loads and predicts (not run
automatically as part of the build -- see validate.py in this directory):
```bash
docker run --rm -v $(pwd)/dockerfiles/bawil/validate.py:/tmp/validate.py \
    frheault/sf-lesionflow-bawil:1.0.0 python3 /tmp/validate.py
```

## What the upstream model expects

Inspected in the upstream repository (`src/inference/wmh_leverage_normal_inference.py`,
`data/train/*.png`):

* 2D U-Net, 256×256×1 input, 3-class softmax (0 background, 1 normal periventricular
  hyperintensity, 2 abnormal WMH); the lesion class is **class 2**, decision rule `argmax`.
* Training slices: whole-head, unstripped 1.5 T clinical axial FLAIR (~20 thick slices per
  case), **anterior at the top of the image**, head filling ~85–96 % of the frame, per-slice
  z-score over the whole frame. **No rotation/flip augmentation** anywhere in `src/`.
* Post-processing: `remove_small_objects(min_size=5)` + 3×3 opening per slice.

The Frontiers 2024 paper by the same group (10.3389/fnins.2024.1416174, GM-mask cGAN for WMH
*classification*) is a different model and is not used.

## What `bin/bawil_filter.py` does

Per axial slice of the 1 mm resampled FLAIR (`RESAMPLE_FLAIR`, with its SynthStrip mask):

1. reorient to RAS and rotate to the training orientation (`--orientation rot90` = anterior
   at the top; the pre-2026-09-30 code fed slices rotated 90° relative to training);
2. `--framing brainbox`: crop the brain mask's bounding box (in-plane and in z) and resize it
   to 256×256; `--strip`: zero everything outside the brain;
3. z-score the frame, predict, map the three probabilities back to the native grid;
4. `--decision argmax` (class 2 wins, the upstream rule), upstream 2D post-processing, drop
   3D components < `--min_cluster_size` voxels;
5. write the binary and p(class 2) in the input grid/orientation.

The alternative `--framing head` (square head-centred window, `--fov_fill`) and `--slab_mm`
(thick-slice emulation) are kept for experiments; see below for why they are not the default.

## Calibration experiment (2026-09-30)

sub-007_ses-1 (low lesion load) and sub-019_ses-1 (lesion-rich). Each candidate was warped to
MNI and compared with the voxels labelled by ≥ 3 of the other 11 default algorithms
(sub-007: 1.43 mL, sub-019: 16.41 mL). "masked" = after the pipeline's 1-voxel-dilated brain
mask (LESION_FINALIZE). Volumes are MNI-normalized mL.

| Configuration | sub-019 vol | sub-019 Dice | sub-019 cortex frac | sub-007 vol | sub-007 Dice |
|---|---|---|---|---|---|
| **brainbox + rot90 + strip + argmax (new default)** | **17.25** | **0.472** | 0.35 | 19.70 | 0.035 |
| brainbox + none (old orientation) + argmax | 21.15 | 0.452 | 0.37 | 26.93 | 0.026 |
| brainbox + rot90 + argmax (unstripped) | 23.08 | 0.443 | 0.45 | 23.81 | 0.025 |
| previous code (brain-bbox crop, old orientation, p ≥ 0.90), masked | 8.45 | 0.433 | 0.29 | 7.84 | 0.116 |
| head framing + rot90 + strip + argmax | 40.13 | 0.412 | 0.23 | 33.25 | 0.026 |
| head framing (fill 0.92) + rot90 + argmax (unstripped, full FOV) | 221.32 | 0.113 | 0.42 | 220.29 | 0.007 |
| head framing, all 8 orientations / fill 0.85–1.0 / slab 3–5 mm | 73–416 | 0.06–0.14 | | 67–416 | ≤ 0.008 |

Findings:
* Showing the model the whole head (training-like framing) is catastrophic on this 3D 1 mm
  FLAIR: false positives in every slice including neck/face slices (the full FOV extends ~47
  slices below the brain) — the extra-cerebral contrast of this acquisition differs from the
  1.5 T 2D clinical training data. Thick-slice emulation makes it worse.
* The training orientation (rot90) and skull removal each help; with both, the upstream
  argmax rule gives a volume matching the ensemble on the lesion-rich subject (17.3 vs
  16.4 mL) with the best agreement of all 28 candidates, no out-of-brain voxels, and no
  need for the old volume-matching 0.90 threshold.
* On the low-load subject **no configuration works**: BAWIL mostly segments cortical
  hyperintensities (≈ 60 % of its voxels on SynthSeg cortex labels). The previous code's
  smaller false-positive volume there came only from its 0.90 threshold, which halves the
  true lesion volume on sub-019.
* Conclusion: the model is only partly in-domain for this cohort's FLAIR. It stays in the
  default ensemble with the principled presentation above (STAPLE down-weights it where it
  disagrees); if a larger cohort confirms the low-load behaviour, move it to opt-in like
  TrueNet (`--skip_algorithms bawil`).

Reproduce: the harness scripts live outside the repo; rerun `bawil_filter.py` with the flags
above inside the container on `preproc/*space-FLAIR_desc-resampled_FLAIR.nii.gz` +
`*space-FLAIR_desc-brain_mask.nii.gz`, warp with `xfm/` (`from-T1w_to-MNI` then
`from-FLAIR_to-T1w`), and score against `lesions/`.

## Output Target
`sub-*/ses-*/lesions/sub-*_ses-*_space-MNI_desc-bawil_{mask,probseg}.nii.gz` (brain-masked,
see README "Outputs"); native outputs only with `--publish_native`.
