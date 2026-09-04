#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conform SynthSeg multiclass segmentation to reference geometry.

Extracts white matter lesion labels (default: label 77) from SynthSeg
segmentations and resamples masks to match reference image geometry.
"""

import argparse
import nibabel as nib
import numpy as np
from scipy.ndimage import affine_transform


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Conform SynthSeg multiclass output to reference geometry")
    parser.add_argument("--input", required=True, help="Input SynthSeg multiclass NIfTI segmentation file")
    parser.add_argument("--ref", required=True, help="Reference NIfTI image for geometry matching")
    parser.add_argument("--output", required=True, help="Output binary lesion mask NIfTI file")
    parser.add_argument("--label_id", type=int, default=77, help="Label ID for white matter lesions (default: 77)")
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    ref = nib.load(args.ref)
    img = nib.load(args.input)
    # Extract specified lesion label from multiclass segmentation volume.
    data = (img.get_fdata() == args.label_id).astype(np.uint8)

    # Resample segmentation array if dimensions or affine matrix differ from reference.
    if data.shape != ref.shape or not np.allclose(img.affine, ref.affine, atol=1e-3):
        T = np.linalg.inv(img.affine) @ ref.affine
        conformed = affine_transform(data, T[:3, :3], offset=T[:3, 3], output_shape=ref.shape, order=0)
        data = (conformed > 0).astype(np.uint8)

    out_img = nib.Nifti1Image(data, ref.affine, ref.header)
    out_img.set_data_dtype(np.uint8)
    nib.save(out_img, args.output)


if __name__ == "__main__":
    main()
