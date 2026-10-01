#!/usr/bin/env bash
# Print nf-core style versions YAML for one algorithm, probed from INSIDE its own container.
# Usage: probe_versions.sh <algo> <process_name> <container_image>
# Never prints a made-up number: anything that cannot be probed is reported as "unknown".
set -u
algo="$1"; proc="$2"; image="$3"

py() {  # first python interpreter available in the image
    for p in python3 python fspython; do command -v "$p" >/dev/null 2>&1 && { echo "$p"; return; }; done
    [ -x "${FREESURFER_HOME:-/usr/local/freesurfer}/python/bin/python3" ] && echo "${FREESURFER_HOME:-/usr/local/freesurfer}/python/bin/python3"
}
PY="$(py)"

pkg() {  # pkg <distribution-name>... -> version of the first installed one, or "unknown"
    [ -z "$PY" ] && { echo unknown; return; }
    "$PY" - "$@" 2>/dev/null <<'EOF' || echo unknown
import sys
try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    from pkg_resources import get_distribution as _gd
    def version(n): return _gd(n).version
    PackageNotFoundError = Exception
for name in sys.argv[1:]:
    try:
        print(version(name)); break
    except PackageNotFoundError:
        continue
    except Exception:
        continue
else:
    print("unknown")
EOF
}

fs_build() {  # FreeSurfer build stamp
    local f="${FREESURFER_HOME:-/usr/local/freesurfer}/build-stamp.txt"
    [ -s "$f" ] && head -1 "$f" || echo unknown
}

sha_short() {  # sha256 (12 chars) of the first existing file among the arguments
    for f in "$@"; do
        [ -f "$f" ] && { sha256sum "$f" 2>/dev/null | cut -c1-12; return; }
    done
    echo unknown
}

rpkg() {
    command -v Rscript >/dev/null 2>&1 || { echo unknown; return; }
    Rscript -e "cat(as.character(packageVersion('$1')))" 2>/dev/null || echo unknown
}

declare -a lines
add() { lines+=("    $1: \"$2\""); }

add container "$image"
case "$algo" in
    lst_ai)
        add lst_ai "$(pkg LST-AI lst_ai lst-ai)"
        add tensorflow "$(pkg tensorflow tensorflow-cpu)"
        add torch "$(pkg torch)" ;;
    samseg | synthseg)
        add freesurfer "$(fs_build)" ;;
    wmh_synthseg)
        add freesurfer "$(fs_build)"
        add torch "$(pkg torch)"
        add wmh_synthseg_model_sha256 "$(sha_short "${FREESURFER_HOME:-/usr/local/freesurfer}"/models/WMH-SynthSeg_v10_231110.pth "${FREESURFER_HOME:-/usr/local/freesurfer}"/models/WMH-SynthSeg*.pth)" ;;
    fast_outlier)
        add fsl "$(cat "${FSLDIR:-/usr/local/fsl}"/etc/fslversion 2>/dev/null | head -1 || echo unknown)" ;;
    flames)
        add nnunetv2 "$(pkg nnunetv2)"
        add torch "$(pkg torch)" ;;
    truenet)
        add truenet "$(pkg truenet)"
        add fsl "$(cat "${FSLDIR:-/usr/local/fsl}"/etc/fslversion 2>/dev/null | head -1 || echo unknown)"
        add torch "$(pkg torch)" ;;
    hypermapp3r)
        add hypermapp3r "$(pkg hypermapp3r hypermapper)"
        add tensorflow "$(pkg tensorflow tensorflow-gpu)" ;;
    segcsvd)
        add segcsvd_release "rc03"
        add wmh_weights_sha256 "$(find /seg/weights/wmh -type f 2>/dev/null | sort | xargs -r cat 2>/dev/null | sha256sum | cut -c1-12)"
        add torch "$(pkg torch)" ;;
    emory_robust)
        [ -x /opt/conda/envs/nnunet/bin/python ] && PY=/opt/conda/envs/nnunet/bin/python
        add nnunetv2 "$(pkg nnunetv2)"
        add torch "$(pkg torch)" ;;
    mars_wmh)
        add nnunet "$(pkg nnunetv2 nnunet)"
        add torch "$(pkg torch)" ;;
    bawil)
        add bawil_weights_sha256 "$(sha_short /opt/bawil/scenario2_multiclass_model.h5)"
        add tensorflow "$(pkg tensorflow)"
        add opencv "$(pkg opencv-python-headless opencv-python)"
        add nibabel "$(pkg nibabel)" ;;
    mimosa)
        add mimosa "$(rpkg mimosa)"
        add R "$(Rscript -e 'cat(paste(R.version$major, R.version$minor, sep="."))' 2>/dev/null || echo unknown)" ;;
    shivai)
        add tensorflow "$(pkg tensorflow tensorflow-cpu)"
        add nibabel "$(pkg nibabel)" ;;
    mindglide)
        add monai "$(pkg monai)"
        add torch "$(pkg torch)" ;;
    *)
        add python "$($PY --version 2>&1 | awk '{print $2}')" ;;
esac
[ -n "$PY" ] && add python "$($PY --version 2>&1 | awk '{print $2}')"

echo "\"${proc}\":"
printf '%s\n' "${lines[@]}"
