# Standalone CLI Tools (`bin/`)

This directory contains standalone Python CLI scripts following the `nf-core` / `nf-junction_atlas` architecture. Each tool uses standard `argparse`, supports `--help`, and exposes algorithmic parameters directly to Nextflow via `task.ext.*` directives.

In containerized pipeline runs (`-profile docker` / `-profile singularity`), dependencies are provided by the respective container environment. For local development or testing, install the dependencies listed in `requirements.txt`.

---

## Tool Reference & Dependency Matrix

| Script | Purpose | Dependencies | Calling Nextflow Process | Container Image |
|---|---|---|---|---|
| **`create_nonzero_mask.py`** | Creates binary mask from non-zero voxels ($x > 0$) | `numpy`, `nibabel` | `SEGMENTATION_HYPERMAPP3R`<br>`SEGMENTATION_SEGCSVD` | `mgoubran/hypermapper:latest`<br>`segcsvd_rc03:latest` |
| **`threshold_probmap.py`** | Thresholds probability maps ($\ge \tau$) into binary masks | `numpy`, `nibabel` | `SEGMENTATION_TRUENET`<br>`SEGMENTATION_HYPERMAPP3R`<br>`SEGMENTATION_SEGCSVD` | `ms_chus/truenet:latest`<br>`mgoubran/hypermapper:latest`<br>`segcsvd_rc03:latest` |
| **`fast_outlier.py`** | DWM mask generation & intensity $z$-score outlier filter | `numpy`, `nibabel` | `SEGMENTATION_FAST_OUTLIER` | `ms_chus/fast_outlier:latest` |
| **`conform_synthseg.py`** | Extracts label 77 & conforms geometry to reference | `numpy`, `nibabel`, `scipy` | `SEGMENTATION_WMH_SYNTHSEG` | `ms_chus/wmh_synthseg:latest` |
| **`bawil_filter.py`** | Gaussian-smoothed z-score lesion proxy | `numpy`, `nibabel`, `scipy` | `SEGMENTATION_BAWIL` | `ms_chus/lst_ai:latest` |
| **`mimosa_filter.py`** | Multimodal T1/FLAIR regression candidate filter | `numpy`, `nibabel`, `scipy` | `SEGMENTATION_MIMOSA` | `ms_chus/lst_ai:latest` |
| **`shivai_filter.py`** | Multi-scale contrast lesion proxy | `numpy`, `nibabel`, `scipy` | `SEGMENTATION_SHIVAI` | `ms_chus/lst_ai:latest` |
| **`staple_consensus.py`** | SimpleITK STAPLE EM fusion + watershed instance segmentation | `numpy`, `scipy`, `SimpleITK`, `scikit-image` | `CONSENSUS_STAPLE` | `segcsvd_rc03:latest` |
| **`harmonize_staple.py`** | 4D longitudinal lesion tracking & audit CSV generation | `numpy`, `scipy`, `nibabel`, `pandas`, `scikit-image` | `HARMONIZATION_STAPLE` | `segcsvd_rc03:latest` |

---

## CLI Specifications

### 1. `create_nonzero_mask.py`
```bash
create_nonzero_mask.py --input <in.nii.gz> --output <out_mask.nii.gz>
```

### 2. `threshold_probmap.py`
```bash
threshold_probmap.py --input <prob.nii.gz> --output <out_binary.nii.gz> [--threshold 0.5]
threshold_probmap.py --input_glob 'out/Predicted_*.nii.gz' --output <out_binary.nii.gz> [--threshold 0.5]
```

### 3. `fast_outlier.py`
```bash
fast_outlier.py --flair <flair.nii.gz> --wm_pve <pve_2.nii.gz> --output <out_binary.nii.gz> \
                [--sigma 2.5] [--pve_threshold 0.95] [--dwm_threshold 0.50]
```

### 4. `conform_synthseg.py`
```bash
conform_synthseg.py --input <multiclass.nii.gz> --ref <ref.nii.gz> --output <out_binary.nii.gz> [--label_id 77]
```

### 5. `bawil_filter.py`
```bash
bawil_filter.py --flair <flair.nii.gz> --output <out_binary.nii.gz> [--sigma 2.0] [--min_cluster_size 3]
```

### 6. `mimosa_filter.py`
```bash
mimosa_filter.py --t1 <t1.nii.gz> --flair <flair.nii.gz> --output <out_binary.nii.gz> \
                 [--prob_threshold 0.30] [--flair_cand_threshold 1.5] [--min_cluster_size 3]
```

### 7. `shivai_filter.py`
```bash
shivai_filter.py --t1 <t1.nii.gz> --flair <flair.nii.gz> --output <out_binary.nii.gz> \
                 [--prob_threshold 0.50] [--min_cluster_size 3]
```

### 8. `staple_consensus.py`
```bash
staple_consensus.py --ref_image <ref.nii.gz> --masks <mask1.nii.gz mask2.nii.gz ...> \
                    --out_probmap <prob.nii.gz> --out_binary <bin.nii.gz> --out_labels <labels.nii.gz> \
                    [--threshold 0.90] [--min_cluster_size 6] [--min_distance 3] [--gaussian_sigma 0.8]
```

### 9. `harmonize_staple.py`
```bash
harmonize_staple.py --subject <sub-001> --masks <ses1_mask.nii.gz ses2_mask.nii.gz ...> \
                    --out_csv <audit.csv> [--min_cluster_size 6] [--min_distance 3] \
                    [--gaussian_sigma 0.8] [--pct_change_threshold 20.0]
```
