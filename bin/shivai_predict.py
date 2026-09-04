#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SHIVA-WMH lesion segmentation inference (Tsuchida et al., doi:10.1002/hbm.26548).

Model: v2/T1+FLAIR-WMH (github.com/pboutinaud/SHIVA_WMH).
Architecture: 5-fold TensorFlow SavedModel ResUnet3D ensemble.
Input tensor shape: (None, 160, 214, 176, 2) [T1w, FLAIR].
Output tensor shape: (None, 160, 214, 176, 1) [WMH probability].
Pipeline workflow: center-crop or pad to target shape, normalize intensities,
execute ensemble inference, and reconstruct output into original volume space.
"""

import argparse
from pathlib import Path
import numpy as np
import nibabel as nib
import tensorflow as tf
from _lesion_utils import filter_small_components

TARGET_SHAPE = (160, 214, 176)


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Real SHIVA-WMH (v2, T1+FLAIR) inference")
    parser.add_argument("--t1", required=True, help="Input T1w NIfTI image (already skull-stripped, MNI space)")
    parser.add_argument("--flair", required=True, help="Input FLAIR NIfTI image (already skull-stripped, MNI space)")
    parser.add_argument("--output", required=True, help="Output binary lesion mask NIfTI file")
    parser.add_argument(
        "--models_dir", default="/opt/shivai/T1.FLAIR-WMH",
        help="Directory containing the 5 fold_*.tf_inference SavedModel subdirectories"
    )
    parser.add_argument(
        "--prob_threshold", type=float, default=0.50,
        help="Threshold on the averaged fold probability map (default: 0.50, per upstream README)"
    )
    parser.add_argument(
        "--min_cluster_size", type=int, default=3,
        help="Minimum connected component size (default: 3), matching bawil_filter.py/mimosa_predict.R"
    )
    return parser


def center_crop_or_pad(volume, target_shape):
    """Center crop or zero-pad each volume axis to target_shape.

    Returns (result, dst_slices) where dst_slices defines coordinate
    ranges for output reconstruction.
    """
    result = np.zeros(target_shape, dtype=volume.dtype)
    src_slices = []
    dst_slices = []
    for src_dim, dst_dim in zip(volume.shape, target_shape):
        if src_dim >= dst_dim:
            start = (src_dim - dst_dim) // 2
            src_slices.append(slice(start, start + dst_dim))
            dst_slices.append(slice(0, dst_dim))
        else:
            start = (dst_dim - src_dim) // 2
            src_slices.append(slice(0, src_dim))
            dst_slices.append(slice(start, start + src_dim))
    result[tuple(dst_slices)] = volume[tuple(src_slices)]
    return result, dst_slices


def paste_back(cropped_volume, dst_slices, original_shape):
    """Reconstruct target_shape array into original volume dimensions."""
    result = np.zeros(original_shape, dtype=cropped_volume.dtype)
    src_slices = []
    out_slices = []
    for (dst_sl, orig_dim, crop_dim) in zip(dst_slices, original_shape, cropped_volume.shape):
        if orig_dim >= crop_dim:
            start = (orig_dim - crop_dim) // 2
            out_slices.append(slice(start, start + crop_dim))
            src_slices.append(slice(0, crop_dim))
        else:
            out_slices.append(slice(0, orig_dim))
            src_slices.append(dst_sl)
    result[tuple(out_slices)] = cropped_volume[tuple(src_slices)]
    return result


def minmax_normalize(volume):
    """Normalize nonzero brain voxel intensities to [0, 1] using 99th percentile."""
    brain_voxels = volume[volume > 0]
    if brain_voxels.size == 0:
        return np.zeros_like(volume, dtype=np.float32)
    p99 = np.percentile(brain_voxels, 99)
    if p99 <= 0:
        return np.zeros_like(volume, dtype=np.float32)
    normalized = np.clip(volume / p99, 0.0, 1.0)
    return normalized.astype(np.float32)


def main():
    args = build_arg_parser().parse_args()

    t1_img = nib.load(args.t1)
    flair_img = nib.load(args.flair)
    assert t1_img.shape == flair_img.shape, (
        f"T1 shape {t1_img.shape} != FLAIR shape {flair_img.shape}; "
        "both modalities must already be co-registered to the same grid."
    )
    affine = t1_img.affine
    header = t1_img.header
    original_shape = t1_img.shape

    t1_data = t1_img.get_fdata(dtype=np.float32)
    flair_data = flair_img.get_fdata(dtype=np.float32)

    t1_norm = minmax_normalize(t1_data)
    flair_norm = minmax_normalize(flair_data)

    t1_cropped, dst_slices = center_crop_or_pad(t1_norm, TARGET_SHAPE)
    flair_cropped, _ = center_crop_or_pad(flair_norm, TARGET_SHAPE)

    images = np.stack([t1_cropped, flair_cropped], axis=-1)  # (160, 214, 176, 2)
    batch = tf.constant(images[np.newaxis, ...], dtype=tf.float32)  # (1, 160, 214, 176, 2)

    def _is_fold_dir(p):
        # Verify valid SavedModel directory and handle filesystem permission errors.
        try:
            return p.is_dir() and (p / "saved_model.pb").exists()
        except OSError:
            return False

    fold_dirs = sorted(p for p in Path(args.models_dir).iterdir() if _is_fold_dir(p))
    if not fold_dirs:
        raise RuntimeError(f"No fold SavedModel directories found under {args.models_dir}")

    predictions = []
    for fold_dir in fold_dirs:
        model = tf.saved_model.load(str(fold_dir))
        pred = model.serve(batch).numpy()  # (1, 160, 214, 176, 1)
        predictions.append(pred)

    mean_prob = np.mean(predictions, axis=0)[0, ..., 0]  # (160, 214, 176)

    binary_cropped = (mean_prob >= args.prob_threshold).astype(np.uint8)
    if args.min_cluster_size > 1:
        binary_cropped = filter_small_components(binary_cropped, args.min_cluster_size)
    binary_native = paste_back(binary_cropped, dst_slices, original_shape)

    out_img = nib.Nifti1Image(binary_native, affine, header)
    out_img.set_data_dtype(np.uint8)
    nib.save(out_img, args.output)


if __name__ == "__main__":
    main()
