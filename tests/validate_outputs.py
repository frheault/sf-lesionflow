#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a finished sf-lesionflow results directory end to end.

Usage: validate_outputs.py <results_dir> [--algorithms a,b,c] [--input data] [--space MNI] [--json out.json]

Layout (see conf/output.config): results/sub-X/ses-Y/{anat,lesions,consensus,xfm,qc,multiqc}/,
results/sub-X/longitudinal/, results/multiqc/, results/pipeline_info/.

Global:
  - no broken symlinks; no path containing `ses-single`; every published file under sub-*/
    is prefixed with its subject (MultiQC data dirs excepted);
  - pipeline_info/software_versions.yml lists every active algorithm, no placeholder versions;
  - the algorithm container map in lib/AlgorithmSelection.groovy matches the processes.
Per session (discovered from --input, BIDS layout):
  - MNI anatomicals + MNI brain mask; every NIfTI in anat/ lesions/ consensus/ is on the template grid;
  - every active algorithm has _mask (values {0,1}), _probseg (finite, in [0,1], soft) or
    _zscore, and a JSON sidecar;
  - the probability map, thresholded at the algorithm's operating point, agrees with its mask:
      exact  (plain threshold of this very map)                      -> FAIL if Dice < 0.98
      close  (extra resampling/warping, argmax over >2 classes, ...) -> WARN if Dice < 0.70
      loose  (heavy post-processing)                                  -> reported only
  - no lesion voxel outside the (dilated) brain mask for brain-masked algorithms (FAIL),
    WARN above 1 % for the others;
  - agreement sanity: an algorithm whose mean Dice against the others is < 0.05 while its
    volume is > 2x the STAPLE consensus is flagged (WARN), as is a session mean < 0.25;
  - STAPLE consensus, QC files (registration metrics: no N/A, MNI scale in range), MultiQC report.
Per subject: longitudinal tracking CSV and one harmonized mask per session.
Exit status 1 if any FAIL.
"""

import argparse
import glob
import json
import os
import re
import sys

import nibabel as nib
import numpy as np
from scipy.ndimage import binary_dilation

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "bin"))
from _lesion_utils import BIDS_LABEL  # noqa: E402

DEFAULT = ["lst_ai", "samseg", "wmh_synthseg", "flames", "hypermapp3r", "segcsvd", "emory_robust",
           "mars_wmh", "bawil", "mimosa", "shivai", "mindglide"]
UNSTRIPPED_INPUT = {"samseg", "wmh_synthseg", "mars_wmh", "bawil", "mindglide"}

# algorithm -> (probability threshold of its own binary, agreement class). The binaries of the
# native-space algorithms (LST-AI, TrueNet, MARS-WMH, BAWIL, mindGlide) are NearestNeighbor-warped
# while their prob maps are Linear-warped, hence "close" at best.
EXPECT = {
    "flames": (0.5, "exact"), "emory_robust": (0.5, "exact"), "hypermapp3r": (0.5, "exact"),
    "segcsvd": (0.35, "exact"),
    "mars_wmh": (0.5, "close"), "truenet": (0.5, "close"), "lst_ai": (0.5, "close"),
    "wmh_synthseg": (0.5, "close"), "samseg": (0.5, "close"), "mindglide": (0.5, "close"),
    "shivai": (0.5, "close"),
    "bawil": (0.5, "loose"),  # argmax over 3 classes + 2D/3D post-processing
    "mimosa": (0.3, "loose"), "fast_outlier": (None, "loose"),
}
PLACEHOLDER_VERSIONS = {"1.0", "2.0"}  # values the old hard-coded heredocs used

fails, warns = [], []


def fail(msg):
    fails.append(msg)
    print(f"  FAIL  {msg}")


def warn(msg):
    warns.append(msg)
    print(f"  WARN  {msg}")


def ok(msg):
    print(f"  ok    {msg}")


def load(path):
    try:
        img = nib.load(path)
        return img, np.asanyarray(img.dataobj).astype(np.float32)
    except Exception as e:  # noqa: BLE001
        fail(f"{path}: unreadable ({e})")
        return None, None


def same_grid(a, b):
    return a.shape[:3] == b.shape[:3] and np.allclose(a.affine, b.affine, atol=1e-3)


def dice(a, b):
    d = a.sum() + b.sum()
    return 2.0 * np.logical_and(a, b).sum() / d if d else 1.0


def nonempty(path, what, tag):
    if not os.path.exists(path) or (os.path.isfile(path) and os.path.getsize(path) == 0):
        fail(f"{tag}: missing/empty {what} ({path})")
        return False
    if os.path.isdir(path) and not os.listdir(path):
        fail(f"{tag}: empty {what} dir ({path})")
        return False
    return True


def check_algo(lesdir, sid, algo, space, ref, brain, masked):
    """Returns the boolean mask (or None)."""
    label = BIDS_LABEL[algo]
    tag = f"{sid} {algo}"
    stem = os.path.join(lesdir, f"{sid}_space-{space}_desc-{label}")
    mask_p, json_p = f"{stem}_mask.nii.gz", f"{stem}_mask.json"
    prob_p = f"{stem}_zscore.nii.gz" if algo == "fast_outlier" else f"{stem}_probseg.nii.gz"
    for p in (mask_p, prob_p, json_p):
        if not os.path.exists(p):
            fail(f"{tag}: missing {os.path.basename(p)}")
            return None
    sidecar = json.load(open(json_p))

    m_img, m = load(mask_p)
    if m_img is None:
        return None
    if ref is not None and not same_grid(m_img, ref):
        fail(f"{tag}: mask is not on the template grid")
        return None
    vals = np.unique(m)
    if not np.all(np.isin(vals, [0, 1])):
        fail(f"{tag}: mask not binary (values {vals[:6]})")
    m = m > 0
    vox_ml = float(np.prod(m_img.header.get_zooms()[:3])) / 1000

    p_img, p = load(prob_p)
    if p_img is None:
        return m
    if not same_grid(p_img, m_img):
        fail(f"{tag}: prob map not on the mask grid")
        return m
    if not np.all(np.isfinite(p)):
        fail(f"{tag}: prob map has non-finite values")
        return m
    is_z = algo == "fast_outlier"
    if not is_z and (p.min() < -1e-4 or p.max() > 1 + 1e-4):
        fail(f"{tag}: prob map outside [0,1] ({p.min():.3f}..{p.max():.3f})")
    if not is_z and np.unique(p[p > 0]).size <= 2:
        if sidecar.get("ProbabilityIsBinary") and algo == "truenet":
            warn(f"{tag}: no soft output available (binary published as probseg)")
        else:
            fail(f"{tag}: probseg is binary, not a soft map")

    # Brain containment
    if brain is not None:
        outside = int((m & ~brain).sum())
        frac = outside / max(int(m.sum()), 1)
        if masked and outside:
            fail(f"{tag}: {outside} lesion voxels outside the brain mask although brain masking was applied")
        elif not masked and frac > 0.01:
            warn(f"{tag}: {100 * frac:.1f}% of lesion voxels outside the brain mask")
    if masked and not sidecar.get("BrainMaskApplied"):
        fail(f"{tag}: expected brain masking (unstripped input) but sidecar says it was not applied")

    thr, cls = EXPECT.get(algo, (0.5, "loose"))
    removed = sidecar.get("VolumeRemovedByBrainMask_MNI_mL", 0.0)
    summary = f"{algo:13s} {m.sum() * vox_ml:7.2f} mL" + (f" (-{removed:.2f} mL brainmask)" if masked else "")
    if thr is None:
        ok(f"{tag}: {summary}")
        return m
    d = dice(p >= thr, m)
    line = f"{summary}  Dice(p>={thr}, mask)={d:.3f} [{cls}]"
    if cls == "exact" and d < 0.98:
        fail(f"{tag}: {line}")
    elif cls == "close" and d < 0.70:
        warn(f"{tag}: {line}")
    else:
        ok(f"{tag}: {line}")
    return m


def check_registration(qcdir, sid):
    for tsv in sorted(glob.glob(os.path.join(qcdir, f"{sid}_desc-reg*_qc.tsv"))):
        rows = [l.rstrip("\n").split("\t") for l in open(tsv) if not l.startswith("#") and l.strip()]
        if len(rows) < 2:
            fail(f"{sid}: empty registration table {os.path.basename(tsv)}")
            continue
        rec = dict(zip(rows[0], rows[1]))
        stage = rec.get("Stage", "?")
        na = [k for k in ("NCC", "NMI", "Mask_Dice", "Affine_Scale_Factor") if rec.get(k, "N/A") == "N/A"]
        if na:
            fail(f"{sid}: registration {stage} has N/A metrics: {', '.join(na)}")
            continue
        scale = float(rec["Affine_Scale_Factor"])
        msg = (f"{sid}: registration {stage} NCC {float(rec['NCC']):.3f} NMI {float(rec['NMI']):.3f} "
               f"MaskDice {float(rec['Mask_Dice']):.3f} scale {scale:.3f} [{rec.get('Status')}]")
        if stage == "baseline_to_mni" and not (0.7 <= scale <= 1.9):
            warn(msg + " -- MNI scale factor out of range")
        elif stage != "baseline_to_mni" and abs(scale - 1) > 1e-3:
            fail(msg + " -- rigid stage with non-unit scale")
        elif not rec.get("Status", "").startswith("PASS"):
            warn(msg)
        else:
            ok(msg)


def check_versions(R, algos):
    p = os.path.join(R, "pipeline_info", "software_versions.yml")
    if not os.path.exists(p):
        fail("pipeline_info/software_versions.yml missing")
        return
    text = open(p).read()
    blocks = {}
    cur = None
    for line in text.splitlines():
        m = re.match(r'^"?([A-Za-z0-9_:]+)"?:\s*$', line)
        if m:
            cur = m.group(1).split(":")[-1]
            blocks.setdefault(cur, {})
            continue
        m = re.match(r'^\s+([^:]+):\s*"?([^"]*)"?\s*$', line)
        if m and cur:
            blocks[cur][m.group(1).strip()] = m.group(2).strip()
    for algo in algos:
        proc = f"SEGMENTATION_{algo.upper()}"
        if proc not in blocks:
            fail(f"software versions: {proc} missing")
            continue
        vals = {k: v for k, v in blocks[proc].items() if k != "container"}
        bad = [k for k, v in vals.items() if v in PLACEHOLDER_VERSIONS and k not in ("tensorflow", "torch")]
        unknown = [k for k, v in vals.items() if v == "unknown"]
        if not vals:
            warn(f"software versions: {proc} has only a container reference")
        elif bad:
            warn(f"software versions: {proc} has placeholder-looking values: {bad}")
        elif unknown:
            warn(f"software versions: {proc} could not probe {unknown}")
        else:
            ok(f"software versions: {proc} " + ", ".join(f"{k}={v}" for k, v in vals.items() if k != "python"))


def check_containers():
    groovy = open(os.path.join(REPO, "lib", "AlgorithmSelection.groovy")).read()
    block = groovy[groovy.index("CONTAINER = ["):]
    block = block[: block.index("]")]
    declared = dict(re.findall(r"(\w+)\s*:\s*'([^']+)'", block))
    nf = open(os.path.join(REPO, "modules", "local", "lesion_segmentation.nf")).read()
    actual = {}
    for m in re.finditer(r"process (SEGMENTATION_\w+|PREPROC_SYNTHSEG) \{\s*.*?container '([^']+)'", nf, flags=re.S):
        key = m.group(1).replace("SEGMENTATION_", "").replace("PREPROC_", "").lower()
        actual[key] = m.group(2)
    mismatch = {k: (declared.get(k), v) for k, v in actual.items() if declared.get(k) != v}
    if mismatch:
        fail(f"container map out of sync with lesion_segmentation.nf: {mismatch}")
    else:
        ok(f"container map matches {len(actual)} processes")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("--algorithms", default=",".join(DEFAULT))
    ap.add_argument("--input", default="data")
    ap.add_argument("--space", default="MNI")
    ap.add_argument("--brainmask_mode", default="unstripped", choices=("unstripped", "all", "none"))
    ap.add_argument("--json", default=None, help="Also write the FAIL/WARN lists to this JSON file")
    args = ap.parse_args()
    algos = [a.strip() for a in args.algorithms.split(",") if a.strip()]
    masked_set = {"unstripped": UNSTRIPPED_INPUT, "all": set(algos), "none": set()}[args.brainmask_mode]
    R, S = args.results, args.space

    print("== layout")
    broken, single, unprefixed = [], [], []
    for r, dirs, fs in os.walk(R):
        rel = os.path.relpath(r, R)
        if "ses-single" in rel:
            single.append(rel)
        in_mqc_data = re.search(r"_multiqc_report_(data|plots)", rel)
        top = rel.split(os.sep)[0]
        for f in fs:
            p = os.path.join(r, f)
            if os.path.islink(p) and not os.path.exists(p):
                broken.append(p)
            if top.startswith("sub-") and not in_mqc_data and not f.startswith(top):
                unprefixed.append(os.path.join(rel, f))
    if broken:
        fail(f"{len(broken)} broken symlink(s), e.g. {broken[0]}")
    if single:
        fail(f"'ses-single' directories present: {single[:3]}")
    if unprefixed:
        fail(f"{len(unprefixed)} published file(s) without subject prefix, e.g. {unprefixed[:3]}")
    if not (broken or single or unprefixed):
        ok("no broken symlinks, no ses-single, every file subject-prefixed")
    check_containers()
    check_versions(R, algos)

    subjects = sorted(os.path.basename(s) for s in glob.glob(os.path.join(args.input, "sub-*")))
    for sub in subjects:
        sessions = sorted(os.path.basename(s) for s in glob.glob(os.path.join(args.input, sub, "ses-*")))
        for ses in sessions:
            sid = f"{sub}_{ses}"
            sesdir = os.path.join(R, sub, ses)
            print(f"\n== {sid}")
            if not nonempty(sesdir, "session output", sid):
                continue
            anat = os.path.join(sesdir, "anat")
            ref = brain = None
            for d in ("brain_T1w", "brain_FLAIR", "head_T1w", "head_FLAIR", "brain_mask"):
                f = os.path.join(anat, f"{sid}_space-{S}_desc-{d}.nii.gz")
                if nonempty(f, f"anat desc-{d}", sid) and ref is None:
                    ref = nib.load(f)
            bm = os.path.join(anat, f"{sid}_space-{S}_desc-brain_mask.nii.gz")
            if os.path.exists(bm):
                bimg, b = load(bm)
                if bimg is not None:
                    brain = binary_dilation(b > 0, iterations=1)
            for d in ("anat", "lesions", "consensus"):
                for f in glob.glob(os.path.join(sesdir, d, "*.nii.gz")):
                    if ref is not None and not same_grid(nib.load(f), ref):
                        fail(f"{sid}: {d}/{os.path.basename(f)} is not on the template grid")

            masks = {}
            for algo in algos:
                m = check_algo(os.path.join(sesdir, "lesions"), sid, algo, S, ref, brain, algo in masked_set)
                if m is not None:
                    masks[algo] = m

            cons = os.path.join(sesdir, "consensus", f"{sid}_space-{S}_desc-staple")
            for suffix in ("probseg", "mask", "dseg"):
                f = f"{cons}_{suffix}.nii.gz"
                if nonempty(f, f"STAPLE {suffix}", sid) and suffix == "probseg":
                    _, a = load(f)
                    if a is not None and (a.min() < -1e-4 or a.max() > 1 + 1e-4):
                        fail(f"{sid}: STAPLE probseg outside [0,1]")
            st = None
            if os.path.exists(f"{cons}_mask.nii.gz"):
                st_img, st = load(f"{cons}_mask.nii.gz")
                if st is not None:
                    st = st > 0
                    vox_ml = float(np.prod(st_img.header.get_zooms()[:3])) / 1000
                    ok(f"{sid}: STAPLE consensus {st.sum() * vox_ml:.2f} mL (MNI-normalized)")

            # Agreement sanity
            names = sorted(masks)
            if len(names) > 1:
                mat = {(a, b): dice(masks[a], masks[b]) for a in names for b in names if a < b}
                mean_all = float(np.mean(list(mat.values())))
                (warn if mean_all < 0.25 else ok)(f"{sid}: mean inter-algorithm Dice {mean_all:.3f}")
                for a in names:
                    mean_a = float(np.mean([mat[tuple(sorted((a, b)))] for b in names if b != a]))
                    if st is not None and mean_a < 0.05 and masks[a].sum() > 2 * max(st.sum(), 1):
                        warn(f"{sid}: outlier algorithm {a}: mean Dice vs others {mean_a:.3f}, "
                             f"volume {masks[a].sum() / max(st.sum(), 1):.1f}x STAPLE")

            qc = os.path.join(sesdir, "qc")
            if nonempty(qc, "qc", sid):
                check_registration(qc, sid)
                for kind in ("ensemblevolumes", "pairwisedice", "staplesummary", "consensus"):
                    if not glob.glob(os.path.join(qc, f"{sid}_desc-{kind}_qc.*")):
                        fail(f"{sid}: missing qc desc-{kind}")
            if not glob.glob(os.path.join(sesdir, "multiqc", "*_multiqc_report.html")):
                fail(f"{sid}: no per-session MultiQC report")

        print(f"\n== {sub} (longitudinal)")
        lon = os.path.join(R, sub, "longitudinal")
        csv = os.path.join(lon, f"{sub}_space-{S}_desc-lesiontracking.csv")
        if nonempty(csv, "lesion tracking CSV", sub):
            header = open(csv).readline()
            if "Vol_MNI_mm3_" not in header:
                fail(f"{sub}: tracking CSV lacks MNI-normalized volume columns")
            ok(f"{sub}: lesion tracking CSV, {sum(1 for _ in open(csv)) - 1} rows")
        harm = glob.glob(os.path.join(lon, f"{sub}_ses-*_space-{S}_desc-harmonized_mask.nii.gz"))
        if len(harm) != len(sessions):
            fail(f"{sub}: {len(harm)} harmonized masks for {len(sessions)} sessions")
        if not glob.glob(os.path.join(lon, "qc", f"{sub}_desc-*_qc.tsv")):
            fail(f"{sub}: missing longitudinal qc tables")

    print("\n== global")
    if not glob.glob(os.path.join(R, "multiqc", "cohort_multiqc_report.html")):
        fail("no cohort MultiQC report")
    else:
        ok("cohort MultiQC report present")

    print(f"\nSUMMARY: {len(fails)} FAIL, {len(warns)} WARN")
    if args.json:
        with open(args.json, "w") as f:
            json.dump({"fail": fails, "warn": warns}, f, indent=2)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
