#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import os
import numpy as np
import nibabel as nib
from scipy.ndimage import gaussian_filter, label

def build_arg_parser():
    parser = argparse.ArgumentParser(description="BAWIL Heuristic Proxy White Matter Lesion Segmentation")
    parser.add_argument("--flair", required=True, help="Input FLAIR NIfTI image")
    parser.add_argument("--output", required=True, help="Output binary lesion mask NIfTI file")
    parser.add_argument("--sigma", type=float, default=2.0, help="Gaussian smoothing sigma (default: 2.0)")
    parser.add_argument("--min_cluster_size", type=int, default=3, help="Minimum connected component size (default: 3)")
    return parser

def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    img = nib.load(args.flair)
    data = img.get_fdata().astype(np.float32)
    affine = img.affine
    header = img.header

    orig_shape = data.shape
    brain_mask = data > 0

    if np.sum(brain_mask) == 0:
        empty_out = np.zeros(orig_shape, dtype=np.uint8)
        nib.save(nib.Nifti1Image(empty_out, affine, header), args.output)
        sys.exit(0)

    mean_val = np.mean(data[brain_mask])
    std_val = np.std(data[brain_mask]) or 1.0
    norm_data = np.zeros_like(data)
    norm_data[brain_mask] = np.clip((data[brain_mask] - mean_val) / std_val, -3.0, 10.0)

    target_h, target_w = 256, 256
    nx, ny, nz = orig_shape
    pad_x = (target_h - nx) // 2
    pad_y = (target_w - ny) // 2
    pad_x_extra = target_h - (nx + pad_x)
    pad_y_extra = target_w - (ny + pad_y)

    class2_prob = np.zeros(orig_shape, dtype=np.float32)
    class1_prob = np.zeros(orig_shape, dtype=np.float32)

    for z in range(nz):
        m_2d = brain_mask[:, :, z]
        if np.sum(m_2d) < 10:
            continue
        s_2d = norm_data[:, :, z]
        padded = np.pad(s_2d, ((pad_x, pad_x_extra), (pad_y, pad_y_extra)), mode='constant')

        smooth_2 = gaussian_filter(padded, sigma=args.sigma)
        grad_mag = np.sqrt(np.gradient(padded, axis=0)**2 + np.gradient(padded, axis=1)**2)
        local_contrast = padded - smooth_2

        l0 = 3.0 - np.maximum(0, padded - 1.0) * 3.0
        l1 = np.maximum(0, padded - 1.2) * 1.5 + np.maximum(0, smooth_2 - 1.0) * 2.0 - np.maximum(0, local_contrast) * 2.0 - grad_mag
        l2 = -2.5 + np.maximum(0, padded - 1.8) * 3.0 + np.maximum(0, local_contrast - 0.5) * 3.5 + (padded > 2.5).astype(np.float32) * 2.0

        logits = np.stack([l0, l1, l2], axis=-1)
        exp_l = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probs = exp_l / np.sum(exp_l, axis=-1, keepdims=True)

        class1_prob[:, :, z] = probs[pad_x:pad_x+nx, pad_y:pad_y+ny, 1] * m_2d
        class2_prob[:, :, z] = probs[pad_x:pad_x+nx, pad_y:pad_y+ny, 2] * m_2d

    abnormal = ((class2_prob >= 0.5) & (class2_prob > class1_prob) & brain_mask).astype(np.uint8)
    labeled, n_f = label(abnormal)
    if n_f > 0:
        counts = np.bincount(labeled.ravel())
        abnormal[(counts < args.min_cluster_size)[labeled]] = 0

    out_img = nib.Nifti1Image(abnormal, affine, header)
    out_img.set_data_dtype(np.uint8)
    nib.save(out_img, args.output)

if __name__ == "__main__":
    main()
