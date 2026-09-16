#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Format longitudinal tracking audit trail CSV into MultiQC-compliant tables and trajectory summaries."""

import argparse
import re
import pandas as pd
import numpy as np


def _session_sort_key(col_name):
    m = re.search(r"ses-(\d+)", col_name)
    if m:
        return (0, int(m.group(1)))
    return (1, col_name)


def main():
    parser = argparse.ArgumentParser(description="MultiQC Longitudinal Trajectory Extractor")
    parser.add_argument("--subject", required=True, help="Subject identifier (e.g. sub-018)")
    parser.add_argument("--audit_csv", required=True, help="Longitudinal tracking audit trail CSV")
    parser.add_argument("--out_summary", required=True, help="Subject-level summary TSV for General Stats")
    parser.add_argument("--out_trajectories", required=True, help="Trajectory fate counts TSV for Barplot")
    parser.add_argument("--out_instances", required=True, help="Granular instance table TSV for MultiQC Table")
    args = parser.parse_args()

    try:
        df = pd.read_csv(args.audit_csv)
    except (pd.errors.EmptyDataError, FileNotFoundError):
        df = pd.DataFrame()

    vol_cols = sorted(
        [c for c in df.columns if c.startswith("Vol_mm3_")],
        key=_session_sort_key,
    )
    num_sessions = len(vol_cols)

    if len(df) == 0 or num_sessions == 0:
        total_vol_bl = 0.0
        total_vol_fu = 0.0
        net_delta_ml = 0.0
        pct_change_str = "0.0"
        no_lesions = True
        fate_counts = {}
    else:
        total_vol_bl = float(df[vol_cols[0]].sum()) / 1000.0
        total_vol_fu = float(df[vol_cols[-1]].sum()) / 1000.0
        net_delta_ml = total_vol_fu - total_vol_bl

        if total_vol_bl > 0:
            pct_change = (total_vol_fu - total_vol_bl) / total_vol_bl * 100.0
            pct_change_str = f"{pct_change:.1f}"
        elif total_vol_fu > 0:
            pct_change_str = "N/A"
        else:
            pct_change_str = "0.0"

        no_lesions = (df[vol_cols].sum().sum() == 0)
        fate_counts = df["Status"].value_counts().to_dict() if "Status" in df else {}

    new_count = fate_counts.get("New", 0)

    # 1. Write Subject-Level Summary for General Stats
    with open(args.out_summary, "w") as f:
        f.write("# id: 'longitudinal_summary'\n")
        f.write("# section_name: 'Longitudinal Trajectory Summary'\n")
        f.write("# plot_type: 'table'\n")
        f.write("Sample\tBaseline_TLV_mL\tFollowup_TLV_mL\tNet_Delta_TLV_mL\tPercent_Change\tNew_Lesions\tNo_Lesions_Flag\n")
        f.write(
            f"{args.subject}\t{total_vol_bl:.3f}\t{total_vol_fu:.3f}\t{net_delta_ml:.3f}\t{pct_change_str}\t{new_count}\t{int(no_lesions)}\n"
        )

    # 2. Write Trajectory Distribution for Stacked Barplot
    fates = ["New", "Enlarging", "Stable", "Shrinking", "Resolved", "Transient", "Baseline"]
    with open(args.out_trajectories, "w") as f:
        f.write("# id: 'lesion_trajectory_fates'\n")
        f.write("# section_name: 'Lesion Trajectory Classification'\n")
        f.write("# description: 'Distribution of individual lesion instance fates across longitudinal follow-up.'\n")
        f.write("# plot_type: 'bargraph'\n")
        f.write("# pconfig:\n")
        f.write("#   id: 'lesion_trajectory_fates_plot'\n")
        f.write("#   title: 'Lesion Fate Breakdown'\n")
        f.write("#   ylab: 'Number of Lesions'\n")

        headers = ["Sample"] + fates
        f.write("\t".join(headers) + "\n")
        counts_row = [args.subject] + [str(fate_counts.get(fate, 0)) for fate in fates]
        f.write("\t".join(counts_row) + "\n")

    # 3. Write Detailed Instance Table for Subject Report
    with open(args.out_instances, "w") as f:
        f.write("# id: 'lesion_instance_table'\n")
        f.write("# section_name: 'Tracked Lesion Instances (Audit Trail)'\n")
        f.write(
            "# description: 'Per-lesion instance metrics with 3D MNI centroid coordinates (mm) and trajectory classification.'\n"
        )
        f.write("# plot_type: 'table'\n")
        f.write("# pconfig:\n")
        f.write("#   id: 'lesion_instances_datatable'\n")
        f.write("#   title: 'Individual Lesion Audit Trail'\n")
        if len(df) == 0:
            empty_cols = ["Lesion_ID"] + vol_cols + [
                "Status",
                "Delta_Vol_mm3",
                "Pct_Change",
                "Centroid_X_mm",
                "Centroid_Y_mm",
                "Centroid_Z_mm",
            ]
            empty_row = {c: "N/A" for c in empty_cols}
            empty_row["Lesion_ID"] = "None"
            empty_row["Status"] = "No lesions detected"
            empty_row["Delta_Vol_mm3"] = 0.0
            empty_row["Pct_Change"] = "0.0"
            for c in vol_cols:
                empty_row[c] = 0.0
            df_out = pd.DataFrame([empty_row], columns=empty_cols)
        else:
            df_out = df
        df_out.to_csv(f, sep="\t", index=False)


if __name__ == "__main__":
    main()
