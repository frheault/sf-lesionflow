#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run mindGlide and also export its lesion (label 18) softmax probability map.

mindGlide's `run_inference()` argmaxes the sliding-window logits into a label
map and discards them -- there is no CLI flag to save probabilities. This
wrapper patches that one function at runtime, inserting (just before the label
map is saved) the softmax of the lesion channel, taken through the same
uncrop/reorientation steps as the label map, and restricted to the label map's
nonzero (keep-largest-component) brain extent. The patch is anchored on an
exact source line and aborts if it is not found, so an upstream code change
fails loudly rather than silently producing no/incorrect probabilities.

Resampled (anisotropic) inputs: mindGlide recovers the label map per class with
order-1 resizes (in two stages if anisotropic); the probability is recovered
with a single order-1 resize to the same crop shape -- equivalent for isotropic
inputs, a close approximation otherwise.

Usage: identical to `mindglide`; for `-o X.nii.gz` the map is `X_prob.nii.gz`.
The exported channel is $MINDGLIDE_PROB_LABEL (default 18, "Lesion").
"""

import os
import sys

LESION_LABEL = int(os.environ.get("MINDGLIDE_PROB_LABEL", 18))
ANCHOR = "                    save_atomically(nifti_img, opaths[idx])\n"
INJECT = (
    "                    _lp = torch.softmax(predictions[idx].float(), dim=0)[_LESION_LABEL].numpy()\n"
    "                    if resample_flag:\n"
    "                        from skimage.transform import resize as _resize\n"
    "                        _lp = _resize(_lp, crop_shape, order=1, mode='edge', clip=True, anti_aliasing=False)\n"
    "                    _lp_padded = np.zeros(original_shape, dtype=np.float32)\n"
    "                    _lp_padded[h_start:h_end, w_start:w_end, d_start:d_end] = _lp\n"
    "                    _prob_img = nib.Nifti1Image(_lp_padded, current_affine)\n"
    "                    if not np.all(current_orientation == original_orientation):\n"
    "                        _prob_img = _prob_img.as_reoriented(back_to_orig_ornt)\n"
    "                    _brain = np.asanyarray(nifti_img.dataobj) > 0\n"
    "                    _prob_img = nib.Nifti1Image(np.asanyarray(_prob_img.dataobj).astype(np.float32) * _brain,\n"
    "                                                nifti_img.affine)\n"
    "                    save_atomically(_prob_img, _prob_path(opaths[idx]))\n"
)


def _prob_path(out_path):
    for ext in (".nii.gz", ".nii"):
        if out_path.endswith(ext):
            return out_path[:-len(ext)] + "_prob" + ext
    return out_path + "_prob.nii.gz"


def main():
    import mindglide.infer as infer
    with open(infer.__file__) as f:
        src = f.read()
    if src.count(ANCHOR) != 1:
        sys.exit(f"Error: mindGlide source anchor not found exactly once in {infer.__file__}; "
                 "cannot expose the probability map for this mindGlide version")
    infer.__dict__["_LESION_LABEL"] = LESION_LABEL
    infer.__dict__["_prob_path"] = _prob_path
    exec(compile(src.replace(ANCHOR, INJECT + ANCHOR), infer.__file__, "exec"), infer.__dict__)
    sys.exit(infer.main())


if __name__ == "__main__":
    main()
