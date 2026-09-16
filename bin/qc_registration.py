#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract registration similarity metrics and generate visual checkerboard overlays."""

import argparse
import os
import re
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt


def create_checkerboard(img1, img2, square_size=16):
    """Create checkerboard composite of two 2D image slices."""
    if img1.shape != img2.shape:
        min_shape = (min(img1.shape[0], img2.shape[0]), min(img1.shape[1], img2.shape[1]))
        img1 = img1[:min_shape[0], :min_shape[1]]
        img2 = img2[:min_shape[0], :min_shape[1]]
    cb = np.zeros_like(img1)
    mask = (np.indices(img1.shape) // square_size).sum(axis=0) % 2 == 0
    cb[mask] = img1[mask]
    cb[~mask] = img2[~mask]
    return cb


def parse_ants_metric(log_file):
    """Extract final similarity metric value from ANTs registration log."""
    if not log_file or not os.path.isfile(log_file):
        return None
    final_metric = None
    num_pattern = r"(-?[\d\.]+(?:[eE][-+]?\d+)?)"
    with open(log_file, "r") as f:
        for line in f:
            # Matches ANTs iteration logs: 1: 0.123456...
            m = re.search(rf"DIAGNOSTIC,iteration,\d+,metricValue,{num_pattern}", line)
            if m:
                final_metric = float(m.group(1))
            else:
                m2 = re.search(rf"2: Metric value: {num_pattern}", line)
                if m2:
                    final_metric = float(m2.group(1))
                else:
                    m3 = re.search(rf"Final metric value = {num_pattern}", line)
                    if m3:
                        final_metric = float(m3.group(1))
    return final_metric


def main():
    parser = argparse.ArgumentParser(description="MultiQC Registration QC Extractor")
    parser.add_argument("--meta_id", required=True, help="Session identifier (sub-XX_ses-YY)")
    parser.add_argument(
        "--stage",
        required=True,
        choices=["flair_to_t1", "t1_to_baseline", "baseline_to_mni"],
        help="Which of the three ANTs registration stages this invocation covers",
    )
    parser.add_argument("--fixed", required=True, help="Fixed reference volume (.nii.gz)")
    parser.add_argument("--moving_warped", required=True, help="Moving volume warped to fixed (.nii.gz)")
    parser.add_argument("--log", required=False, help="ANTs registration stdout/log file")
    parser.add_argument("--out_metrics", required=True, help="Output registration metrics TSV")
    parser.add_argument("--out_png", required=True, help="Output checkerboard screenshot PNG")
    args = parser.parse_args()

    # 1. Parse similarity metric
    metric_val = parse_ants_metric(args.log)
    metric_str = f"{metric_val:.4f}" if metric_val is not None else "N/A"

    sample_id = f"{args.meta_id}_{args.stage}"

    with open(args.out_metrics, "w") as f:
        f.write("# id: 'registration_metrics'\n")
        f.write("# section_name: 'Spatial Registration Performance'\n")
        f.write("# plot_type: 'table'\n")
        f.write("Sample\tStage\tFinal_Metric_Value\n")
        f.write(f"{sample_id}\t{args.stage}\t{metric_str}\n")

    # 2. Generate Triplanar Checkerboard Overlay
    fixed_nii = nib.as_closest_canonical(nib.load(args.fixed))
    warped_nii = nib.as_closest_canonical(nib.load(args.moving_warped))

    f_data = np.squeeze(fixed_nii.get_fdata())
    w_data = np.squeeze(warped_nii.get_fdata())

    while f_data.ndim < 3:
        f_data = np.expand_dims(f_data, axis=-1)
    if f_data.ndim > 3:
        f_data = f_data[..., 0]

    while w_data.ndim < 3:
        w_data = np.expand_dims(w_data, axis=-1)
    if w_data.ndim > 3:
        w_data = w_data[..., 0]

    # Normalize intensity to [0, 1]
    f_data = np.nan_to_num(f_data)
    w_data = np.nan_to_num(w_data)
    if np.any(f_data > 0):
        p99_f = np.percentile(f_data[f_data > 0], 99)
        if p99_f > 0:
            f_data = np.clip(f_data / p99_f, 0, 1)
    if np.any(w_data > 0):
        p99_w = np.percentile(w_data[w_data > 0], 99)
        if p99_w > 0:
            w_data = np.clip(w_data / p99_w, 0, 1)

    shape = f_data.shape
    mid_ax = shape[2] // 2
    mid_cor = shape[1] // 2
    mid_sag = shape[0] // 2

    # Handle slice indices safely
    mid_ax = max(0, min(mid_ax, f_data.shape[2] - 1))
    mid_cor = max(0, min(mid_cor, f_data.shape[1] - 1))
    mid_sag = max(0, min(mid_sag, f_data.shape[0] - 1))

    mid_ax_w = max(0, min(mid_ax, w_data.shape[2] - 1))
    mid_cor_w = max(0, min(mid_cor, w_data.shape[1] - 1))
    mid_sag_w = max(0, min(mid_sag, w_data.shape[0] - 1))

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor="black")

    ax_cb = create_checkerboard(f_data[:, :, mid_ax], w_data[:, :, mid_ax_w])
    cor_cb = create_checkerboard(f_data[:, mid_cor, :], w_data[:, mid_cor_w, :])
    sag_cb = create_checkerboard(f_data[mid_sag, :, :], w_data[mid_sag_w, :, :])

    axes[0].imshow(np.rot90(ax_cb), cmap="gray")
    axes[0].set_title(f"Axial (Z={mid_ax})", color="white")
    axes[0].axis("off")

    axes[1].imshow(np.rot90(cor_cb), cmap="gray")
    axes[1].set_title(f"Coronal (Y={mid_cor})", color="white")
    axes[1].axis("off")

    axes[2].imshow(np.rot90(sag_cb), cmap="gray")
    axes[2].set_title(f"Sagittal (X={mid_sag})", color="white")
    axes[2].axis("off")

    plt.suptitle(
        f"{args.meta_id} [{args.stage}] Coregistration Checkerboard (Fixed vs Warped)",
        color="white",
        fontsize=14,
    )
    plt.tight_layout()
    plt.savefig(args.out_png, facecolor="black", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
