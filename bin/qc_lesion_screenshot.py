#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate high-contrast triplanar slice montages with lesion segmentation contours."""

import argparse
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
from scipy.ndimage import binary_dilation


def main():
    parser = argparse.ArgumentParser(description="MultiQC Lesion Screenshot Generator")
    parser.add_argument("--meta_id", required=True, help="Session identifier (sub-XX_ses-YY)")
    parser.add_argument("--anat", required=True, help="Underlying anatomical image (FLAIR .nii.gz)")
    parser.add_argument("--mask", required=True, help="Consensus binary lesion mask (.nii.gz)")
    parser.add_argument("--out_png", required=True, help="Output screenshot PNG")
    args = parser.parse_args()

    anat_img = nib.as_closest_canonical(nib.load(args.anat))
    mask_img = nib.as_closest_canonical(nib.load(args.mask))

    anat = np.squeeze(anat_img.get_fdata())
    mask = np.squeeze(mask_img.get_fdata()) > 0

    while anat.ndim < 3:
        anat = np.expand_dims(anat, axis=-1)
    if anat.ndim > 3:
        anat = anat[..., 0]

    while mask.ndim < 3:
        mask = np.expand_dims(mask, axis=-1)
    if mask.ndim > 3:
        mask = mask[..., 0]

    if mask.shape != anat.shape:
        aligned_mask = np.zeros_like(anat, dtype=bool)
        min_shape = [min(a, m) for a, m in zip(anat.shape, mask.shape)]
        aligned_mask[: min_shape[0], : min_shape[1], : min_shape[2]] = mask[: min_shape[0], : min_shape[1], : min_shape[2]]
        mask = aligned_mask

    # Normalize anatomical contrast
    anat = np.nan_to_num(anat)
    if np.any(anat > 0):
        p99 = np.percentile(anat[anat > 0], 99)
        if p99 > 0:
            anat = np.clip(anat / p99, 0, 1)

    # Find the axial, coronal, and sagittal slices with the maximum lesion volume
    if np.any(mask):
        ax_counts = np.sum(mask, axis=(0, 1))
        cor_counts = np.sum(mask, axis=(0, 2))
        sag_counts = np.sum(mask, axis=(1, 2))

        best_ax = int(np.argmax(ax_counts))
        best_cor = int(np.argmax(cor_counts))
        best_sag = int(np.argmax(sag_counts))
    else:
        best_ax = anat.shape[2] // 2
        best_cor = anat.shape[1] // 2
        best_sag = anat.shape[0] // 2

    # Bounds check
    best_ax = min(max(0, best_ax), anat.shape[2] - 1)
    best_cor = min(max(0, best_cor), anat.shape[1] - 1)
    best_sag = min(max(0, best_sag), anat.shape[0] - 1)

    best_ax_m = min(best_ax, mask.shape[2] - 1)
    best_cor_m = min(best_cor, mask.shape[1] - 1)
    best_sag_m = min(best_sag, mask.shape[0] - 1)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor="black")

    slices = [
        (np.rot90(anat[:, :, best_ax]), np.rot90(mask[:, :, best_ax_m]), f"Axial Slice Z={best_ax}"),
        (np.rot90(anat[:, best_cor, :]), np.rot90(mask[:, best_cor_m, :]), f"Coronal Slice Y={best_cor}"),
        (np.rot90(anat[best_sag, :, :]), np.rot90(mask[best_sag_m, :, :]), f"Sagittal Slice X={best_sag}"),
    ]

    for idx, (a_sl, m_sl, title) in enumerate(slices):
        axes[idx].imshow(a_sl, cmap="gray", origin="upper")
        if np.any(m_sl):
            dilated = binary_dilation(m_sl, iterations=1)
            border = dilated ^ m_sl
            rgba_mask = np.zeros((*m_sl.shape, 4), dtype=np.float32)
            rgba_mask[m_sl] = [1.0, 0.0, 0.0, 0.5]    # Semi-transparent red
            rgba_mask[border] = [1.0, 1.0, 0.0, 1.0]  # Solid yellow border
            axes[idx].imshow(rgba_mask, origin="upper")

        axes[idx].set_title(title, color="white", fontsize=12)
        axes[idx].axis("off")

    status = "Lesions Detected" if np.any(mask) else "No Lesions Detected (Zero Mask)"
    plt.suptitle(f"{args.meta_id} STAPLE Consensus Segmentation ({status})", color="white", fontsize=14)
    plt.tight_layout()
    plt.savefig(args.out_png, facecolor="black", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
