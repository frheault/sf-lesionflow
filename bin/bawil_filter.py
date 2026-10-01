#!/usr/bin/env python3
"""BAWIL lesion segmentation inference (Bashiri Bawil et al., Biomedical Engineering Online 2026, PMC13202883).

Model: Hugging Face `Bawil/wmh_leverage_normal_abnormal_segmentation`,
`unet/models/scenario2_multiclass_model.h5` -- a 2D Keras U-Net with a 3-class softmax
(0: background, 1: normal periventricular hyperintensity, 2: abnormal WMH).

The upstream training data (github.com/Mahdi-Bashiri/wmh-normal-abnormal-segmentation,
data/train/*.png) are whole-head, unstripped 1.5 T clinical axial FLAIR slices, anterior at
the top of the image, per-slice z-scored over the whole frame; training used no rotation/flip
augmentation, and inference takes argmax == 2. Per axial slice this script:

  1. reorients to RAS and rotates the slice to the training display orientation
     (--orientation, one of the 8 in-plane dihedral variants; rot90 = anterior at the top);
  2. frames it: --framing brainbox (default) crops the brain mask's bounding box (in-plane
     and in z) and resizes it to 256x256; --framing head uses a square head-centred window
     where the head fills --fov_fill of the frame (isotropic scaling);
  3. optionally zeroes everything outside the brain (--strip) and averages neighbouring
     slices (--slab_mm, thick-slice emulation);
  4. z-scores the 256x256 frame and predicts the three class probabilities;
  5. maps them back to the native grid, decides per voxel (--decision argmax: class 2 wins;
     or threshold on p(class 2)), applies the upstream 2D post-processing (objects < 5 px
     removed, 3x3 opening), then drops 3D components smaller than --min_cluster_size.

Pipeline defaults (brainbox + rot90 + --strip + argmax) come from the calibration experiment
documented in dockerfiles/bawil/README.md.

The probability map written is p(class 2). Output grid and orientation are those of the input.
"""

import argparse

import nibabel as nib
import numpy as np
import scipy.ndimage as ndi

ORIENTATIONS = ("none", "rot90", "rot180", "rot270", "flip", "rot90_flip", "rot180_flip", "rot270_flip")
NET_SIZE = 256


def build_arg_parser():
    parser = argparse.ArgumentParser(description="BAWIL inference (3-class 2D U-Net)")
    parser.add_argument("--flair", required=True, help="Input FLAIR NIfTI (full FOV, unstripped)")
    parser.add_argument("--brainmask", default=None, help="Brain mask on the FLAIR grid (optional, centring only)")
    parser.add_argument("--output", required=True, help="Output binary lesion mask NIfTI file")
    parser.add_argument("--output_prob", default=None, help="Optional: continuous p(class 2) map")
    parser.add_argument("--model", default="/opt/bawil/scenario2_multiclass_model.h5", help="Keras .h5 model")
    parser.add_argument("--orientation", default="rot90", choices=ORIENTATIONS,
                        help="In-plane transform from a RAS axial slice to the network frame (default: rot90 = "
                             "anterior at the top)")
    parser.add_argument("--fov_fill", type=float, default=0.92,
                        help="Fraction of the frame covered by the head's larger in-plane extent (default: 0.92)")
    parser.add_argument("--framing", default="brainbox", choices=("head", "brainbox"),
                        help="head: square head-centred window (--fov_fill); brainbox: the brain mask's in-plane "
                             "bounding box stretched to 256x256 (pre-2026-09-30 behaviour)")
    parser.add_argument("--strip", action="store_true", help="Zero the input outside the brain mask")
    parser.add_argument("--slab_mm", type=float, default=0.0,
                        help="Average this many mm of neighbouring slices before inference (0 = off)")
    parser.add_argument("--decision", default="argmax", choices=("argmax", "threshold"),
                        help="argmax: class 2 wins (upstream rule); threshold: p(class 2) >= --prob_threshold")
    parser.add_argument("--prob_threshold", type=float, default=0.50, help="Threshold for --decision threshold")
    parser.add_argument("--min_cluster_size", type=int, default=3, help="Minimum 3D component size in voxels")
    parser.add_argument("--batch_size", type=int, default=8, help="Slices per model.predict batch")
    return parser


# ── geometry (pure numpy; unit-tested in tests/test_bawil_geometry.py) ────────────────────────
def orient_forward(sl, orientation):
    """RAS axial slice (rows = x, cols = y) -> network frame."""
    name = orientation.replace("_flip", "")
    k = {"none": 0, "rot90": 1, "rot180": 2, "rot270": 3, "flip": 0}[name]
    out = np.rot90(sl, k)
    if orientation.endswith("flip"):
        out = np.fliplr(out)
    return out


def orient_inverse(sl, orientation):
    """Network frame -> RAS axial slice (exact inverse of orient_forward)."""
    name = orientation.replace("_flip", "")
    k = {"none": 0, "rot90": 1, "rot180": 2, "rot270": 3, "flip": 0}[name]
    out = np.fliplr(sl) if orientation.endswith("flip") else sl
    return np.rot90(out, -k)


def head_mask(vol):
    """Head (not brain) mask: Otsu threshold, largest 3D component, per-slice hole filling."""
    from skimage.filters import threshold_otsu

    vals = vol[np.isfinite(vol)]
    thr = threshold_otsu(vals[vals > 0]) if np.any(vals > 0) else 0.0
    mask = vol > thr * 0.5
    labeled, n = ndi.label(mask)
    if n > 1:
        counts = np.bincount(labeled.ravel())
        counts[0] = 0
        mask = labeled == np.argmax(counts)
    for z in range(mask.shape[2]):
        mask[:, :, z] = ndi.binary_fill_holes(mask[:, :, z])
    return mask


def square_window(mask2d_union, fov_fill):
    """Square window (x0, y0, side) centred on the head's in-plane bounding box, such that the
    larger in-plane head extent covers `fov_fill` of the side."""
    xs = np.where(mask2d_union.any(axis=1))[0]
    ys = np.where(mask2d_union.any(axis=0))[0]
    if xs.size == 0:
        side = max(mask2d_union.shape)
        return (mask2d_union.shape[0] - side) // 2, (mask2d_union.shape[1] - side) // 2, side
    ext = max(xs[-1] - xs[0] + 1, ys[-1] - ys[0] + 1)
    side = int(np.ceil(ext / fov_fill))
    cx = (xs[0] + xs[-1] + 1) / 2.0
    cy = (ys[0] + ys[-1] + 1) / 2.0
    return int(round(cx - side / 2.0)), int(round(cy - side / 2.0)), side


def extract_window(sl, x0, y0, side, fill_value):
    """Crop sl[x0:x0+side, y0:y0+side], padding out-of-bounds with fill_value."""
    out = np.full((side, side), fill_value, dtype=np.float32)
    sx0, sy0 = max(x0, 0), max(y0, 0)
    sx1, sy1 = min(x0 + side, sl.shape[0]), min(y0 + side, sl.shape[1])
    if sx1 > sx0 and sy1 > sy0:
        out[sx0 - x0:sx1 - x0, sy0 - y0:sy1 - y0] = sl[sx0:sx1, sy0:sy1]
    return out


def paste_window(win, shape, x0, y0):
    """Inverse of extract_window for a (side, side[, C]) array -> array of `shape` (zeros outside)."""
    side = win.shape[0]
    out = np.zeros(shape + win.shape[2:], dtype=win.dtype)
    sx0, sy0 = max(x0, 0), max(y0, 0)
    sx1, sy1 = min(x0 + side, shape[0]), min(y0 + side, shape[1])
    if sx1 > sx0 and sy1 > sy0:
        out[sx0:sx1, sy0:sy1] = win[sx0 - x0:sx1 - x0, sy0 - y0:sy1 - y0]
    return out


def to_network(win, orientation):
    import cv2 as cv

    frame = orient_forward(win, orientation).astype(np.float32)
    frame = cv.resize(frame, (NET_SIZE, NET_SIZE), interpolation=cv.INTER_LINEAR)
    return (frame - frame.mean()) / (frame.std() + 1e-7)  # upstream per-slice z-score, whole frame


def from_network(pred, side, orientation):
    """(256, 256, C) network output -> (side, side, C) window in RAS slice layout."""
    import cv2 as cv

    chans = [cv.resize(pred[..., c], (side, side), interpolation=cv.INTER_LINEAR) for c in range(pred.shape[-1])]
    return np.stack([orient_inverse(c, orientation) for c in chans], axis=-1)


def slab_average(vol, z, n):
    if n <= 1:
        return vol[:, :, z]
    lo, hi = max(0, z - n // 2), min(vol.shape[2], z + n // 2 + 1)
    return vol[:, :, lo:hi].mean(axis=2)


# ── inference ──────────────────────────────────────────────────────────────────────────────────
def brainbox_window(brain):
    """(x0, x1, y0, y1, z0, z1) bounding box of the brain mask."""
    xs, ys, zs = (np.where(brain.any(axis=a))[0] for a in ((1, 2), (0, 2), (0, 1)))
    return xs[0], xs[-1] + 1, ys[0], ys[-1] + 1, zs[0], zs[-1] + 1


def predict_volume(model, vol, zooms, orientation="rot90", fov_fill=0.92, slab_mm=0.0, batch_size=8,
                   hmask=None, min_head_frac=0.05, framing="head", brain=None):
    """Return (X, Y, Z, 3) class probabilities for a RAS volume.

    framing="head": square head-centred window, isotropic resize (training-like framing).
    framing="brainbox": brain bounding box (in-plane and in z), stretched to 256x256.
    """
    import cv2 as cv

    hmask = head_mask(vol) if hmask is None else hmask
    n_slab = int(round(slab_mm / float(zooms[2]))) if slab_mm > 0 else 1
    probs = np.zeros(vol.shape + (3,), dtype=np.float32)
    probs[..., 0] = 1.0

    if framing == "brainbox":
        if brain is None or not brain.any():
            raise ValueError("framing='brainbox' needs a non-empty brain mask")
        x0, x1, y0, y1, z0, z1 = brainbox_window(brain)
        todo = list(range(z0, z1))
        for i in range(0, len(todo), batch_size):
            zs = todo[i:i + batch_size]
            frames = []
            for z in zs:
                sl = orient_forward(slab_average(vol, z, n_slab)[x0:x1, y0:y1], orientation).astype(np.float32)
                sl = cv.resize(sl, (NET_SIZE, NET_SIZE), interpolation=cv.INTER_LINEAR)
                frames.append((sl - sl.mean()) / (sl.std() + 1e-7))
            preds = model.predict(np.stack(frames)[..., np.newaxis], verbose=0)
            for z, pred in zip(zs, preds):
                h, w = orient_forward(np.zeros((x1 - x0, y1 - y0)), orientation).shape
                chans = [orient_inverse(cv.resize(pred[..., c], (w, h), interpolation=cv.INTER_LINEAR), orientation)
                         for c in range(3)]
                probs[x0:x1, y0:y1, z] = np.stack(chans, axis=-1)
        return probs

    x0, y0, side = square_window(hmask.any(axis=2), fov_fill)
    background = float(np.median(vol[~hmask])) if np.any(~hmask) else 0.0
    todo = [z for z in range(vol.shape[2]) if hmask[:, :, z].sum() >= min_head_frac * side * side]
    for i in range(0, len(todo), batch_size):
        zs = todo[i:i + batch_size]
        batch = np.stack([
            to_network(extract_window(slab_average(vol, z, n_slab), x0, y0, side, background), orientation)
            for z in zs
        ])[..., np.newaxis]
        preds = model.predict(batch, verbose=0)
        for z, pred in zip(zs, preds):
            win = from_network(pred.astype(np.float32), side, orientation)
            full = paste_window(win, vol.shape[:2], x0, y0)
            outside = paste_window(np.ones((side, side), np.float32), vol.shape[:2], x0, y0) == 0
            full[outside] = (1.0, 0.0, 0.0)
            probs[:, :, z] = full
    return probs


def decide(probs, decision="argmax", prob_threshold=0.5, min_cluster_size=3):
    from _lesion_utils import filter_small_components

    if decision == "argmax":
        binary = np.argmax(probs, axis=-1) == 2
    else:
        binary = probs[..., 2] >= prob_threshold
    # Upstream 2D post-processing (per slice): drop objects < 5 px, then a 3x3 opening.
    struct = np.ones((3, 3), dtype=bool)
    for z in range(binary.shape[2]):
        sl = binary[:, :, z]
        if sl.any():
            sl = filter_small_components(sl, 5)
            binary[:, :, z] = ndi.binary_opening(sl, structure=struct)
    if min_cluster_size > 1:
        binary = filter_small_components(binary, min_cluster_size)
    return binary.astype(np.uint8)


def save_like(data, canon_img, orig_img, path, dtype):
    out = nib.Nifti1Image(data.astype(dtype), canon_img.affine)
    out.set_data_dtype(dtype)
    to_orig = nib.orientations.ornt_transform(
        nib.orientations.io_orientation(canon_img.affine), nib.orientations.io_orientation(orig_img.affine))
    out = out.as_reoriented(to_orig)
    nib.save(out, path)


def main():
    args = build_arg_parser().parse_args()
    from tensorflow import keras

    orig = nib.load(args.flair)
    canon = nib.as_closest_canonical(orig)
    vol = np.nan_to_num(np.asanyarray(canon.dataobj).astype(np.float32))
    zooms = canon.header.get_zooms()[:3]

    brain = None
    if args.brainmask:
        brain = np.asanyarray(nib.as_closest_canonical(nib.load(args.brainmask)).dataobj) > 0
        if brain.shape != vol.shape:
            raise SystemExit(f"--brainmask shape {brain.shape} differs from the FLAIR {vol.shape}")
    if (args.strip or args.framing == "brainbox") and brain is None:
        raise SystemExit("--strip / --framing brainbox need --brainmask")
    if args.strip:
        vol = vol * brain
    hmask = head_mask(vol) if not args.strip else brain.copy()
    if brain is not None:
        hmask |= brain

    model = keras.models.load_model(args.model, compile=False)
    probs = predict_volume(model, vol, zooms, args.orientation, args.fov_fill, args.slab_mm, args.batch_size, hmask,
                           framing=args.framing, brain=brain)
    binary = decide(probs, args.decision, args.prob_threshold, args.min_cluster_size)

    save_like(binary, canon, orig, args.output, np.uint8)
    if args.output_prob:
        save_like(probs[..., 2], canon, orig, args.output_prob, np.float32)


if __name__ == "__main__":
    main()
