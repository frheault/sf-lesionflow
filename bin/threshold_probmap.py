#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import glob
import sys
import nibabel as nib
import numpy as np

def build_arg_parser():
    parser = argparse.ArgumentParser(description="Threshold a probability map NIfTI file to create a binary mask")
    parser.add_argument("--input", help="Input probability map NIfTI file")
    parser.add_argument("--input_glob", help="Glob pattern to match input probability map NIfTI file")
    parser.add_argument("--output", required=True, help="Output binary mask NIfTI file")
    parser.add_argument("--threshold", type=float, default=0.5, help="Probability threshold (default: 0.5)")
    return parser

def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    input_file = args.input
    if not input_file and args.input_glob:
        matched = glob.glob(args.input_glob)
        if not matched:
            sys.exit(f"Error: No files matched pattern '{args.input_glob}'")
        input_file = matched[0]

    if not input_file:
        sys.exit("Error: Either --input or --input_glob must be specified")

    img = nib.load(input_file)
    data = img.get_fdata()
    binary = (data >= args.threshold).astype(np.uint8)

    out_img = nib.Nifti1Image(binary, img.affine, img.header)
    out_img.set_data_dtype(np.uint8)
    nib.save(out_img, args.output)

if __name__ == "__main__":
    main()
