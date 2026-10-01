#!/usr/bin/env python3
"""Binary mask generator for nonzero volume voxels."""

import argparse

import nibabel as nib
import numpy as np


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Create a binary mask from non-zero voxels of an input image")
    parser.add_argument("--input", required=True, help="Input NIfTI image")
    parser.add_argument("--output", required=True, help="Output binary mask NIfTI file")
    parser.add_argument(
        "--dilate", type=int, default=0,
        help="Number of binary dilation iterations (voxels) to expand the mask (default: 0)"
    )
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    img = nib.load(args.input)
    data = img.get_fdata()
    mask = (data > 0).astype(np.uint8)

    if args.dilate > 0:
        from scipy.ndimage import binary_dilation
        mask = binary_dilation(mask, iterations=args.dilate).astype(np.uint8)

    out_img = nib.Nifti1Image(mask, img.affine, img.header)
    out_img.set_data_dtype(np.uint8)
    nib.save(out_img, args.output)


if __name__ == "__main__":
    main()
