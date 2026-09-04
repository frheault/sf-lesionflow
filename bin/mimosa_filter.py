#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import numpy as np
import nibabel as nib
from scipy.ndimage import gaussian_filter
from _lesion_utils import filter_small_components

def build_arg_parser():
    parser = argparse.ArgumentParser(description="MIMoSA Heuristic Proxy Lesion Segmentation")
    parser.add_argument("--t1", required=True, help="Input T1w NIfTI image")
    parser.add_argument("--flair", required=True, help="Input FLAIR NIfTI image")
    parser.add_argument("--output", required=True, help="Output binary lesion mask NIfTI file")
    parser.add_argument("--prob_threshold", type=float, default=0.30, help="Probability threshold for lesion candidate binarization (default: 0.30)")
    parser.add_argument("--flair_cand_threshold", type=float, default=1.5, help="Normalized FLAIR candidate threshold (default: 1.5)")
    parser.add_argument("--min_cluster_size", type=int, default=3, help="Minimum connected component size (default: 3)")
    return parser

def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    t1_img = nib.load(args.t1)
    flair_img = nib.load(args.flair)
    t1_data = t1_img.get_fdata().astype(np.float32)
    flair_data = flair_img.get_fdata().astype(np.float32)
    brain_mask = (t1_data > 0) & (flair_data > 0)

    if np.sum(brain_mask) == 0:
        empty_out = np.zeros(flair_data.shape, dtype=np.uint8)
        nib.save(nib.Nifti1Image(empty_out, flair_img.affine, flair_img.header), args.output)
        sys.exit(0)

    t1_norm = np.zeros_like(t1_data)
    t1_norm[brain_mask] = (t1_data[brain_mask] - np.mean(t1_data[brain_mask])) / (np.std(t1_data[brain_mask]) or 1.0)

    flair_norm = np.zeros_like(flair_data)
    flair_norm[brain_mask] = (flair_data[brain_mask] - np.mean(flair_data[brain_mask])) / (np.std(flair_data[brain_mask]) or 1.0)

    flair_sm1 = gaussian_filter(flair_norm, sigma=1.0)
    flair_sm2 = gaussian_filter(flair_norm, sigma=2.0)
    flair_var = np.sqrt(np.maximum(0, gaussian_filter(flair_norm**2, sigma=1.0) - flair_sm1**2))
    intermodal = flair_norm - t1_norm
    local_contrast = flair_norm - flair_sm2

    cand = (flair_norm > args.flair_cand_threshold) & brain_mask
    logit = -4.0 + 2.2*np.maximum(0, flair_norm-1.5) + 1.8*np.maximum(0, intermodal-0.5) + 1.5*np.maximum(0, local_contrast-0.3) + 0.8*flair_var

    prob = np.zeros_like(flair_data, dtype=np.float32)
    prob[cand] = 1.0 / (1.0 + np.exp(-np.clip(logit[cand], -20.0, 20.0)))
    binary = ((prob >= args.prob_threshold) & cand).astype(np.uint8)
    binary = filter_small_components(binary, args.min_cluster_size)

    out_img = nib.Nifti1Image(binary, flair_img.affine, flair_img.header)
    out_img.set_data_dtype(np.uint8)
    nib.save(out_img, args.output)

if __name__ == "__main__":
    main()
