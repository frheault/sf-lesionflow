#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import nibabel as nib
import numpy as np

def build_arg_parser():
    parser = argparse.ArgumentParser(description="FSL FAST White Matter Outlier Lesion Segmentation")
    parser.add_argument("--flair", required=True, help="Input FLAIR NIfTI image")
    parser.add_argument("--wm_pve", required=True, help="Input FAST WM PVE NIfTI image (e.g. fast_pve_2.nii.gz)")
    parser.add_argument("--output", required=True, help="Output binary lesion mask NIfTI file")
    parser.add_argument("--sigma", type=float, default=2.5, help="Standard deviation multiplier for thresholding (default: 2.5)")
    parser.add_argument("--pve_threshold", type=float, default=0.95, help="PVE threshold for healthy white matter (default: 0.95)")
    parser.add_argument("--dwm_threshold", type=float, default=0.50, help="Deep white matter mask threshold (default: 0.50)")
    return parser

def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    flair_img = nib.load(args.flair)
    wm_img = nib.load(args.wm_pve)
    flair_data = flair_img.get_fdata()
    wm_data = wm_img.get_fdata()

    pure_wm = wm_data > args.pve_threshold
    if np.sum(pure_wm) < 100:
        pure_wm = wm_data > 0.80
    if np.sum(pure_wm) < 50:
        pure_wm = wm_data > 0.50

    healthy_flair = flair_data[pure_wm]
    mean_wm = float(np.mean(healthy_flair))
    std_wm = float(np.std(healthy_flair))
    threshold = mean_wm + args.sigma * std_wm

    dwm_mask = wm_data > args.dwm_threshold
    lesion_mask = (flair_data > threshold) & dwm_mask

    out_img = nib.Nifti1Image(lesion_mask.astype(np.uint8), flair_img.affine, flair_img.header)
    out_img.set_data_dtype(np.uint8)
    nib.save(out_img, args.output)

if __name__ == "__main__":
    main()
