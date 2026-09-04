#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import numpy as np
import nibabel as nib
from scipy.ndimage import gaussian_filter
from _lesion_utils import filter_small_components

def build_arg_parser():
    parser = argparse.ArgumentParser(description="SHiVAi Heuristic Proxy Lesion Segmentation")
    parser.add_argument("--t1", required=True, help="Input T1w NIfTI image")
    parser.add_argument("--flair", required=True, help="Input FLAIR NIfTI image")
    parser.add_argument("--output", required=True, help="Output binary lesion mask NIfTI file")
    parser.add_argument("--prob_threshold", type=float, default=0.50, help="Probability threshold for lesion binarization (default: 0.50)")
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
    t1_norm[brain_mask] = np.clip((t1_data[brain_mask] - np.mean(t1_data[brain_mask])) / (np.std(t1_data[brain_mask]) or 1.0), -4.0, 4.0)

    flair_norm = np.zeros_like(flair_data)
    flair_norm[brain_mask] = np.clip((flair_data[brain_mask] - np.mean(flair_data[brain_mask])) / (np.std(flair_data[brain_mask]) or 1.0), -4.0, 10.0)

    f_sm_low = gaussian_filter(flair_norm, sigma=1.0)
    f_sm_high = gaussian_filter(flair_norm, sigma=2.5)
    f_contrast = flair_norm - f_sm_high
    f_grad = np.sqrt(np.gradient(f_sm_low, axis=0)**2 + np.gradient(f_sm_low, axis=1)**2 + np.gradient(f_sm_low, axis=2)**2)

    cross_sal = np.maximum(0, flair_norm - 1.0) * (1.0 + 0.5 * np.maximum(0, -t1_norm))
    logit = -3.8 + 2.2*np.maximum(0, flair_norm-1.0) + 1.6*f_contrast + 1.2*cross_sal - 0.6*f_grad

    prob = np.zeros_like(flair_data, dtype=np.float32)
    prob[brain_mask] = 1.0 / (1.0 + np.exp(-np.clip(logit[brain_mask], -20.0, 20.0)))
    binary = ((prob >= args.prob_threshold) & brain_mask).astype(np.uint8)
    binary = filter_small_components(binary, args.min_cluster_size)

    out_img = nib.Nifti1Image(binary, flair_img.affine, flair_img.header)
    out_img.set_data_dtype(np.uint8)
    nib.save(out_img, args.output)

if __name__ == "__main__":
    main()
