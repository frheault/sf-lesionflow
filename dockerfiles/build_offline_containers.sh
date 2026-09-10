#!/usr/bin/env bash
# Build a complete offline Apptainer/Singularity container cache for sf-lesionflow
# (e.g. for Alliance Canada, whose compute nodes have no internet access).
#
# Two kinds of containers are handled:
#
#   1. Nine images (ms_chus/* and segcsvd_rc03) were built locally from
#      dockerfiles/<algo>/ and never pushed to any registry -- there is
#      nothing for `apptainer pull` to fetch. They are converted straight
#      from the local Docker daemon (docker-daemon://) and named to match
#      the explicit `container` overrides in conf/offline.config; keep the
#      two in sync if you add/rename a container. This phase needs to run
#      on a machine that has Docker AND these images already built (an HPC
#      login node cannot do this -- it has no Docker daemon to convert
#      from).
#
#   2. The remaining containers (freesurfer/freesurfer, mgoubran/hypermapper,
#      emorycn2l/emory_robust_wmh, ghcr.io/miac-research/wmh-nnunet, and the
#      nf-neuro modules' scilus/scilpy, scilus/scilus, mrtrix3/mrtrix3,
#      freesurfer/synthstrip:1.8 and :1.8-gpu) are public and are pulled
#      straight from their registry (docker://) into Nextflow's normal
#      apptainer/singularity cache-file naming convention, so no config
#      override is needed for them. This phase only needs `apptainer` (or
#      `singularity`) and internet access -- it works fine on an HPC login
#      node too, without Docker.
#
# Run with no Docker daemon reachable to fetch ONLY the public containers
# (e.g. from a cluster login node); run on a machine with both Docker and
# these images built to fetch everything in one pass.
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
echo "Build tool: $BUILD_CMD"
echo ""

FAILED=0

# -----------------------------------------------------------------------------
# Phase 1: locally-built-only images (docker-daemon:// source)
# sif_name:docker_image -- keep in sync with conf/offline.config
# -----------------------------------------------------------------------------
LOCAL_IMAGES=(
    "lst_ai.sif:ms_chus/lst_ai:latest"
    "wmh_synthseg.sif:ms_chus/wmh_synthseg:latest"
    "fast_outlier.sif:ms_chus/fast_outlier:latest"
    "flames.sif:ms_chus/flames:latest"
    "truenet.sif:ms_chus/truenet:latest"
    "bawil.sif:ms_chus/bawil:latest"
    "mimosa.sif:ms_chus/mimosa:latest"
    "shivai.sif:ms_chus/shivai:latest"
    "segcsvd.sif:segcsvd_rc03:latest"
)

if docker info &> /dev/null; then
    echo "=== Phase 1: locally-built containers (docker-daemon://) ==="
    for entry in "${LOCAL_IMAGES[@]}"; do
        sif_name="${entry%%:*}"
        docker_image="${entry#*:}"
        out_file="$OUT_DIR/$sif_name"

        if [ -f "$out_file" ]; then
            echo "Skipping $sif_name (already exists)"
            continue
        fi

        if ! docker image inspect "$docker_image" &> /dev/null; then
            echo "Skipping $sif_name: Docker image '$docker_image' not found locally" \
                 "(see dockerfiles/<algo>/README.md to build it)" >&2
            FAILED=1
            continue
        fi

        echo "Building $sif_name from docker-daemon://$docker_image ..."
        if "$BUILD_CMD" build --force "$out_file" "docker-daemon://$docker_image"; then
            echo "Done: $out_file"
        else
            echo "Failed: $sif_name" >&2
            FAILED=1
        fi
        echo ""
    done
else
    echo "=== Phase 1 skipped: no Docker daemon reachable here ==="
    echo "(run this script on the workstation where the ms_chus/* and segcsvd_rc03"
    echo " images were built to fetch those nine; continuing with public images)"
    echo ""
fi

# -----------------------------------------------------------------------------
# Phase 2: public registry images (docker:// source)
# Named using Nextflow's own apptainer/singularity cache-file convention, so
# they are found automatically -- no conf/offline.config entry needed.
# -----------------------------------------------------------------------------
PUBLIC_IMAGES=(
    "freesurfer/freesurfer:7.4.1"
    "mgoubran/hypermapper:latest"
    "emorycn2l/emory_robust_wmh:v1.2"
    "ghcr.io/miac-research/wmh-nnunet:latest"
    "scilus/scilpy:2.2.2_cpu"
    "scilus/scilus:2.2.2"
    "mrtrix3/mrtrix3:3.0.5"
    "freesurfer/synthstrip:1.8"
    "freesurfer/synthstrip:1.8-gpu"
)

echo "=== Phase 2: public containers (docker://) ==="
for docker_image in "${PUBLIC_IMAGES[@]}"; do
    # Same sanitization Nextflow itself applies: prefix docker.io/ when no
    # registry domain is present, then replace / and : with -.
    if [[ "$docker_image" =~ ^[^/]+\.[^/]+/ ]]; then
        clean_image="$docker_image"
    else
        clean_image="docker.io/$docker_image"
    fi
    cache_name=$(echo "$clean_image" | sed 's|/|-|g; s|:|-|g')
    out_file="$OUT_DIR/${cache_name}.img"

    if [ -f "$out_file" ]; then
        echo "Skipping $cache_name (already exists)"
        continue
    fi

    echo "Pulling docker://$docker_image ..."
    if "$BUILD_CMD" pull --disable-cache "$out_file" "docker://$docker_image"; then
        echo "Done: $out_file"
    else
        echo "Failed: $cache_name" >&2
        FAILED=1
    fi
    echo ""
done

if [ $FAILED -eq 0 ]; then
    echo "All offline containers are ready in $OUT_DIR"
    echo "Transfer this directory to the cluster (e.g. /project/<def-group>/sf-lesionflow_sif)"
    echo "and export NXF_APPTAINER_CACHEDIR / NXF_SINGULARITY_CACHEDIR (or pass --sif_cache)"
    echo "together with -profile ...,offline"
else
    echo "One or more containers failed -- see messages above." >&2
    exit 1
fi
