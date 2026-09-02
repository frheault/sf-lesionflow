#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import nibabel as nib
import numpy as np

def build_arg_parser():
    parser = argparse.ArgumentParser(description="Create a binary mask from non-zero voxels of an input image")
    parser.add_argument("--input", required=True, help="Input NIfTI image")
    parser.add_argument("--output", required=True, help="Output binary mask NIfTI file")
    return parser

def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    img = nib.load(args.input)
    data = img.get_fdata()
    mask = (data > 0).astype(np.uint8)

    out_img = nib.Nifti1Image(mask, img.affine, img.header)
    out_img.set_data_dtype(np.uint8)
    nib.save(out_img, args.output)

if __name__ == "__main__":
    main()
