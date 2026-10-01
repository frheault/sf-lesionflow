#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export nnU-Net softmax probabilities (.npz) to a native-space NIfTI map.

Handles both nnU-Net generations used in this pipeline:

- nnU-Net v1 (`nnUNet_predict -z`, MARS-WMH): the `softmax` array is resampled
  back to the original spacing but is still CROPPED to the nonzero bounding box.
  The sibling `.pkl` (`crop_bbox`, `original_size_of_raw_data`) is used to pad
  it back into the full image grid, exactly like nnU-Net v1's own
  `save_segmentation_nifti_from_softmax` does for the label map.
- nnU-Net v2 (`nnUNetv2_predict --save_probabilities`, FLAMeS / Emory Robust):
  the `probabilities` array is already reverted to the full original shape.

Both arrays are in SimpleITK (z, y, x) order (all models here use SimpleITKIO),
so geometry is copied from the nnU-Net INPUT image (`--ref`) with SimpleITK
rather than re-derived from a nibabel affine. Several npz files are averaged
(this is what `nnUNetv2_ensemble` does). With `--target`, the map is linearly
resampled (identity transform, physical space) onto another image's grid.

With `--check_mask`, reports the Dice between `prob >= 0.5` and the tool's own
binary output as an alignment sanity check (a misaligned export gives ~0).
"""

import argparse
import os
import pickle
import sys

import numpy as np
import SimpleITK as sitk


def build_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--npz", nargs="+", required=True, help="nnU-Net .npz file(s); several are averaged")
    parser.add_argument("--ref", required=True, help="nnU-Net input image (defines the probability grid)")
    parser.add_argument("--output", required=True, help="Output probability NIfTI")
    parser.add_argument("--class_index", type=int, default=1, help="Foreground class channel (default: 1)")
    parser.add_argument("--target", help="Optional image to linearly resample the map onto")
    parser.add_argument("--check_mask", help="Optional binary mask (on the output grid) for a Dice sanity check")
    return parser


def load_foreground(npz_path, class_index, ref_shape_zyx):
    data = np.load(npz_path)
    key = "probabilities" if "probabilities" in data.files else "softmax"
    prob = data[key][class_index].astype(np.float32)
    if prob.shape == tuple(ref_shape_zyx):
        return prob

    # nnU-Net v1: cropped to the nonzero bounding box -> pad back
    pkl_path = npz_path[:-4] + ".pkl"
    if not os.path.isfile(pkl_path):
        sys.exit(f"Error: {npz_path} has shape {prob.shape} != reference {tuple(ref_shape_zyx)} "
                 f"and no {pkl_path} is available to undo cropping")
    with open(pkl_path, "rb") as f:
        props = pickle.load(f)
    full_shape = tuple(int(s) for s in props["original_size_of_raw_data"])
    if full_shape != tuple(ref_shape_zyx):
        sys.exit(f"Error: nnU-Net original size {full_shape} != reference {tuple(ref_shape_zyx)}")
    full = np.zeros(full_shape, dtype=np.float32)
    bbox = props.get("crop_bbox")
    if bbox is None:
        sys.exit(f"Error: {pkl_path} has no crop_bbox")
    sl = tuple(slice(int(b[0]), min(int(b[0]) + prob.shape[c], full_shape[c])) for c, b in enumerate(bbox))
    full[sl] = prob[tuple(slice(0, s.stop - s.start) for s in sl)]
    return full


def main():
    args = build_arg_parser().parse_args()

    ref = sitk.ReadImage(args.ref)
    ref_shape_zyx = ref.GetSize()[::-1]
    prob = np.mean([load_foreground(p, args.class_index, ref_shape_zyx) for p in args.npz], axis=0)

    img = sitk.GetImageFromArray(np.clip(prob, 0.0, 1.0).astype(np.float32))
    img.CopyInformation(ref)
    if args.target:
        target = sitk.ReadImage(args.target)
        img = sitk.Resample(img, target, sitk.Transform(), sitk.sitkLinear, 0.0, sitk.sitkFloat32)
    sitk.WriteImage(img, args.output)

    out = sitk.GetArrayFromImage(img)
    print(f"Probability map: shape={out.shape[::-1]} min={out.min():.4f} max={out.max():.4f} "
          f"voxels>=0.5: {int((out >= 0.5).sum())}")

    if args.check_mask:
        mask = sitk.GetArrayFromImage(sitk.ReadImage(args.check_mask)) > 0
        if mask.shape != out.shape:
            print(f"Warning: check_mask shape {mask.shape[::-1]} != probability grid {out.shape[::-1]}")
        else:
            pred = out >= 0.5
            denom = pred.sum() + mask.sum()
            dice = 2.0 * np.logical_and(pred, mask).sum() / denom if denom else 1.0
            print(f"Sanity check: Dice(prob>=0.5, binary mask) = {dice:.4f}")


if __name__ == "__main__":
    main()
