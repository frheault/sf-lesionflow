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


# Canonical per-process specs, mirroring conf/base.config's individual withName
# blocks directly (CPU-path values where a process has a separate GPU path).
# There is no generic tier here on purpose -- each entry reflects what that one
# tool actually needs, not a shared bucket. Keep this in sync with base.config.
PROCESS_SPECS = {
    'RESAMPLE_FLAIR': {'cpu': 1, 'ram': 4.0},
    'RESAMPLE_T1': {'cpu': 1, 'ram': 4.0},
    'SYNTHSTRIP_T1': {'cpu': 4, 'ram': 6.0},
    'SYNTHSTRIP_FLAIR': {'cpu': 4, 'ram': 6.0},
    'CROP_T1_MASK': {'cpu': 1, 'ram': 4.0},
    'CROP_T1_RAW': {'cpu': 1, 'ram': 4.0},
    'CROP_FLAIR_MASK': {'cpu': 1, 'ram': 4.0},
    'CROP_FLAIR_RAW': {'cpu': 1, 'ram': 4.0},
    'N4_T1': {'cpu': 4, 'ram': 8.0},
    'N4_FLAIR': {'cpu': 4, 'ram': 8.0},
    'MASK_FLAIR': {'cpu': 1, 'ram': 4.0},
    'MASK_T1': {'cpu': 1, 'ram': 4.0},
    'REGISTER_BASELINE_TO_MNI': {'cpu': 4, 'ram': 8.0},
    'REGISTER_FLAIR_TO_T1': {'cpu': 4, 'ram': 8.0},
    'REGISTER_T1_TO_BASELINE': {'cpu': 4, 'ram': 8.0},
    'TRANSFORM_FLAIR_UNSTRIPPED_TO_MNI': {'cpu': 1, 'ram': 4.0},
    'TRANSFORM_FLAIR_TO_MNI': {'cpu': 1, 'ram': 4.0},
    'TRANSFORM_T1W_UNSTRIPPED_TO_MNI': {'cpu': 1, 'ram': 4.0},
    'TRANSFORM_T1W_TO_MNI': {'cpu': 1, 'ram': 4.0},
    'SEGMENTATION_FLAMES': {'cpu': 4, 'ram': 16.0},
    'SEGMENTATION_SAMSEG': {'cpu': 8, 'ram': 20.0},
    'SEGMENTATION_WMH_SYNTHSEG': {'cpu': 1, 'ram': 24.0},
    'SEGMENTATION_SEGCSVD': {'cpu': 4, 'ram': 16.0},
    'SEGMENTATION_BAWIL': {'cpu': 4, 'ram': 10.0},
    'SEGMENTATION_SHIVAI': {'cpu': 4, 'ram': 10.0},
    'SEGMENTATION_EMORY_ROBUST': {'cpu': 4, 'ram': 16.0},
    'SEGMENTATION_LST_AI': {'cpu': 6, 'ram': 10.0},
    'SEGMENTATION_MIMOSA': {'cpu': 1, 'ram': 10.0},
    'SEGMENTATION_FAST_OUTLIER': {'cpu': 1, 'ram': 4.0},
    'SEGMENTATION_HYPERMAPP3R': {'cpu': 2, 'ram': 20.0},
    'SEGMENTATION_MARS_WMH': {'cpu': 4, 'ram': 16.0},
    'SEGMENTATION_TRUENET': {'cpu': 4, 'ram': 16.0},
    'CONSENSUS_STAPLE': {'cpu': 2, 'ram': 6.0},
    'HARMONIZATION_STAPLE': {'cpu': 2, 'ram': 6.0},
    'QC_ENSEMBLE_METRICS': {'cpu': 1, 'ram': 4.0},
    'QC_LONGITUDINAL': {'cpu': 1, 'ram': 4.0},
    'QC_REGISTRATION_FLAIR_T1': {'cpu': 1, 'ram': 4.0},
    'QC_REGISTRATION_T1_BASELINE': {'cpu': 1, 'ram': 4.0},
    'QC_REGISTRATION_BASELINE_MNI': {'cpu': 1, 'ram': 4.0},
    'QC_LESION_SCREENSHOT': {'cpu': 1, 'ram': 4.0},
    'MULTIQC_SUBJECT': {'cpu': 1, 'ram': 4.0},
    'MULTIQC_GLOBAL': {'cpu': 1, 'ram': 4.0},
}

# Fallback for any process not yet profiled/added above -- matches base.config's
# bare top-level default (1 cpu / 4GB), not a guessed "medium" bucket.
DEFAULT_SPEC = {'cpu': 1, 'ram': 4.0}


def analyze_trace(trace_file):
    df = pd.read_csv(trace_file, sep='\t')
    df['realtime_sec'] = df['realtime'].apply(parse_time)
    df['peak_rss_gb'] = df['peak_rss'].apply(parse_bytes_gb)
    df['cpu_pct'] = pd.to_numeric(df['%cpu'].astype(str).str.rstrip('%').replace('-', '0'), errors='coerce').fillna(0.0)

    rows = []
    for _, r in df.iterrows():
        task_name = r['name'].split(' ')[0]
        spec = PROCESS_SPECS.get(task_name, DEFAULT_SPEC)
        alloc_ram = spec['ram']
        alloc_cpu = spec['cpu']

        mem_eff = (r['peak_rss_gb'] / alloc_ram) * 100.0
        cpu_eff = (r['cpu_pct'] / (alloc_cpu * 100.0)) * 100.0

        # Classify process resource utilization against its OWN current allocation
        # (no tier names involved -- just this process's numbers vs. what it used).
        if alloc_ram >= 16.0 and r['peak_rss_gb'] < 2.0:
            category = "Phantom High-Memory"
            rec_cpu = 1 if r['cpu_pct'] < 150 else 2
            rec_ram = "2.GB" if r['cpu_pct'] < 150 else "4.GB"
        elif alloc_cpu >= 4 and r['cpu_pct'] <= 120 and r['realtime_sec'] > 30:
            category = "Pseudo Multi-Threaded"
            rec_cpu = 1
            rec_ram = f"{max(4, int(r['peak_rss_gb'] * 1.25) + 1)}.GB"
        elif r['peak_rss_gb'] >= 10.0:
            category = "True Memory Monopoly"
            rec_cpu = alloc_cpu
            rec_ram = "16.GB"
        elif r['cpu_pct'] > 250 and r['peak_rss_gb'] <= 4.0:
            category = "High-Compute Hotspot"
            rec_cpu = 4
            rec_ram = "4.GB"
        elif r['realtime_sec'] < 10.0:
            category = "Fast Heuristic / Filter"
            rec_cpu = 1
            rec_ram = "2.GB"
        elif r['peak_rss_gb'] <= 8.0 and alloc_ram >= 16.0:
            category = "Over-Allocated RAM"
            rec_cpu = 4
            rec_ram = "8.GB"
        else:
            category = "Balanced"
            rec_cpu = alloc_cpu
            rec_ram = f"{int(alloc_ram)}.GB"

        rows.append({
            'Task': task_name,
            'Alloc CPU': alloc_cpu,
            'Alloc RAM': f"{alloc_ram:.0f} GB",
            'Realtime': r['realtime'],
            '% CPU': f"{r['cpu_pct']:.1f}%",
            'Peak RSS': f"{r['peak_rss_gb']:.2f} GB",
            'Mem Eff': f"{mem_eff:.1f}%",
            'CPU Eff': f"{cpu_eff:.1f}%",
            'Diagnostic Bucket': category,
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
