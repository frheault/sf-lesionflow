#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run LST-AI and also export its joint (3-model mean) lesion probability map.

LST-AI's `unet_segmentation()` averages the sigmoid outputs of its three U-Nets
into `joint_seg`, thresholds it (`--threshold`, default 0.5) and discards it --
there is no CLI flag to save it. This wrapper patches that one function at
runtime (inserting a save of `joint_seg`, padded back exactly like the binary
mask) and then runs the unmodified `lst` driver script. The patch is anchored on
an exact source line and aborts if it is not found, so an upstream code change
fails loudly rather than silently producing no/incorrect probabilities.

The probability is produced in LST-AI's internal MNI space; it is warped back to
the FLAIR space with the same greedy call LST-AI uses for its binary mask, but
with LINEAR instead of LABEL interpolation.

Usage: lst_ai_prob.py --output_prob P.nii.gz --work_dir W [lst args ...]
(`--temp W` is added to the lst call so its working files are kept.)
"""

import argparse
import os
import runpy
import shlex
import subprocess
import sys

ANCHOR = "    joint_seg /= len(unet_mdls)\n"
INJECT = (
    "    _prob = np.pad(joint_seg,\n"
    "        ((shape_lst[0], shape_lst[1]), (shape_lst[2], shape_lst[3]), (shape_lst[4], shape_lst[5])),\n"
    "        'constant', constant_values=0.)\n"
    "    nib.save(nib.Nifti1Image(_prob.astype(np.float32), t1_nib.affine),\n"
    "             output_segmentation_path.replace('.nii.gz', '_prob.nii.gz'))\n"
)


def main():
    # allow_abbrev=False: otherwise lst's own --output is prefix-matched to --output_prob
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     allow_abbrev=False)
    parser.add_argument("--output_prob", required=True, help="Output probability map in FLAIR space")
    parser.add_argument("--work_dir", required=True, help="LST-AI working directory (passed as --temp)")
    args, lst_args = parser.parse_known_args()
    if "--temp" in lst_args:
        sys.exit("Error: pass --work_dir instead of --temp")

    import LST_AI.segment as seg
    with open(seg.__file__) as f:
        src = f.read()
    if src.count(ANCHOR) != 1:
        sys.exit(f"Error: LST-AI source anchor not found exactly once in {seg.__file__}; "
                 "cannot expose the probability map for this LST-AI version")
    exec(compile(src.replace(ANCHOR, ANCHOR + INJECT), seg.__file__, "exec"), seg.__dict__)

    work_dir = os.path.abspath(args.work_dir)
    os.makedirs(work_dir, exist_ok=True)
    lst_script = os.path.join(os.path.dirname(seg.__file__), "lst")
    sys.argv = [lst_script] + lst_args + ["--temp", work_dir]
    try:
        runpy.run_path(lst_script, run_name="__main__")
    except SystemExit as e:
        if e.code not in (None, 0):
            raise

    # File names are fixed inside the lst driver script.
    prob_mni = os.path.join(work_dir, "sub-X_ses-Y_space-mni_seg-lst_prob.nii.gz")
    flair_ref = os.path.join(work_dir, "sub-X_ses-Y_space-flair_desc-stripped_FLAIR.nii.gz")
    affine = os.path.join(work_dir, "affine_flair_to_mni.mat")
    for p in (prob_mni, flair_ref, affine):
        if not os.path.isfile(p):
            sys.exit(f"Error: expected LST-AI intermediate missing: {p}")

    threads = os.environ.get("OMP_NUM_THREADS", "1")
    cmd = (f"greedy -threads {threads} -d 3 -rf {flair_ref} -ri LINEAR -rm {prob_mni} "
           f"{os.path.abspath(args.output_prob)} -r {affine},-1")
    subprocess.run(shlex.split(cmd), check=True)


if __name__ == "__main__":
    main()
