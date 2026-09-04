#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import re
import numpy as np
import nibabel as nib
import pandas as pd
from _lesion_utils import filter_small_components, watershed_instances

def build_arg_parser():
    parser = argparse.ArgumentParser(description="Longitudinal STAPLE Harmonization & Lesion Tracking Audit Trail")
    parser.add_argument("--subject", required=True, help="Subject identifier (e.g. sub-003)")
    parser.add_argument("--masks", nargs="+", required=True, help="List of session consensus binary mask NIfTI files")
    parser.add_argument("--out_csv", required=True, help="Output lesion tracking CSV file")
    parser.add_argument("--min_cluster_size", type=int, default=6, help="Minimum connected component size (default: 6)")
    parser.add_argument("--min_distance", type=int, default=3, help="Minimum peak distance for watershed (default: 3)")
    parser.add_argument("--gaussian_sigma", type=float, default=0.8, help="Gaussian smoothing sigma (default: 0.8)")
    parser.add_argument("--pct_change_threshold", type=float, default=20.0, help="Percentage change threshold for Enlarging/Shrinking (default: 20.0)")
    return parser

def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    subject = args.subject
    files = sorted(args.masks, key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', x)])
    session_names = []
    for idx, f in enumerate(files):
        m = re.search(r'ses-[0-9a-zA-Z]+', os.path.basename(f))
        session_names.append(m.group(0) if m else f"ses-{idx+1}")

    imgs = [nib.load(f) for f in files]
    voxel_sizes = imgs[0].header.get_zooms()[:3]
    voxel_vol = np.prod(voxel_sizes)
    affine = imgs[0].affine
    header = imgs[0].header

    stack = np.stack([img.get_fdata() > 0 for img in imgs], axis=-1)
    time_union = np.any(stack, axis=-1)

    time_union = filter_small_components(time_union, args.min_cluster_size)
    ws_harmonized = watershed_instances(time_union, min_distance=args.min_distance, gaussian_sigma=args.gaussian_sigma)

    for i, f in enumerate(files):
        ses = session_names[i]
        ses_mask = stack[..., i]
        ses_labels = np.where(ses_mask, ws_harmonized, 0).astype(np.uint16)
        ses_bin = (ses_labels > 0).astype(np.uint8)

        nib.save(nib.Nifti1Image(ses_bin, affine, header), f"{subject}_{ses}_staple_thr90_harmonized_binary.nii.gz")
        nib.save(nib.Nifti1Image(ses_labels, affine, header), f"{subject}_{ses}_staple_thr90_harmonized_labels_uint16.nii.gz")

    unique_labels = [l for l in np.unique(ws_harmonized) if l > 0]
    records = []
    for lid in unique_labels:
        roi = (ws_harmonized == lid)
        centroid = np.mean(np.argwhere(roi), axis=0) * np.array(voxel_sizes)
        row = {"Lesion_ID": lid}
        vols = []
        for idx, ses in enumerate(session_names):
            v = int(np.sum(roi & stack[..., idx])) * voxel_vol
            row[f"Vol_mm3_{ses}"] = round(v, 2)
            vols.append(v)

        if len(session_names) == 1:
            status, delta_v, pct = "Baseline", 0.0, 0.0
        else:
            v0, v1 = vols[0], vols[-1]
            delta_v = v1 - v0
            if v0 == 0 and v1 > 0:
                status, pct = "New", 100.0
            elif v0 > 0 and v1 == 0:
                status, pct = "Resolved", -100.0
            elif v0 == 0 and v1 == 0:
                status, pct = "Transient", 0.0
            else:
                pct = ((v1 - v0) / v0) * 100.0 if v0 > 0 else 0.0
                if pct > args.pct_change_threshold:
                    status = "Enlarging"
                elif pct < -args.pct_change_threshold:
                    status = "Shrinking"
                else:
                    status = "Stable"

        row.update({
            "Status": status,
            "Delta_Vol_mm3": round(delta_v, 2),
            "Pct_Change": round(pct, 2),
            "Centroid_X_mm": round(centroid[0], 2),
            "Centroid_Y_mm": round(centroid[1], 2),
            "Centroid_Z_mm": round(centroid[2], 2)
        })
        records.append(row)

    expected_cols = ["Lesion_ID"] + [f"Vol_mm3_{ses}" for ses in session_names] + [
        "Status", "Delta_Vol_mm3", "Pct_Change", "Centroid_X_mm", "Centroid_Y_mm", "Centroid_Z_mm"
    ]
    pd.DataFrame(records, columns=expected_cols).to_csv(args.out_csv, index=False)

if __name__ == "__main__":
    main()
