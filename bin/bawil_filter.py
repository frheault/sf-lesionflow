#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BAWIL lesion segmentation inference (Bashiri Bawil et al., arXiv:2506.07123).

Model: Hugging Face `Bawil/wmh_leverage_normal_abnormal_segmentation`,
`unet/models/scenario2_multiclass_model.h5`.
Architecture: Keras U-Net with 3-class softmax output
(background, normal periventricular hyperintensity, abnormal WMH).
Input: 256x256 axial FLAIR slices with per-slice z-score normalization.
"""

import argparse
import numpy as np
import nibabel as nib
import cv2 as cv
from tensorflow import keras
from _lesion_utils import filter_small_components


def build_arg_parser():
    parser = argparse.ArgumentParser(description="BAWIL real inference (3-class U-Net)")
    parser.add_argument("--flair", required=True, help="Input FLAIR NIfTI image")
    parser.add_argument("--output", required=True, help="Output binary lesion mask NIfTI file")
    parser.add_argument(
        "--model", default="/opt/bawil/scenario2_multiclass_model.h5",
        help="Path to the Keras .h5 model (baked into the image at build time)"
    )
    parser.add_argument(
        "--prob_threshold", type=float, default=0.50,
        help="Threshold on the class-2 (abnormal WMH) softmax probability (default: 0.50)"
    )
    parser.add_argument(
        "--min_cluster_size", type=int, default=3,
        help="Minimum connected component size (default: 3)"
    )
    return parser


def main():
    args = build_arg_parser().parse_args()

    # Reorient volume to canonical RAS orientation (axis 2 = axial).
    img = nib.as_closest_canonical(nib.load(args.flair))
    data = img.get_fdata().astype(np.float32)
    affine = img.affine
    header = img.header
    native_shape = data.shape[:2]

    model = keras.models.load_model(args.model, compile=False)

    abnormal_prob = np.zeros(data.shape, dtype=np.float32)

    for z in range(data.shape[2]):
        sl = data[:, :, z]
        if np.max(sl) <= 0:
            continue

        sl_resized = cv.resize(sl, (256, 256))
        mean = np.mean(sl_resized)
        std = np.std(sl_resized)
        if std < 1e-7:
            continue
        sl_norm = (sl_resized - mean) / (std + 1e-7)

        pred = model.predict(sl_norm[np.newaxis, ..., np.newaxis], verbose=0)[0]
        prob2 = pred[..., 2]  # class 2 = abnormal WMH

        # Resize continuous probability map to native in-plane resolution.
        prob2_native = cv.resize(prob2, (native_shape[1], native_shape[0]))
        abnormal_prob[:, :, z] = prob2_native

    binary = (abnormal_prob >= args.prob_threshold).astype(np.uint8)
    if args.min_cluster_size > 1:
        binary = filter_small_components(binary, args.min_cluster_size)

    out_img = nib.Nifti1Image(binary, affine, header)
    out_img.set_data_dtype(np.uint8)
    nib.save(out_img, args.output)


if __name__ == "__main__":
    main()
