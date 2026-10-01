#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compute registration quality metrics and generate visual checkerboard overlays.

Metrics are computed from the images themselves (fixed vs moving-warped, in the fixed
space, inside the fixed image's foreground), so no ANTs log is required:
  NCC        Pearson correlation of intensities
  NMI        normalized mutual information (Studholme, 64 bins)
  Mask_Dice  Dice of the two foregrounds (brain envelope overlap)
  Affine_Scale_Factor  volume scaling moving -> fixed of the forward transform (--transform):
             1/|det A| (ANTs/ITK forward transforms map FIXED-space points to MOVING space);
             1.0 for rigid stages, >1 when the MNI template is larger than the subject's head
The ANTs final metric is added as an extra column when --log is given.
"""

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


# Initial PASS/WARN thresholds per stage (None = not checked). Set from the first 2-subject run
# (visually good registrations: FLAIR->T1 NCC 0.08-0.27 / NMI 1.06-1.09 -- NCC is meaningless
# across contrasts; T1->baseline NCC 0.98 / NMI 1.29-1.34; T1->MNI template NCC 0.58-0.60 /
# NMI 1.03-1.04 against the smooth template). Tune on a larger cohort.
THRESHOLDS = {
    "flair_to_t1": {"NCC": None, "NMI": 1.03, "Mask_Dice": 0.90},
    "t1_to_baseline": {"NCC": 0.90, "NMI": 1.15, "Mask_Dice": 0.95},
    "baseline_to_mni": {"NCC": 0.45, "NMI": 1.02, "Mask_Dice": 0.90},
}
SCALE_RANGE = (0.7, 1.9)


def _as_3d(data):
    data = np.squeeze(np.nan_to_num(np.asarray(data, dtype=np.float64)))
    while data.ndim < 3:
        data = np.expand_dims(data, axis=-1)
    if data.ndim > 3:
        data = data[..., 0]
    return data


def ncc(a, b, mask):
    """Pearson correlation of a and b inside mask."""
    x, y = a[mask], b[mask]
    if x.size < 2 or x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def nmi(a, b, mask, bins=64):
    """Studholme normalized mutual information (H(A)+H(B))/H(A,B) inside mask; 1 = independent, 2 = identical."""
    x, y = a[mask], b[mask]
    if x.size < 2:
        return float("nan")
    hist, _, _ = np.histogram2d(x, y, bins=bins)
    pxy = hist / hist.sum()
    px, py = pxy.sum(axis=1), pxy.sum(axis=0)

    def entropy(p):
        p = p[p > 0]
        return float(-(p * np.log(p)).sum())

    hxy = entropy(pxy.ravel())
    return float((entropy(px) + entropy(py)) / hxy) if hxy > 0 else float("nan")


def mask_dice(a, b):
    total = a.sum() + b.sum()
    return float(2.0 * np.logical_and(a, b).sum() / total) if total else float("nan")


def affine_scale_factor(mat_file):
    """Volume scaling moving -> fixed of an ITK/ANTs forward affine .mat (AffineTransform_*_3_3).

    ITK transforms map FIXED-space points to MOVING space (resampling convention), so a moving
    image is scaled by 1/|det A| when warped into the fixed space.
    """
    if not mat_file or not os.path.isfile(mat_file):
        return None
    from scipy.io import loadmat

    mat = loadmat(mat_file)
    key = next((k for k in mat if k.startswith("AffineTransform_") or k.startswith("MatrixOffsetTransformBase_")), None)
    if key is None:
        return None
    params = np.asarray(mat[key]).ravel()
    if params.size < 9:
        return None
    det = abs(np.linalg.det(params[:9].reshape(3, 3)))
    return float(1.0 / det) if det > 0 else None


def foreground(data):
    """Foreground mask: non-zero voxels, or above 10% of the 99th percentile for unmasked images."""
    nz = data > 0
    if nz.mean() > 0.9:  # image has no zero background (unstripped/noisy)
        thr = 0.1 * np.percentile(data, 99)
        return data > thr
    return nz


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
    parser.add_argument("--log", required=False, help="ANTs registration stdout/log file (optional extra column)")
    parser.add_argument("--transform", required=False, help="Forward affine .mat of this stage (for Affine_Scale_Factor)")
    parser.add_argument("--out_metrics", required=True, help="Output registration metrics TSV")
    parser.add_argument("--out_png", required=True, help="Output checkerboard screenshot PNG")
    args = parser.parse_args()

    fixed_nii = nib.as_closest_canonical(nib.load(args.fixed))
    warped_nii = nib.as_closest_canonical(nib.load(args.moving_warped))
    f_raw = _as_3d(fixed_nii.get_fdata())
    w_raw = _as_3d(warped_nii.get_fdata())

    # 1. Image-based similarity metrics (only meaningful on a shared grid)
    if f_raw.shape == w_raw.shape:
        f_fg, w_fg = foreground(f_raw), foreground(w_raw)
        m_ncc, m_nmi, m_dice = ncc(f_raw, w_raw, f_fg), nmi(f_raw, w_raw, f_fg), mask_dice(f_fg, w_fg)
    else:
        m_ncc = m_nmi = m_dice = float("nan")
    scale = affine_scale_factor(args.transform)
    ants_metric = parse_ants_metric(args.log)

    thr = THRESHOLDS[args.stage]
    problems = [k for k, v in (("NCC", m_ncc), ("NMI", m_nmi), ("Mask_Dice", m_dice))
                if thr[k] is not None and not (v >= thr[k])]
    if scale is not None:
        if args.stage == "baseline_to_mni" and not (SCALE_RANGE[0] <= scale <= SCALE_RANGE[1]):
            problems.append("Affine_Scale_Factor")
        if args.stage != "baseline_to_mni" and abs(scale - 1.0) > 1e-3:
            problems.append("Affine_Scale_Factor(rigid!=1)")
    status = "PASS" if not problems else "WARN(" + ",".join(problems) + ")"

    def fmt(v, nd=4):
        return "N/A" if v is None or not np.isfinite(v) else f"{v:.{nd}f}"

    sample_id = f"{args.meta_id}_{args.stage}"
    with open(args.out_metrics, "w") as f:
        f.write("# id: 'registration_metrics'\n")
        f.write("# section_name: 'Spatial Registration Performance'\n")
        f.write("# description: 'Image-based similarity between the fixed image and the warped moving image "
                "(inside the fixed foreground). Affine_Scale_Factor is the volume scaling of the transform: "
                "MNI-normalized volume = native volume x Affine_Scale_Factor.'\n")
        f.write("# plot_type: 'table'\n")
        cols = ["Sample", "Stage", "NCC", "NMI", "Mask_Dice", "Affine_Scale_Factor", "Status"]
        vals = [sample_id, args.stage, fmt(m_ncc), fmt(m_nmi), fmt(m_dice), fmt(scale), status]
        if ants_metric is not None:
            cols.append("ANTs_Final_Metric")
            vals.append(fmt(ants_metric))
        f.write("\t".join(cols) + "\n")
        f.write("\t".join(vals) + "\n")

    # 2. Generate Triplanar Checkerboard Overlay
    f_data, w_data = f_raw, w_raw
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
