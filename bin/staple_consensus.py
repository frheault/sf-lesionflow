#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import numpy as np
import SimpleITK as sitk
from _lesion_utils import filter_small_components, watershed_instances

def build_arg_parser():
    parser = argparse.ArgumentParser(description="STAPLE Consensus Fusion with Size Filter and Marker-Controlled Watershed")
    parser.add_argument("--ref_image", required=True, help="Reference NIfTI image for geometry/header copying")
    parser.add_argument("--masks", nargs="+", required=True, help="List of binary segmentation mask NIfTI files")
    parser.add_argument("--out_probmap", required=True, help="Output continuous STAPLE probability map NIfTI file")
    parser.add_argument("--out_binary", required=True, help="Output thresholded binary mask NIfTI file")
    parser.add_argument("--out_labels", required=True, help="Output watershed instance labels uint16 NIfTI file")
    parser.add_argument("--threshold", type=float, default=0.90, help="Probability threshold (default: 0.90)")
    parser.add_argument("--min_cluster_size", type=int, default=6, help="Minimum connected component size in voxels/mm3 (default: 6)")
    parser.add_argument("--min_distance", type=int, default=3, help="Minimum distance between watershed peaks (default: 3)")
    parser.add_argument("--gaussian_sigma", type=float, default=0.8, help="Gaussian smoothing sigma for distance transform (default: 0.8)")
    return parser

def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    ref_sitk = sitk.ReadImage(args.ref_image)
    mask_files = sorted(args.masks)

    aligned_masks = []
    for m in mask_files:
        img = sitk.ReadImage(m, sitk.sitkUInt8)
        if img.GetSize() != ref_sitk.GetSize() or img.GetSpacing() != ref_sitk.GetSpacing():
            res = sitk.ResampleImageFilter()
            res.SetReferenceImage(ref_sitk)
            res.SetInterpolator(sitk.sitkNearestNeighbor)
            img = res.Execute(img)
        aligned_masks.append(img)

    has_any_lesion = any(np.any(sitk.GetArrayViewFromImage(img) > 0) for img in aligned_masks)
    if not has_any_lesion:
        ref_size = ref_sitk.GetSize()
        empty_float = sitk.Image(ref_size, sitk.sitkFloat32)
        empty_float.CopyInformation(ref_sitk)
        sitk.WriteImage(empty_float, args.out_probmap)

        empty_uint8 = sitk.Image(ref_size, sitk.sitkUInt8)
        empty_uint8.CopyInformation(ref_sitk)
        sitk.WriteImage(empty_uint8, args.out_binary)

        empty_uint16 = sitk.Image(ref_size, sitk.sitkUInt16)
        empty_uint16.CopyInformation(ref_sitk)
        sitk.WriteImage(empty_uint16, args.out_labels)
        return

    staple = sitk.STAPLEImageFilter()
    staple_prob = staple.Execute(aligned_masks)
    sitk.WriteImage(staple_prob, args.out_probmap)

    thr_raw = sitk.BinaryThreshold(staple_prob, lowerThreshold=args.threshold, upperThreshold=1.0, insideValue=1, outsideValue=0)
    arr = sitk.GetArrayFromImage(thr_raw) > 0

    arr = filter_small_components(arr, args.min_cluster_size)

    thr_sitk = sitk.GetImageFromArray(arr.astype(np.uint8))
    thr_sitk.CopyInformation(ref_sitk)
    sitk.WriteImage(thr_sitk, args.out_binary)

    ws_labels = watershed_instances(arr, min_distance=args.min_distance, gaussian_sigma=args.gaussian_sigma)

    ws_sitk = sitk.GetImageFromArray(ws_labels)
    ws_sitk.CopyInformation(ref_sitk)
    sitk.WriteImage(ws_sitk, args.out_labels)

if __name__ == "__main__":
    main()
