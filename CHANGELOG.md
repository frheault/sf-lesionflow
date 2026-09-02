# Changelog

All notable changes to the `sf-lesionflow` pipeline will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-02

### Added
- **DSL2 Pipeline Architecture**: Modular 5-phase DAG covering BIDS input parsing, nf-neuro isotropic resampling, SynthStrip brain extraction, N4 bias correction, ANTs registrations, and composite MNI warping.
- **13-Algorithm Segmentation Ensemble**: Integrated containerized pipelines for LST-AI, SAMSEG, WMH-SynthSeg, FAST Outlier, FLAMeS, TrueNet, HyperMapp3r, SegCSVD, Emory Robust WMH, MARS-WMH, BAWIL, MIMoSA, and SHiVAi.
- **STAPLE Consensus Fusion**: Implementation of expectation-maximization probability maps, 90% thresholding, $\ge 6\text{ mm}^3$ connected component filtering, and distance-transform watershed instance labeling (`CONSENSUS_STAPLE`).
- **4D Longitudinal Harmonization**: Spatiotemporal union tracking across sessions with automated lesion trajectory classification (`HARMONIZATION_STAPLE`).
- **Modular Python CLI Tools**: Extracted standalone scripts with `argparse` into `bin/` (`fast_outlier.py`, `conform_synthseg.py`, `bawil_filter.py`, `mimosa_filter.py`, `shivai_filter.py`, `staple_consensus.py`, `harmonize_staple.py`, `export_results.py`).
- **Comprehensive Documentation**: Added `README.md`, `CITATIONS.md`, `CODE_REVIEW_AND_PLAN.md`, and `LICENSE`.

### Changed
- **Container Hardening**: Configured `--entrypoint ""` globally and `-u 0:0` on root-requiring images.
- **Resource Management**: Implemented `maxForks = 2` on memory-heavy processes (`SAMSEG`, `WMH-SynthSeg`, `Emory Robust WMH`) and dynamic memory retries.
- **DSL Cleanup**: Removed obsolete `nextflow.enable.dsl=2`, centralized versioning to `manifest.version`, and added hard Nextflow version pin (`!>=24.04.0`).
