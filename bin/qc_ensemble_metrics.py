#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compute ensemble segmentation volume comparisons, pairwise Dice agreement,
and STAPLE consensus statistics for MultiQC reporting.
"""

import argparse
import os
import sys
import numpy as np
import nibabel as nib
import pandas as pd
from scipy.ndimage import label


def compute_dice(im1, im2):
    """Compute Dice similarity coefficient between two boolean arrays."""
    im1 = np.squeeze(im1)
    im2 = np.squeeze(im2)
    if im1.shape != im2.shape:
        return 0.0
    intersection = np.logical_and(im1, im2).sum()
    total = im1.sum() + im2.sum()
    if total == 0:
        return 1.0  # Both empty -> perfect agreement
    return float(2.0 * intersection / total)


def main():
    parser = argparse.ArgumentParser(description="MultiQC Ensemble Metrics Extractor")
    parser.add_argument("--meta_id", required=True, help="Session identifier (sub-XX_ses-YY)")
    parser.add_argument("--consensus", required=True, help="STAPLE consensus binary mask (.nii.gz)")
    parser.add_argument("--masks", nargs="+", required=True, help="Active algorithm binary masks")
    parser.add_argument("--out_volumes", required=True, help="Output volumes TSV for MultiQC bar chart")
    parser.add_argument("--out_dice", required=True, help="Output pairwise Dice TSV for MultiQC heatmap")
    parser.add_argument("--out_summary", required=True, help="Output summary scalar metrics TSV")
    args = parser.parse_args()

    # 1. Load STAPLE Consensus Mask
    cons_img = nib.as_closest_canonical(nib.load(args.consensus))
    cons_data = np.squeeze(cons_img.get_fdata()) > 0
    while cons_data.ndim < 3:
        cons_data = np.expand_dims(cons_data, axis=-1)
    if cons_data.ndim > 3:
        cons_data = cons_data[..., 0]
    voxel_size = float(np.prod(cons_img.header.get_zooms()[:3]))  # mm³ per voxel

    # Convert all volumes to mL at parse time (single unit path — never divide at write time).
    cons_vol_ml = float(cons_data.sum() * voxel_size) / 1000.0

    # Lesion count = number of connected components in the STAPLE binary mask.
    # This may differ from the watershed instance count in staple_thr90_labels_uint16.nii.gz,
    # which further splits components that are close together. Both are valid; be consistent.
    _, cons_num_lesions = label(cons_data)

    # 2. Parse Algorithms — store volumes in mL from the start
    algo_masks = {}
    algo_volumes_ml = {}  # always mL, never mm³
    algo_dice_vs_cons = {}

    for mask_path in sorted(args.masks):
        fname = os.path.basename(mask_path)
        # Extract algorithm name from filename pattern: {meta.id}_{algo}_binary.nii.gz
        clean_name = fname
        if clean_name.startswith(f"{args.meta_id}_"):
            clean_name = clean_name[len(args.meta_id) + 1 :]
        if clean_name.endswith("_binary.nii.gz"):
            clean_name = clean_name[:-len("_binary.nii.gz")]
        elif clean_name.endswith(".nii.gz"):
            clean_name = clean_name[:-len(".nii.gz")]

        img = nib.as_closest_canonical(nib.load(mask_path))
        data = np.squeeze(img.get_fdata()) > 0
        while data.ndim < 3:
            data = np.expand_dims(data, axis=-1)
        if data.ndim > 3:
            data = data[..., 0]
        algo_voxel_size = float(np.prod(img.header.get_zooms()[:3]))

        algo_masks[clean_name] = data
        algo_volumes_ml[clean_name] = float(data.sum() * algo_voxel_size) / 1000.0  # mL
        algo_dice_vs_cons[clean_name] = compute_dice(data, cons_data)

    # 3. Compute Pairwise Dice Matrix
    algo_names = list(algo_masks.keys())
    n_algos = len(algo_names)
    pairwise_dice = np.zeros((n_algos, n_algos), dtype=np.float32)

    for i in range(n_algos):
        for j in range(i, n_algos):
            d = compute_dice(algo_masks[algo_names[i]], algo_masks[algo_names[j]])
            pairwise_dice[i, j] = d
            pairwise_dice[j, i] = d

    # Mean Inter-Algorithm Dice
    if n_algos > 1:
        triu_indices = np.triu_indices(n_algos, k=1)
        mean_pairwise_dice = float(np.mean(pairwise_dice[triu_indices]))
    else:
        mean_pairwise_dice = 1.0

    # 4. Write Volume Comparison TSV (MultiQC Barplot Custom Content)
    # All values are in mL — consistent with cons_vol_ml and algo_volumes_ml.
    with open(args.out_volumes, "w") as f:
        f.write("# id: 'lesion_ensemble_volumes'\n")
        f.write("# section_name: 'Ensemble Lesion Volumes'\n")
        f.write("# description: 'Comparison of total lesion volume (mL) across active algorithms and STAPLE consensus.'\n")
        f.write("# plot_type: 'bargraph'\n")
        f.write("# pconfig:\n")
        f.write("#   id: 'lesion_ensemble_volumes_plot'\n")
        f.write("#   title: 'Ensemble Lesion Volume by Algorithm (mL)'\n")
        f.write("#   ylab: 'Volume (mL)'\n")

        headers = ["Sample"] + algo_names + ["STAPLE_Consensus"]
        f.write("\t".join(headers) + "\n")
        row = [args.meta_id] + [f"{algo_volumes_ml[a]:.3f}" for a in algo_names] + [f"{cons_vol_ml:.3f}"]
        f.write("\t".join(row) + "\n")

    # 5. Write Pairwise Dice Heatmap TSV
    with open(args.out_dice, "w") as f:
        f.write("# id: 'lesion_pairwise_dice'\n")
        f.write("# section_name: 'Inter-Algorithm Pairwise Dice Agreement'\n")
        f.write("# description: 'Pairwise Dice similarity coefficients between all active segmentation models.'\n")
        f.write("# plot_type: 'heatmap'\n")
        f.write("# pconfig:\n")
        f.write("#   id: 'lesion_pairwise_dice_heatmap'\n")
        f.write("#   title: 'Pairwise Dice Similarity Matrix'\n")
        f.write("#   min: 0.0\n")
        f.write("#   max: 1.0\n")

        headers = ["Algorithm"] + algo_names
        f.write("\t".join(headers) + "\n")
        for i, a_name in enumerate(algo_names):
            row = [a_name] + [f"{pairwise_dice[i, j]:.3f}" for j in range(n_algos)]
            f.write("\t".join(row) + "\n")

    # 6. Write Scalar Summary TSV (For General Statistics Table)
    with open(args.out_summary, "w") as f:
        f.write("# id: 'lesion_consensus_summary'\n")
        f.write("# section_name: 'STAPLE Consensus Lesion Metrics'\n")
        f.write("# plot_type: 'table'\n")
        f.write("Sample\tConsensus_TLV_mL\tConsensus_Lesion_Count\tMean_Inter_Algo_Dice\tActive_Algos\n")
        f.write(f"{args.meta_id}\t{cons_vol_ml:.3f}\t{cons_num_lesions}\t{mean_pairwise_dice:.3f}\t{n_algos}\n")


if __name__ == "__main__":
    main()
