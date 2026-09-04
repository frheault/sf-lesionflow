#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared image processing utilities for lesion segmentation and consensus fusion.

Provides connected-component filtering and marker-controlled watershed
instance segmentation algorithms.
"""

import numpy as np
import scipy.ndimage as ndi
from skimage.feature import peak_local_max
from skimage.segmentation import watershed


def filter_small_components(binary_mask, min_size):
    """Filter connected components smaller than min_size voxels from binary mask."""
    labeled, n_features = ndi.label(binary_mask)
    if n_features > 0:
        counts = np.bincount(labeled.ravel())
        binary_mask = binary_mask.copy()
        binary_mask[(counts < min_size)[labeled]] = 0
    return binary_mask


def watershed_instances(binary_mask, min_distance=3, gaussian_sigma=0.8):
    """Label distinct lesion instances using marker-controlled watershed segmentation."""
    if not np.any(binary_mask):
        return np.zeros(binary_mask.shape, dtype=np.uint16)

    dist = ndi.distance_transform_edt(binary_mask)
    dist_sm = ndi.gaussian_filter(dist, sigma=gaussian_sigma)
    coords = peak_local_max(dist_sm, min_distance=min_distance, labels=binary_mask)

    if len(coords) == 0:
        labeled, _ = ndi.label(binary_mask)
        return labeled.astype(np.uint16)

    markers_mask = np.zeros(dist.shape, dtype=bool)
    markers_mask[tuple(coords.T)] = True
    markers, _ = ndi.label(markers_mask)
    return watershed(-dist_sm, markers, mask=binary_mask).astype(np.uint16)
