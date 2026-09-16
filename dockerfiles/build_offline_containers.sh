#!/usr/bin/env bash
# Build a complete offline Apptainer/Singularity container cache for sf-lesionflow
# (e.g. for Alliance Canada, whose compute nodes have no internet access).
#
# All sf-lesionflow-specific containers are now published on DockerHub under
# frheault/sf-lesionflow-<algo>:<version> and are pulled in Phase 2 below
# alongside the other public images.
#
# Phase 1 (docker-daemon://) is kept as a developer convenience: if you have
# modified a container locally and want to bake the modified image into a .sif
# *without* first pushing to DockerHub, run this script on a machine that has
# Docker and the images already built. The resulting .sif files are named to
# match the explicit `container` overrides in conf/offline.config; keep the
# two in sync if you add/rename a container.  An HPC login node (no Docker
# daemon) will skip Phase 1 automatically.
#
# Phase 2 pulls all containers straight from their public registries
# (docker://) into Nextflow's normal apptainer/singularity cache-file naming
# convention, so no conf/offline.config override is needed. This phase only
# needs `apptainer` (or `singularity`) and internet access -- it works fine
# on an HPC login node, without Docker.
#
# Run with no Docker daemon reachable to fetch ONLY the public containers;
# run on a machine with Docker and locally-modified images to rebuild without
# pushing first.
#
# Usage: dockerfiles/build_offline_containers.sh [output_dir]
#   output_dir defaults to ./singularity_cache_offline
#   Point --sif_cache (or NXF_APPTAINER_CACHEDIR/NXF_SINGULARITY_CACHEDIR)
#   at output_dir once it's transferred to the cluster.

set -euo pipefail

OUT_DIR="${1:-./singularity_cache_offline}"
mkdir -p "$OUT_DIR"
OUT_DIR=$(realpath "$OUT_DIR")

if ! command -v apptainer &> /dev/null && ! command -v singularity &> /dev/null; then
    echo "Error: neither apptainer nor singularity is installed or in PATH" >&2
    exit 1
fi
BUILD_CMD=$(command -v apptainer &> /dev/null && echo apptainer || echo singularity)

echo "Output directory: $OUT_DIR"
echo "Build tool:       $BUILD_CMD"
echo ""

FAILED=0

# Helper: print elapsed seconds since a given epoch second.
elapsed() { echo "$(( $(date +%s) - $1 ))s"; }

# Helper: print a progress header.
# Usage: progress_header <current> <total> <label>
progress_header() {
    local cur=$1 tot=$2 label=$3
    printf "\n[%d/%d] %s\n" "$cur" "$tot" "$label"
    printf '%*s\n' "${#label}" '' | tr ' ' '-'
}

# -----------------------------------------------------------------------------
# Phase 1: developer override — locally-modified images (docker-daemon:// source)
# Use this ONLY if you have modified a container locally and do NOT want to
# push to DockerHub first. The .sif names here match conf/offline.config so
# Nextflow will pick them up over the public DockerHub pull done in Phase 2.
# sif_name:local_docker_image -- keep in sync with conf/offline.config
# -----------------------------------------------------------------------------
LOCAL_IMAGES=(
    "lst_ai.sif:frheault/sf-lesionflow-lst_ai:1.1.0"
    "wmh_synthseg.sif:frheault/sf-lesionflow-wmh_synthseg:1.0.0"
    "fast_outlier.sif:frheault/sf-lesionflow-fast_outlier:1.0.0"
    "flames.sif:frheault/sf-lesionflow-flames:1.0.0"
    "truenet.sif:frheault/sf-lesionflow-truenet:1.0.0"
    "bawil.sif:frheault/sf-lesionflow-bawil:1.0.0"
    "mimosa.sif:frheault/sf-lesionflow-mimosa:1.0.0"
    "shivai.sif:frheault/sf-lesionflow-shivai:1.0.0"
    "segcsvd.sif:frheault/sf-lesionflow-segcsvd:rc03"
)

if docker info &> /dev/null; then
    total=${#LOCAL_IMAGES[@]}
    echo "=== Phase 1: local dev-override containers (docker-daemon://) — ${total} images ==="
    echo "(any image not found locally is skipped here and pulled from DockerHub in Phase 2 instead)"
    idx=0
    for entry in "${LOCAL_IMAGES[@]}"; do
        idx=$(( idx + 1 ))
        sif_name="${entry%%:*}"
        docker_image="${entry#*:}"
        out_file="$OUT_DIR/$sif_name"

        progress_header "$idx" "$total" "$sif_name"

        if [ -f "$out_file" ]; then
            echo "  ✓ Already exists — skipping ($(du -sh "$out_file" | cut -f1))"
            continue
        fi

        if ! docker image inspect "$docker_image" &> /dev/null; then
            echo "  ✗ Docker image '$docker_image' not found locally — skipping" >&2
            echo "    (Phase 2 will pull frheault/${sif_name%.sif} from DockerHub instead)" >&2
            continue
        fi

        echo "  Converting docker-daemon://$docker_image → $sif_name ..."
        t0=$(date +%s)
        if "$BUILD_CMD" build --force "$out_file" "docker-daemon://$docker_image"; then
            echo "  ✓ Done in $(elapsed $t0) — $(du -sh "$out_file" | cut -f1)"
        else
            echo "  ✗ FAILED after $(elapsed $t0)" >&2
            FAILED=1
        fi
    done
else
    echo "=== Phase 1 skipped: no Docker daemon reachable here ==="
    echo "(all sf-lesionflow containers are on DockerHub — Phase 2 will pull them)"
    echo ""
fi

# -----------------------------------------------------------------------------
# Phase 2: public registry images (docker:// source)
# Named using Nextflow's own apptainer/singularity cache-file convention, so
# they are found automatically -- no conf/offline.config entry needed.
#
# *** ADD NEW PUBLIC CONTAINERS HERE — keep sorted by purpose ***
# -----------------------------------------------------------------------------
PUBLIC_IMAGES=(
    # --- sf-lesionflow custom containers (DockerHub: frheault/) ---
    "frheault/sf-lesionflow-lst_ai:1.1.0"
    "frheault/sf-lesionflow-wmh_synthseg:1.0.0"
    "frheault/sf-lesionflow-fast_outlier:1.0.0"
    "frheault/sf-lesionflow-flames:1.0.0"
    "frheault/sf-lesionflow-truenet:1.0.0"
    "frheault/sf-lesionflow-bawil:1.0.0"
    "frheault/sf-lesionflow-mimosa:1.0.0"
    "frheault/sf-lesionflow-shivai:1.0.0"
    "frheault/sf-lesionflow-segcsvd:rc03"
    # --- nf-neuro standard modules ---
    "scilus/scilpy:2.2.2_cpu"
    "scilus/scilus:2.2.2"
    "mrtrix3/mrtrix3:3.0.5"
    # --- Segmentation algorithms (public registries) ---
    "freesurfer/freesurfer:7.4.1"
    "freesurfer/synthstrip:1.8"
    "freesurfer/synthstrip:1.8-gpu"
    "mgoubran/hypermapper:latest"
    "emorycn2l/emory_robust_wmh:v1.2"
    "ghcr.io/miac-research/wmh-nnunet:latest"
    # --- QC & Reporting ---
    # multiqc-neuroimaging provides MultiQC >= 1.25 plus the custom
    # --single-subject-report flag required by the QC_PIPELINE subworkflow.
    # Keep this version pinned in sync with modules/local/qc_multiqc.nf.
    "gagnonanthony/multiqc-neuroimaging:0.1.4"
)

total=${#PUBLIC_IMAGES[@]}
echo ""
echo "=== Phase 2: public containers (docker://) — ${total} images ==="
idx=0
for docker_image in "${PUBLIC_IMAGES[@]}"; do
    idx=$(( idx + 1 ))

    # Same sanitization Nextflow itself applies: prefix docker.io/ when no
    # registry domain is present, then replace / and : with -.
    if [[ "$docker_image" =~ ^[^/]+\.[^/]+/ ]]; then
        clean_image="$docker_image"
    else
        clean_image="docker.io/$docker_image"
    fi
    cache_name=$(echo "$clean_image" | sed 's|/|-|g; s|:|-|g')
    out_file="$OUT_DIR/${cache_name}.img"

    progress_header "$idx" "$total" "$docker_image"

    if [ -f "$out_file" ]; then
        echo "  ✓ Already exists — skipping ($(du -sh "$out_file" | cut -f1))"
        continue
    fi

    echo "  Pulling docker://$docker_image ..."
    echo "  (apptainer/singularity will stream layer progress below)"
    t0=$(date +%s)
    if "$BUILD_CMD" pull --disable-cache "$out_file" "docker://$docker_image"; then
        echo "  ✓ Done in $(elapsed $t0) — $(du -sh "$out_file" | cut -f1)"
    else
        echo "  ✗ FAILED after $(elapsed $t0)" >&2
        FAILED=1
    fi
done

echo ""
if [ $FAILED -eq 0 ]; then
    echo "════════════════════════════════════════════════════════════════"
    echo "  All offline containers are ready in $OUT_DIR"
    echo "  Transfer this directory to the cluster, then:"
    echo "    export NXF_APPTAINER_CACHEDIR=$OUT_DIR"
    echo "    nextflow run main.nf ... -profile ...,offline"
    echo "════════════════════════════════════════════════════════════════"
else
    echo "One or more containers failed — see ✗ messages above." >&2
    exit 1
fi

