#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Finalize one algorithm's MNI-space lesion prediction for publication.

Single producer of every published per-algorithm lesion file:
  1. checks that the binary mask and probability map are on the MNI template grid;
  2. binarizes the mask (uint8) and clips the probability map to [0, 1] (float32);
     FAST-outlier's map is a z-score, written unclipped as `_zscore`;
  3. optionally multiplies both by the (dilated) MNI brain mask -- used for algorithms
     whose input still contained the skull, so no lesion can sit outside the brain;
  4. writes BIDS-derivatives names plus a JSON sidecar describing what was done.
"""

import argparse
import json

import nibabel as nib
import numpy as np
from scipy.ndimage import binary_dilation


def build_arg_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prefix", required=True, help="Output prefix, e.g. sub-01_ses-1")
    p.add_argument("--algo", required=True, help="Algorithm key, e.g. lst_ai")
    p.add_argument("--label", required=True, help="BIDS desc- label, e.g. lstai")
    p.add_argument("--space", default="MNI", help="BIDS space- label of the template grid")
    p.add_argument("--binary", required=True, help="Binary lesion mask on the template grid")
    p.add_argument("--prob", default=None, help="Probability map on the template grid (optional)")
    p.add_argument("--template", required=True, help="Template image defining the output grid")
    p.add_argument("--brainmask", default=None, help="MNI brain mask (required with --apply_brainmask)")
    p.add_argument("--apply_brainmask", action="store_true", help="Zero predictions outside the brain mask")
    p.add_argument("--dilation", type=int, default=1, help="Brain mask dilation in voxels (default: 1)")
    p.add_argument("--input_space", default="MNI", help="Space the algorithm ran in (for the sidecar)")
    p.add_argument("--zscore", action="store_true", help="The prob map is a z-score (no [0,1] clipping)")
    return p


def load_on_grid(path, ref, what):
    img = nib.load(path)
    data = np.asanyarray(img.dataobj)
    data = np.squeeze(data)
    if data.ndim != 3:
        raise SystemExit(f"{what} '{path}' is {data.ndim}D, expected 3D")
    if data.shape != ref.shape[:3]:
        raise SystemExit(f"{what} '{path}' has shape {data.shape}, template grid is {ref.shape[:3]}")
    if not np.allclose(img.affine, ref.affine, atol=1e-3):
        raise SystemExit(f"{what} '{path}' affine differs from the template affine:\n{img.affine}\nvs\n{ref.affine}")
    return data


def main():
    args = build_arg_parser().parse_args()
    ref = nib.load(args.template)

    binary = load_on_grid(args.binary, ref, "binary mask") > 0
    prob = None
    prob_is_binary = False
    if args.prob:
        prob = np.nan_to_num(load_on_grid(args.prob, ref, "probability map").astype(np.float32))
        if not args.zscore:
            prob = np.clip(prob, 0.0, 1.0)
            prob_is_binary = np.unique(prob).size <= 2
    else:
        # No soft output for this algorithm: publish its decision as a {0,1} map.
        prob = binary.astype(np.float32)
        prob_is_binary = True

    voxel_ml = float(np.prod(ref.header.get_zooms()[:3])) / 1000.0
    removed = 0
    if args.apply_brainmask:
        if not args.brainmask:
            raise SystemExit("--apply_brainmask requires --brainmask")
        brain = load_on_grid(args.brainmask, ref, "brain mask") > 0
        if args.dilation > 0:
            brain = binary_dilation(brain, iterations=args.dilation)
        removed = int((binary & ~brain).sum())
        binary &= brain
        prob = np.where(brain, prob, 0).astype(np.float32)

    def save(data, dtype, name):
        img = nib.Nifti1Image(data.astype(dtype), ref.affine)
        img.set_qform(ref.affine, code=int(ref.header["qform_code"]) or 1)
        img.set_sform(ref.affine, code=int(ref.header["sform_code"]) or 1)
        img.set_data_dtype(dtype)
        nib.save(img, name)

    stem = f"{args.prefix}_space-{args.space}_desc-{args.label}"
    save(binary, np.uint8, f"{stem}_mask.nii.gz")
    save(prob, np.float32, f"{stem}_{'zscore' if args.zscore else 'probseg'}.nii.gz")

    sidecar = {
        "Algorithm": args.algo,
        "Space": args.space,
        "InputSpace": args.input_space,
        "BrainMaskApplied": bool(args.apply_brainmask),
        "BrainMaskDilationVoxels": args.dilation if args.apply_brainmask else 0,
        "VoxelsRemovedByBrainMask": removed,
        "VolumeRemovedByBrainMask_MNI_mL": round(removed * voxel_ml, 4),
        "Volume_MNI_mL": round(float(binary.sum()) * voxel_ml, 4),
        "ProbabilityIsBinary": bool(prob_is_binary),
        "VolumeDefinition": "Voxels on the template grid after affine normalization of the baseline T1w "
                            "(head-size normalized). Native volume ~= Volume_MNI_mL / Affine_Scale_Factor.",
    }
    with open(f"{stem}_mask.json", "w") as f:
        json.dump(sidecar, f, indent=2)


if __name__ == "__main__":
    main()
