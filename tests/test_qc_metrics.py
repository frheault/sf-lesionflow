"""Unit tests for sf-lesionflow MultiQC helper scripts."""

import os
import subprocess
import sys
from pathlib import Path
import numpy as np
import nibabel as nib
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "bin"))

# ── compute_dice ──────────────────────────────────────────────────────────────
def test_dice_identical():
    from qc_ensemble_metrics import compute_dice

    a = np.ones((10, 10, 10), dtype=bool)
    assert compute_dice(a, a) == 1.0


def test_dice_disjoint():
    from qc_ensemble_metrics import compute_dice

    a = np.zeros((10, 10, 10), dtype=bool)
    a[:5] = True
    b = np.zeros((10, 10, 10), dtype=bool)
    b[5:] = True
    assert compute_dice(a, b) == 0.0


def test_dice_both_empty():
    """Two empty masks -> perfect agreement (1.0), never NaN."""
    from qc_ensemble_metrics import compute_dice

    a = np.zeros((10, 10, 10), dtype=bool)
    assert compute_dice(a, a) == 1.0


def test_dice_partial():
    from qc_ensemble_metrics import compute_dice

    a = np.zeros((10, 10, 10), dtype=bool)
    b = np.zeros((10, 10, 10), dtype=bool)
    a[:4, :4, :4] = True  # 64 voxels
    b[:4, :4, 2:6] = True  # 64 voxels, overlap in 2:4 -> 32 voxels
    # intersection = 32, sum = 128 -> dice = 64/128 = 0.5
    assert compute_dice(a, b) == pytest.approx(0.5, rel=1e-3)



# ── qc_ensemble_metrics.py ────────────────────────────────────────────────────
def test_ensemble_metrics_cli(tmp_path):
    """End-to-end CLI test with synthetic 3D NIfTIs."""
    affine = np.eye(4)
    cons = np.zeros((20, 20, 20), dtype=np.uint8)
    cons[5:15, 5:15, 5:15] = 1  # 10x10x10 = 1000 voxels = 1.0 mL at 1mm³
    cons_path = str(tmp_path / "sub-001_ses-1_staple_thr90_binary.nii.gz")
    nib.save(nib.Nifti1Image(cons, affine), cons_path)

    masks = []
    for algo in ["lst_ai", "truenet", "fast_outlier"]:
        m = np.zeros((20, 20, 20), dtype=np.uint8)
        m[6:14, 6:14, 6:14] = 1  # 8x8x8 = 512 voxels = 0.512 mL
        p = str(tmp_path / f"sub-001_ses-1_{algo}_binary.nii.gz")
        nib.save(nib.Nifti1Image(m, affine), p)
        masks.append(p)

    out_vol = str(tmp_path / "volumes_mqc.tsv")
    out_dice = str(tmp_path / "dice_mqc.tsv")
    out_sum = str(tmp_path / "summary_mqc.tsv")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_ensemble_metrics.py",
            "--meta_id",
            "sub-001_ses-1",
            "--consensus",
            cons_path,
            "--masks",
        ]
        + masks
        + [
            "--out_volumes",
            out_vol,
            "--out_dice",
            out_dice,
            "--out_summary",
            out_sum,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()

    # All volumes must be in mL (1.000 for 1000 voxels of 1mm³)
    df_vol = pd.read_csv(out_vol, sep="\t", comment="#")
    assert "STAPLE_Consensus" in df_vol.columns
    assert "lst_ai" in df_vol.columns
    assert df_vol["STAPLE_Consensus"].iloc[0] == pytest.approx(1.000, rel=1e-2)
    assert df_vol["lst_ai"].iloc[0] == pytest.approx(0.512, rel=1e-2)

    # Dice heatmap must be square
    df_dice = pd.read_csv(out_dice, sep="\t", comment="#")
    assert df_dice.shape[0] == df_dice.shape[1] - 1  # rows=algos, cols=Algorithm+algos

    # Scalar summary
    df_sum = pd.read_csv(out_sum, sep="\t", comment="#")
    assert df_sum["Consensus_TLV_mL"].iloc[0] == pytest.approx(1.000, rel=1e-2)
    assert df_sum["Consensus_Lesion_Count"].iloc[0] == 1
    assert df_sum["Active_Algos"].iloc[0] == 3


def test_ensemble_metrics_zero_lesions(tmp_path):
    """Zero lesion consensus test."""
    affine = np.eye(4)
    cons = np.zeros((20, 20, 20), dtype=np.uint8)
    cons_path = str(tmp_path / "sub-zero_ses-1_staple_thr90_binary.nii.gz")
    nib.save(nib.Nifti1Image(cons, affine), cons_path)

    m = np.zeros((20, 20, 20), dtype=np.uint8)
    p = str(tmp_path / "sub-zero_ses-1_lst_ai_binary.nii.gz")
    nib.save(nib.Nifti1Image(m, affine), p)

    out_vol = str(tmp_path / "zero_volumes_mqc.tsv")
    out_dice = str(tmp_path / "zero_dice_mqc.tsv")
    out_sum = str(tmp_path / "zero_summary_mqc.tsv")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_ensemble_metrics.py",
            "--meta_id",
            "sub-zero_ses-1",
            "--consensus",
            cons_path,
            "--masks",
            p,
            "--out_volumes",
            out_vol,
            "--out_dice",
            out_dice,
            "--out_summary",
            out_sum,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()

    df_sum = pd.read_csv(out_sum, sep="\t", comment="#")
    assert df_sum["Consensus_TLV_mL"].iloc[0] == 0.0
    assert df_sum["Consensus_Lesion_Count"].iloc[0] == 0


# ── qc_registration.py ────────────────────────────────────────────────────────
@pytest.mark.parametrize("stage", ["flair_to_t1", "t1_to_baseline", "baseline_to_mni"])
def test_registration_cli(tmp_path, stage):
    affine = np.eye(4)
    fixed = np.random.RandomState(42).rand(20, 20, 20).astype(np.float32)
    warped = np.random.RandomState(43).rand(20, 20, 20).astype(np.float32)

    fixed_p = str(tmp_path / f"fixed_{stage}.nii.gz")
    warped_p = str(tmp_path / f"warped_{stage}.nii.gz")
    nib.save(nib.Nifti1Image(fixed, affine), fixed_p)
    nib.save(nib.Nifti1Image(warped, affine), warped_p)

    out_metrics = str(tmp_path / f"metrics_{stage}.tsv")
    out_png = str(tmp_path / f"overlay_{stage}.png")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_registration.py",
            "--meta_id",
            "sub-001_ses-1",
            "--stage",
            stage,
            "--fixed",
            fixed_p,
            "--moving_warped",
            warped_p,
            "--out_metrics",
            out_metrics,
            "--out_png",
            out_png,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    assert os.path.isfile(out_png)
    assert os.path.getsize(out_png) > 1000

    df = pd.read_csv(out_metrics, sep="\t", comment="#", keep_default_na=False)
    assert df["Sample"].iloc[0] == f"sub-001_ses-1_{stage}"
    assert df["Stage"].iloc[0] == stage
    assert df["Final_Metric_Value"].iloc[0] == "N/A"


def test_registration_with_log(tmp_path):
    affine = np.eye(4)
    fixed = np.ones((20, 20, 20), dtype=np.float32)
    warped = np.ones((20, 20, 20), dtype=np.float32)

    fixed_p = str(tmp_path / "fixed_log.nii.gz")
    warped_p = str(tmp_path / "warped_log.nii.gz")
    nib.save(nib.Nifti1Image(fixed, affine), fixed_p)
    nib.save(nib.Nifti1Image(warped, affine), warped_p)

    log_p = str(tmp_path / "ants.log")
    with open(log_p, "w") as f:
        f.write("DIAGNOSTIC,iteration,10,metricValue,-0.87654\n")

    out_metrics = str(tmp_path / "metrics_log.tsv")
    out_png = str(tmp_path / "overlay_log.png")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_registration.py",
            "--meta_id",
            "sub-001_ses-1",
            "--stage",
            "flair_to_t1",
            "--fixed",
            fixed_p,
            "--moving_warped",
            warped_p,
            "--log",
            log_p,
            "--out_metrics",
            out_metrics,
            "--out_png",
            out_png,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    df = pd.read_csv(out_metrics, sep="\t", comment="#")
    assert df["Final_Metric_Value"].iloc[0] == pytest.approx(-0.8765, abs=1e-3)


# ── qc_lesion_screenshot.py ───────────────────────────────────────────────────
def test_lesion_screenshot_with_lesions(tmp_path):
    affine = np.eye(4)
    anat = np.random.RandomState(42).rand(30, 30, 30).astype(np.float32)
    mask = np.zeros((30, 30, 30), dtype=np.uint8)
    mask[12:18, 12:18, 12:18] = 1

    anat_p = str(tmp_path / "flair.nii.gz")
    mask_p = str(tmp_path / "consensus.nii.gz")
    out_png = str(tmp_path / "screenshot.png")

    nib.save(nib.Nifti1Image(anat, affine), anat_p)
    nib.save(nib.Nifti1Image(mask, affine), mask_p)

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_lesion_screenshot.py",
            "--meta_id",
            "sub-001_ses-1",
            "--anat",
            anat_p,
            "--mask",
            mask_p,
            "--out_png",
            out_png,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    assert os.path.isfile(out_png)
    assert os.path.getsize(out_png) > 1000


def test_lesion_screenshot_zero_lesions(tmp_path):
    affine = np.eye(4)
    anat = np.random.RandomState(42).rand(30, 30, 30).astype(np.float32)
    mask = np.zeros((30, 30, 30), dtype=np.uint8)

    anat_p = str(tmp_path / "flair_zero.nii.gz")
    mask_p = str(tmp_path / "consensus_zero.nii.gz")
    out_png = str(tmp_path / "screenshot_zero.png")

    nib.save(nib.Nifti1Image(anat, affine), anat_p)
    nib.save(nib.Nifti1Image(mask, affine), mask_p)

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_lesion_screenshot.py",
            "--meta_id",
            "sub-001_ses-1",
            "--anat",
            anat_p,
            "--mask",
            mask_p,
            "--out_png",
            out_png,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    assert os.path.isfile(out_png)
    assert os.path.getsize(out_png) > 1000


# ── qc_longitudinal_summary.py ────────────────────────────────────────────────
def test_longitudinal_single_session(tmp_path):
    """Single-session subject -> delta=0, pct_change=0, No_Lesions_Flag=0."""
    csv_path = str(tmp_path / "sub-001_tracking.csv")
    df = pd.DataFrame(
        {
            "Lesion_ID": [1, 2],
            "Vol_mm3_ses-1": [500.0, 300.0],
            "Status": ["Baseline", "Baseline"],
            "Delta_Vol_mm3": [0.0, 0.0],
            "Pct_Change": [0.0, 0.0],
            "Centroid_X_mm": [0, 0],
            "Centroid_Y_mm": [0, 0],
            "Centroid_Z_mm": [0, 0],
        }
    )
    df.to_csv(csv_path, index=False)

    out_sum = str(tmp_path / "summary.tsv")
    out_traj = str(tmp_path / "traj.tsv")
    out_inst = str(tmp_path / "inst.tsv")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_longitudinal_summary.py",
            "--subject",
            "sub-001",
            "--audit_csv",
            csv_path,
            "--out_summary",
            out_sum,
            "--out_trajectories",
            out_traj,
            "--out_instances",
            out_inst,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()

    row = pd.read_csv(out_sum, sep="\t", comment="#").iloc[0]
    assert row["Net_Delta_TLV_mL"] == 0.0
    assert row["Percent_Change"] == 0.0
    assert row["No_Lesions_Flag"] == 0  # lesions exist, just single session
    assert row["Baseline_TLV_mL"] == 0.8  # (500 + 300) / 1000 mL
    assert row["Followup_TLV_mL"] == 0.8


def test_longitudinal_zero_lesions(tmp_path):
    """Zero-lesion subject -> No_Lesions_Flag=1."""
    csv_path = str(tmp_path / "sub-002_tracking.csv")
    df = pd.DataFrame(
        {
            "Lesion_ID": [],
            "Vol_mm3_ses-1": [],
            "Status": [],
            "Delta_Vol_mm3": [],
            "Pct_Change": [],
            "Centroid_X_mm": [],
            "Centroid_Y_mm": [],
            "Centroid_Z_mm": [],
        }
    )
    df.to_csv(csv_path, index=False)

    out_sum = str(tmp_path / "summary.tsv")
    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_longitudinal_summary.py",
            "--subject",
            "sub-002",
            "--audit_csv",
            csv_path,
            "--out_summary",
            out_sum,
            "--out_trajectories",
            str(tmp_path / "traj.tsv"),
            "--out_instances",
            str(tmp_path / "inst.tsv"),
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    row = pd.read_csv(out_sum, sep="\t", comment="#").iloc[0]
    assert row["No_Lesions_Flag"] == 1
    assert row["Baseline_TLV_mL"] == 0.0
    assert row["Followup_TLV_mL"] == 0.0


def test_longitudinal_many_sessions_numeric_sort(tmp_path):
    """Regression test for the ses-2/ses-10 lexicographic-sort bug.

    A subject with 11 sessions (ses-1 .. ses-11) must pick ses-1 as baseline and
    ses-11 as the final follow-up -- NOT ses-1 vs ses-10.
    """
    csv_path = str(tmp_path / "sub-003_tracking.csv")
    n_sessions = 11
    data = {"Lesion_ID": [1], "Status": ["Enlarging"]}
    for i in range(1, n_sessions + 1):
        data[f"Vol_mm3_ses-{i}"] = [100.0 + (i - 1) * 50.0]
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)

    out_sum = str(tmp_path / "summary.tsv")
    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_longitudinal_summary.py",
            "--subject",
            "sub-003",
            "--audit_csv",
            csv_path,
            "--out_summary",
            out_sum,
            "--out_trajectories",
            str(tmp_path / "traj.tsv"),
            "--out_instances",
            str(tmp_path / "inst.tsv"),
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()

    row = pd.read_csv(out_sum, sep="\t", comment="#").iloc[0]
    assert row["Baseline_TLV_mL"] == pytest.approx(0.1, rel=1e-3)
    assert row["Followup_TLV_mL"] == pytest.approx(0.6, rel=1e-3)
    assert row["Net_Delta_TLV_mL"] == pytest.approx(0.5, rel=1e-3)


def test_longitudinal_new_lesions_from_zero_baseline(tmp_path):
    """Regression test: a subject with NO lesions at baseline that develops lesions
    at follow-up must not be reported as "0.0%" change -- expect "N/A".
    """
    csv_path = str(tmp_path / "sub-004_tracking.csv")
    df = pd.DataFrame(
        {
            "Lesion_ID": [1],
            "Vol_mm3_ses-1": [0.0],
            "Vol_mm3_ses-2": [400.0],
            "Status": ["New"],
        }
    )
    df.to_csv(csv_path, index=False)

    out_sum = str(tmp_path / "summary.tsv")
    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_longitudinal_summary.py",
            "--subject",
            "sub-004",
            "--audit_csv",
            csv_path,
            "--out_summary",
            out_sum,
            "--out_trajectories",
            str(tmp_path / "traj.tsv"),
            "--out_instances",
            str(tmp_path / "inst.tsv"),
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()

    row = pd.read_csv(out_sum, sep="\t", comment="#", keep_default_na=False).iloc[0]
    assert str(row["Percent_Change"]) == "N/A"
    assert row["New_Lesions"] == 1


def test_ensemble_metrics_multiple_components(tmp_path):
    """Test connected components counting with multiple disjoint lesions."""
    affine = np.eye(4)
    cons = np.zeros((30, 30, 30), dtype=np.uint8)
    cons[2:5, 2:5, 2:5] = 1   # Component 1 (27 voxels)
    cons[10:14, 10:14, 10:14] = 1  # Component 2 (64 voxels)
    cons[20:25, 20:25, 20:25] = 1  # Component 3 (125 voxels)
    cons_path = str(tmp_path / "sub-mult_ses-1_staple_thr90_binary.nii.gz")
    nib.save(nib.Nifti1Image(cons, affine), cons_path)

    m = np.zeros((30, 30, 30), dtype=np.uint8)
    m[10:14, 10:14, 10:14] = 1
    p = str(tmp_path / "sub-mult_ses-1_lst_ai_binary.nii.gz")
    nib.save(nib.Nifti1Image(m, affine), p)

    out_vol = str(tmp_path / "mult_vol.tsv")
    out_dice = str(tmp_path / "mult_dice.tsv")
    out_sum = str(tmp_path / "mult_sum.tsv")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_ensemble_metrics.py",
            "--meta_id",
            "sub-mult_ses-1",
            "--consensus",
            cons_path,
            "--masks",
            p,
            "--out_volumes",
            out_vol,
            "--out_dice",
            out_dice,
            "--out_summary",
            out_sum,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    df_sum = pd.read_csv(out_sum, sep="\t", comment="#")
    assert df_sum["Consensus_Lesion_Count"].iloc[0] == 3
    total_vox = 27 + 64 + 125  # 216 voxels = 0.216 mL
    assert df_sum["Consensus_TLV_mL"].iloc[0] == pytest.approx(0.216, rel=1e-2)


def test_registration_non_canonical_orientation(tmp_path):
    """Test that non-canonical (e.g. LAS) affine orientation is safely handled."""
    # LAS affine: diagonal [-1, 1, 1, 1]
    las_affine = np.diag([-1, 1, 1, 1])
    fixed = np.random.RandomState(99).rand(20, 20, 20).astype(np.float32)
    warped = np.random.RandomState(100).rand(20, 20, 20).astype(np.float32)

    fixed_p = str(tmp_path / "fixed_las.nii.gz")
    warped_p = str(tmp_path / "warped_las.nii.gz")
    nib.save(nib.Nifti1Image(fixed, las_affine), fixed_p)
    nib.save(nib.Nifti1Image(warped, las_affine), warped_p)

    out_metrics = str(tmp_path / "metrics_las.tsv")
    out_png = str(tmp_path / "overlay_las.png")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_registration.py",
            "--meta_id",
            "sub-las_ses-1",
            "--stage",
            "flair_to_t1",
            "--fixed",
            fixed_p,
            "--moving_warped",
            warped_p,
            "--out_metrics",
            out_metrics,
            "--out_png",
            out_png,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    assert os.path.isfile(out_png)
    assert os.path.getsize(out_png) > 1000


def test_dice_mismatched_shape():
    """Mismatched array shapes must return 0.0 without raising an exception."""
    from qc_ensemble_metrics import compute_dice

    a = np.ones((10, 10, 10), dtype=bool)
    b = np.ones((10, 10, 12), dtype=bool)
    assert compute_dice(a, b) == 0.0


def test_ensemble_metrics_single_algorithm(tmp_path):
    """Degenerate 1-algorithm case must yield 1x1 Dice matrix and mean dice = 1.0."""
    affine = np.eye(4)
    cons = np.zeros((20, 20, 20), dtype=np.uint8)
    cons[5:15, 5:15, 5:15] = 1
    cons_p = str(tmp_path / "sub-single_ses-1_staple_thr90_binary.nii.gz")
    nib.save(nib.Nifti1Image(cons, affine), cons_p)

    m = np.zeros((20, 20, 20), dtype=np.uint8)
    m[5:15, 5:15, 5:15] = 1
    p = str(tmp_path / "sub-single_ses-1_lst_ai_binary.nii.gz")
    nib.save(nib.Nifti1Image(m, affine), p)

    out_vol = str(tmp_path / "single_vol.tsv")
    out_dice = str(tmp_path / "single_dice.tsv")
    out_sum = str(tmp_path / "single_sum.tsv")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_ensemble_metrics.py",
            "--meta_id",
            "sub-single_ses-1",
            "--consensus",
            cons_p,
            "--masks",
            p,
            "--out_volumes",
            out_vol,
            "--out_dice",
            out_dice,
            "--out_summary",
            out_sum,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    df_sum = pd.read_csv(out_sum, sep="\t", comment="#")
    assert df_sum["Active_Algos"].iloc[0] == 1
    assert df_sum["Mean_Inter_Algo_Dice"].iloc[0] == 1.0
    df_dice = pd.read_csv(out_dice, sep="\t", comment="#")
    assert df_dice.shape == (1, 2)  # 1 row, columns: Algorithm + lst_ai
    assert df_dice["lst_ai"].iloc[0] == 1.0


def test_registration_4d_singleton(tmp_path):
    """Test registration QC with 4D images containing a singleton 4th dimension."""
    affine = np.eye(4)
    fixed = np.random.RandomState(42).rand(20, 20, 20, 1).astype(np.float32)
    warped = np.random.RandomState(43).rand(20, 20, 20, 1).astype(np.float32)

    fixed_p = str(tmp_path / "fixed_4d.nii.gz")
    warped_p = str(tmp_path / "warped_4d.nii.gz")
    nib.save(nib.Nifti1Image(fixed, affine), fixed_p)
    nib.save(nib.Nifti1Image(warped, affine), warped_p)

    out_metrics = str(tmp_path / "metrics_4d.tsv")
    out_png = str(tmp_path / "overlay_4d.png")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_registration.py",
            "--meta_id",
            "sub-4d_ses-1",
            "--stage",
            "t1_to_baseline",
            "--fixed",
            fixed_p,
            "--moving_warped",
            warped_p,
            "--out_metrics",
            out_metrics,
            "--out_png",
            out_png,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    assert os.path.isfile(out_png)
    assert os.path.getsize(out_png) > 1000


def test_screenshot_4d_singleton_and_mismatched_shape(tmp_path):
    """Test screenshot generation with 4D singleton anatomical and mismatched mask."""
    affine = np.eye(4)
    anat = np.random.RandomState(44).rand(20, 20, 20, 1).astype(np.float32)
    mask = np.zeros((20, 20, 22), dtype=np.uint8)
    mask[8:12, 8:12, 8:12] = 1

    anat_p = str(tmp_path / "anat_4d.nii.gz")
    mask_p = str(tmp_path / "mask_mismatched.nii.gz")
    nib.save(nib.Nifti1Image(anat, affine), anat_p)
    nib.save(nib.Nifti1Image(mask, affine), mask_p)

    out_png = str(tmp_path / "screenshot_robust.png")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_lesion_screenshot.py",
            "--meta_id",
            "sub-robust_ses-1",
            "--anat",
            anat_p,
            "--mask",
            mask_p,
            "--out_png",
            out_png,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    assert os.path.isfile(out_png)
    assert os.path.getsize(out_png) > 1000


def test_longitudinal_empty_csv(tmp_path):
    """Test that a completely empty (0-byte) CSV file is handled gracefully."""
    csv_path = str(tmp_path / "sub-empty_tracking.csv")
    with open(csv_path, "w") as f:
        pass  # 0 bytes

    out_sum = str(tmp_path / "empty_summary.tsv")
    out_traj = str(tmp_path / "empty_traj.tsv")
    out_inst = str(tmp_path / "empty_inst.tsv")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_longitudinal_summary.py",
            "--subject",
            "sub-empty",
            "--audit_csv",
            csv_path,
            "--out_summary",
            out_sum,
            "--out_trajectories",
            out_traj,
            "--out_instances",
            out_inst,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    df_sum = pd.read_csv(out_sum, sep="\t", comment="#")
    assert df_sum["No_Lesions_Flag"].iloc[0] == 1
    assert df_sum["Baseline_TLV_mL"].iloc[0] == 0.0
    assert df_sum["Followup_TLV_mL"].iloc[0] == 0.0


def test_ensemble_metrics_las_orientation(tmp_path):
    """Test that masks in LAS orientation are reoriented to RAS and match consensus Dice."""
    ras_affine = np.diag([1.0, 1.0, 1.0, 1.0])
    las_affine = np.diag([-1.0, 1.0, 1.0, 1.0])

    # Consensus in RAS: lesion in voxels x: 5..15 (size 10x10x10)
    cons = np.zeros((30, 30, 30), dtype=np.uint8)
    cons[5:15, 5:15, 5:15] = 1
    cons_path = str(tmp_path / "sub-ori_ses-1_staple_thr90_binary.nii.gz")
    nib.save(nib.Nifti1Image(cons, ras_affine), cons_path)

    # Algorithm mask in LAS with identical physical location:
    # Under LAS, x is flipped (index 30 - 1 - x in voxel space).
    # Reorienting to RAS will align them.
    mask_las = np.zeros((30, 30, 30), dtype=np.uint8)
    mask_las[30 - 15 : 30 - 5, 5:15, 5:15] = 1
    mask_path = str(tmp_path / "sub-ori_ses-1_algo_binary.nii.gz")
    nib.save(nib.Nifti1Image(mask_las, las_affine), mask_path)

    out_vol = str(tmp_path / "ori_vol.tsv")
    out_dice = str(tmp_path / "ori_dice.tsv")
    out_sum = str(tmp_path / "ori_sum.tsv")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_ensemble_metrics.py",
            "--meta_id",
            "sub-ori_ses-1",
            "--consensus",
            cons_path,
            "--masks",
            mask_path,
            "--out_volumes",
            out_vol,
            "--out_dice",
            out_dice,
            "--out_summary",
            out_sum,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    df_vol = pd.read_csv(out_vol, sep="\t", comment="#")
    assert df_vol["STAPLE_Consensus"].iloc[0] == pytest.approx(1.000, rel=1e-2)
    assert df_vol["algo"].iloc[0] == pytest.approx(1.000, rel=1e-2)
    df_sum = pd.read_csv(out_sum, sep="\t", comment="#")
    assert df_sum["Mean_Inter_Algo_Dice"].iloc[0] == 1.0


def test_screenshot_2d_input(tmp_path):
    """Test that 2D NIfTIs are handled gracefully without raising IndexError."""
    affine = np.eye(4)
    anat = np.random.RandomState(42).rand(20, 20).astype(np.float32)
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[5:15, 5:15] = 1

    anat_p = str(tmp_path / "anat_2d.nii.gz")
    mask_p = str(tmp_path / "mask_2d.nii.gz")
    nib.save(nib.Nifti1Image(anat, affine), anat_p)
    nib.save(nib.Nifti1Image(mask, affine), mask_p)

    out_png = str(tmp_path / "screenshot_2d.png")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_lesion_screenshot.py",
            "--meta_id",
            "sub-2d_ses-1",
            "--anat",
            anat_p,
            "--mask",
            mask_p,
            "--out_png",
            out_png,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    assert os.path.isfile(out_png)
    assert os.path.getsize(out_png) > 1000


def test_registration_scientific_notation(tmp_path):
    """Test that ANTs metric values in scientific notation are parsed correctly."""
    affine = np.eye(4)
    fixed = np.ones((10, 10, 10), dtype=np.float32)
    warped = np.ones((10, 10, 10), dtype=np.float32)
    fixed_p = str(tmp_path / "fixed_sci.nii.gz")
    warped_p = str(tmp_path / "warped_sci.nii.gz")
    nib.save(nib.Nifti1Image(fixed, affine), fixed_p)
    nib.save(nib.Nifti1Image(warped, affine), warped_p)

    log_p = str(tmp_path / "ants_sci.log")
    with open(log_p, "w") as f:
        f.write("DIAGNOSTIC,iteration,10,metricValue,-1.2345e-02\n")

    out_metrics = str(tmp_path / "metrics_sci.tsv")
    out_png = str(tmp_path / "overlay_sci.png")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_registration.py",
            "--meta_id",
            "sub-sci_ses-1",
            "--stage",
            "flair_to_t1",
            "--fixed",
            fixed_p,
            "--moving_warped",
            warped_p,
            "--log",
            log_p,
            "--out_metrics",
            out_metrics,
            "--out_png",
            out_png,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    df = pd.read_csv(out_metrics, sep="\t", comment="#")
    assert df["Final_Metric_Value"].iloc[0] == pytest.approx(-0.0123, abs=1e-4)


def test_longitudinal_zero_lesions_instance_table(tmp_path):
    """Test that zero-lesion audit CSV produces a valid instance table with placeholder row."""
    csv_path = str(tmp_path / "sub-zero_tracking.csv")
    df = pd.DataFrame(
        {
            "Lesion_ID": [],
            "Vol_mm3_ses-1": [],
            "Status": [],
            "Delta_Vol_mm3": [],
            "Pct_Change": [],
            "Centroid_X_mm": [],
            "Centroid_Y_mm": [],
            "Centroid_Z_mm": [],
        }
    )
    df.to_csv(csv_path, index=False)

    out_sum = str(tmp_path / "zero_summary.tsv")
    out_traj = str(tmp_path / "zero_traj.tsv")
    out_inst = str(tmp_path / "sub-zero_lesion_instances_mqc.tsv")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_longitudinal_summary.py",
            "--subject",
            "sub-zero",
            "--audit_csv",
            csv_path,
            "--out_summary",
            out_sum,
            "--out_trajectories",
            out_traj,
            "--out_instances",
            out_inst,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    df_inst = pd.read_csv(out_inst, sep="\t", comment="#", keep_default_na=False)
    assert len(df_inst) == 1
    assert str(df_inst["Lesion_ID"].iloc[0]) == "None"
    assert df_inst["Status"].iloc[0] == "No lesions detected"


def test_registration_2d_input(tmp_path):
    """Test that 2D NIfTIs are handled gracefully by qc_registration.py without raising IndexError."""
    affine = np.eye(4)
    fixed = np.random.RandomState(42).rand(20, 20).astype(np.float32)
    warped = np.random.RandomState(43).rand(20, 20).astype(np.float32)

    fixed_p = str(tmp_path / "fixed_2d.nii.gz")
    warped_p = str(tmp_path / "warped_2d.nii.gz")
    nib.save(nib.Nifti1Image(fixed, affine), fixed_p)
    nib.save(nib.Nifti1Image(warped, affine), warped_p)

    out_metrics = str(tmp_path / "metrics_2d.tsv")
    out_png = str(tmp_path / "overlay_2d.png")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_registration.py",
            "--meta_id",
            "sub-2d_ses-1",
            "--stage",
            "flair_to_t1",
            "--fixed",
            fixed_p,
            "--moving_warped",
            warped_p,
            "--out_metrics",
            out_metrics,
            "--out_png",
            out_png,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    assert os.path.isfile(out_png)
    assert os.path.getsize(out_png) > 1000


def test_registration_4d_multichannel(tmp_path):
    """Test that 4D multi-channel NIfTIs are clamped to 3D without raising TypeError."""
    affine = np.eye(4)
    fixed = np.random.RandomState(42).rand(20, 20, 20, 2).astype(np.float32)
    warped = np.random.RandomState(43).rand(20, 20, 20, 2).astype(np.float32)

    fixed_p = str(tmp_path / "fixed_4d_multi.nii.gz")
    warped_p = str(tmp_path / "warped_4d_multi.nii.gz")
    nib.save(nib.Nifti1Image(fixed, affine), fixed_p)
    nib.save(nib.Nifti1Image(warped, affine), warped_p)

    out_metrics = str(tmp_path / "metrics_4d_multi.tsv")
    out_png = str(tmp_path / "overlay_4d_multi.png")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_registration.py",
            "--meta_id",
            "sub-4d_multi_ses-1",
            "--stage",
            "baseline_to_mni",
            "--fixed",
            fixed_p,
            "--moving_warped",
            warped_p,
            "--out_metrics",
            out_metrics,
            "--out_png",
            out_png,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    assert os.path.isfile(out_png)
    assert os.path.getsize(out_png) > 1000


def test_ensemble_metrics_4d_multichannel(tmp_path):
    """Test that 4D multi-channel consensus and algorithm masks are clamped to 3D."""
    affine = np.eye(4)
    cons = np.zeros((20, 20, 20, 2), dtype=np.uint8)
    cons[5:15, 5:15, 5:15, 0] = 1
    cons_p = str(tmp_path / "sub-4d_ses-1_staple_thr90_binary.nii.gz")
    nib.save(nib.Nifti1Image(cons, affine), cons_p)

    m = np.zeros((20, 20, 20, 2), dtype=np.uint8)
    m[5:15, 5:15, 5:15, 0] = 1
    m_p = str(tmp_path / "sub-4d_ses-1_lst_ai_binary.nii.gz")
    nib.save(nib.Nifti1Image(m, affine), m_p)

    out_vol = str(tmp_path / "vol_4d.tsv")
    out_dice = str(tmp_path / "dice_4d.tsv")
    out_sum = str(tmp_path / "sum_4d.tsv")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_ensemble_metrics.py",
            "--meta_id",
            "sub-4d_ses-1",
            "--consensus",
            cons_p,
            "--masks",
            m_p,
            "--out_volumes",
            out_vol,
            "--out_dice",
            out_dice,
            "--out_summary",
            out_sum,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    df_vol = pd.read_csv(out_vol, sep="\t", comment="#")
    assert df_vol["STAPLE_Consensus"].iloc[0] == pytest.approx(1.000, rel=1e-2)
    assert df_vol["lst_ai"].iloc[0] == pytest.approx(1.000, rel=1e-2)
    df_sum = pd.read_csv(out_sum, sep="\t", comment="#")
    assert df_sum["Mean_Inter_Algo_Dice"].iloc[0] == 1.0


def test_ensemble_metrics_2d_input(tmp_path):
    """Test that 2D consensus and algorithm masks are clamped to 3D and compute Dice accurately."""
    affine = np.eye(4)
    cons = np.zeros((20, 20), dtype=np.uint8)
    cons[5:15, 5:15] = 1
    cons_p = str(tmp_path / "sub-2d_ses-1_staple_thr90_binary.nii.gz")
    nib.save(nib.Nifti1Image(cons, affine), cons_p)

    m = np.zeros((20, 20), dtype=np.uint8)
    m[5:15, 5:15] = 1
    m_p = str(tmp_path / "sub-2d_ses-1_algo_binary.nii.gz")
    nib.save(nib.Nifti1Image(m, affine), m_p)

    out_vol = str(tmp_path / "vol_2d.tsv")
    out_dice = str(tmp_path / "dice_2d.tsv")
    out_sum = str(tmp_path / "sum_2d.tsv")

    ret = subprocess.run(
        [
            sys.executable,
            "bin/qc_ensemble_metrics.py",
            "--meta_id",
            "sub-2d_ses-1",
            "--consensus",
            cons_p,
            "--masks",
            m_p,
            "--out_volumes",
            out_vol,
            "--out_dice",
            out_dice,
            "--out_summary",
            out_sum,
        ],
        capture_output=True,
    )
    assert ret.returncode == 0, ret.stderr.decode()
    df_sum = pd.read_csv(out_sum, sep="\t", comment="#")
    assert df_sum["Mean_Inter_Algo_Dice"].iloc[0] == 1.0
    assert df_sum["Consensus_Lesion_Count"].iloc[0] == 1




