#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nextflow trace resource profiling and allocation analysis.

Analyzes execution time, CPU utilization, and peak memory usage from
trace logs to recommend process resource allocation tiers.
"""

import sys
import os
import glob
import argparse
import pandas as pd


def parse_time(t_str):
    if not isinstance(t_str, str):
        return 0.0
    t_str = t_str.strip()
    if t_str.endswith('ms'):
        return float(t_str[:-2].strip()) / 1000.0
    total = 0.0
    if 'm' in t_str and 's' in t_str:
        parts = t_str.split('m')
        total += float(parts[0].strip()) * 60
        s_part = parts[1].replace('s', '').strip()
        if s_part:
            total += float(s_part)
    elif 's' in t_str:
        total += float(t_str.replace('s', '').strip())
    return total


def parse_bytes_gb(b_str):
    if not isinstance(b_str, str):
        return 0.0
    b_str = b_str.strip()
    units = {'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4, 'B': 1}
    for u, mult in units.items():
        if b_str.endswith(u):
            val = float(b_str[:-len(u)].strip())
            return (val * mult) / (1024**3)  # GB
    return 0.0


# Canonical label specifications from conf/base.config and conf/local_dev.config.
TIER_SPECS = {
    'process_single': {'cpu': 1, 'base_ram': 4.0, 'dev_ram': 4.0},
    'process_low': {'cpu': 2, 'base_ram': 8.0, 'dev_ram': 6.0},
    'process_medium': {'cpu': 4, 'base_ram': 12.0, 'dev_ram': 8.0},
    'process_high': {'cpu': 8, 'base_ram': 16.0, 'dev_ram': 10.0},
    'process_high_memory': {'cpu': 4, 'base_ram': 24.0, 'dev_ram': 16.0}
}

CURRENT_LABELS = {
    'RESAMPLE_FLAIR': 'process_high_memory',
    'RESAMPLE_T1': 'process_high_memory',
    'SYNTHSTRIP_T1': 'process_single',
    'SYNTHSTRIP_FLAIR': 'process_single',
    'CROP_T1_MASK': 'process_single',
    'CROP_T1_RAW': 'process_single',
    'CROP_FLAIR_MASK': 'process_single',
    'CROP_FLAIR_RAW': 'process_single',
    'N4_T1': 'process_high_memory',
    'N4_FLAIR': 'process_high_memory',
    'MASK_FLAIR': 'process_single',
    'MASK_T1': 'process_single',
    'REGISTER_BASELINE_TO_MNI': 'process_medium',
    'REGISTER_FLAIR_TO_T1': 'process_medium',
    'TRANSFORM_FLAIR_UNSTRIPPED_TO_MNI': 'process_low',
    'TRANSFORM_FLAIR_TO_MNI': 'process_low',
    'TRANSFORM_T1W_UNSTRIPPED_TO_MNI': 'process_low',
    'TRANSFORM_T1W_TO_MNI': 'process_low',
    'SEGMENTATION_FLAMES': 'process_medium',
    'SEGMENTATION_SAMSEG': 'process_high_memory',
    'SEGMENTATION_WMH_SYNTHSEG': 'process_high_memory',
    'SEGMENTATION_SEGCSVD': 'process_medium',
    'SEGMENTATION_BAWIL': 'process_medium',
    'SEGMENTATION_SHIVAI': 'process_medium',
    'SEGMENTATION_EMORY_ROBUST': 'process_high_memory',
    'SEGMENTATION_LST_AI': 'process_medium',
    'SEGMENTATION_MIMOSA': 'process_medium',
    'SEGMENTATION_FAST_OUTLIER': 'process_single',
    'SEGMENTATION_HYPERMAPP3R': 'process_high_memory',
    'SEGMENTATION_MARS_WMH': 'process_medium',
    'SEGMENTATION_TRUENET': 'process_medium',
    'CONSENSUS_STAPLE': 'process_single',
    'HARMONIZATION_STAPLE': 'process_medium'
}


def analyze_trace(trace_file):
    df = pd.read_csv(trace_file, sep='\t')
    df['realtime_sec'] = df['realtime'].apply(parse_time)
    df['peak_rss_gb'] = df['peak_rss'].apply(parse_bytes_gb)
    df['cpu_pct'] = df['%cpu'].str.rstrip('%').astype(float)

    rows = []
    for _, r in df.iterrows():
        task_name = r['name'].split(' ')[0]
        label = CURRENT_LABELS.get(task_name, 'process_medium')
        spec = TIER_SPECS.get(label, {'cpu': 1, 'base_ram': 4.0, 'dev_ram': 4.0})
        alloc_ram = spec['dev_ram']
        alloc_cpu = spec['cpu']

        mem_eff = (r['peak_rss_gb'] / alloc_ram) * 100.0
        cpu_eff = (r['cpu_pct'] / (alloc_cpu * 100.0)) * 100.0

        # Classify process resource utilization.
        if label == 'process_high_memory' and r['peak_rss_gb'] < 2.0:
            category = "Phantom High-Memory"
            rec_label = "process_single" if r['cpu_pct'] < 150 else "process_low"
            rec_cpu = 1 if r['cpu_pct'] < 150 else 2
            rec_ram = "2.GB" if r['cpu_pct'] < 150 else "4.GB"
        elif alloc_cpu >= 4 and r['cpu_pct'] <= 120 and r['realtime_sec'] > 30:
            category = "Pseudo Multi-Threaded"
            rec_label = "process_single"
            rec_cpu = 1
            rec_ram = f"{max(4, int(r['peak_rss_gb'] * 1.25) + 1)}.GB"
        elif r['peak_rss_gb'] >= 10.0:
            category = "True Memory Monopoly"
            rec_label = "process_high_memory"
            rec_cpu = alloc_cpu
            rec_ram = "16.GB"
        elif r['cpu_pct'] > 250 and r['peak_rss_gb'] <= 4.0:
            category = "High-Compute Hotspot"
            rec_label = "process_medium"
            rec_cpu = 4
            rec_ram = "4.GB"
        elif r['realtime_sec'] < 10.0:
            category = "Fast Heuristic / Filter"
            rec_label = "process_single"
            rec_cpu = 1
            rec_ram = "2.GB"
        elif r['peak_rss_gb'] <= 8.0 and label == 'process_high_memory':
            category = "Over-Allocated RAM"
            rec_label = "process_medium"
            rec_cpu = 4
            rec_ram = "8.GB"
        else:
            category = "Balanced"
            rec_label = label
            rec_cpu = alloc_cpu
            rec_ram = f"{int(alloc_ram)}.GB"

        rows.append({
            'Task': task_name,
            'Current Label': label,
            'Alloc CPU': alloc_cpu,
            'Alloc RAM': f"{alloc_ram:.0f} GB",
            'Realtime': r['realtime'],
            '% CPU': f"{r['cpu_pct']:.1f}%",
            'Peak RSS': f"{r['peak_rss_gb']:.2f} GB",
            'Mem Eff': f"{mem_eff:.1f}%",
            'CPU Eff': f"{cpu_eff:.1f}%",
            'Diagnostic Bucket': category,
            'Recommended Tier': rec_label,
            'Rec CPU': rec_cpu,
            'Rec RAM': rec_ram
        })

    return pd.DataFrame(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Profile Nextflow resources & classify misattributions.")
    parser.add_argument('trace_file', nargs='?', help="Path to Nextflow trace.txt file")
    args = parser.parse_args()

    t_file = args.trace_file
    if not t_file:
        trace_files = sorted(glob.glob('trace*.txt'), key=os.path.getmtime)
        if not trace_files:
            sys.exit("Error: No trace*.txt files found in current directory.")
        t_file = trace_files[-1]

    print(f"Analyzing telemetry from: {t_file}\n")
    res = analyze_trace(t_file)
    print(res.to_markdown(index=False))
