#!/bin/bash
# Full end-to-end run (all subjects in data/, default algorithms), strictly one task
# at a time, then validation of every output. Resumes from any finished tasks.
#
# Launch it detached so it survives closing the terminal:
#   tmux new -s lesionflow ./cmd.sh        # detach: Ctrl-b d   reattach: tmux attach -t lesionflow
set -uo pipefail
cd "$(dirname "$0")"

# Output directory. results_v2: the output layout changed on 2026-09-30 (conf/output.config);
# never publish the new layout into an old results/ tree.
OUT="${OUT:-results_v2}"

if pgrep -f "[n]extflow.cli.Launcher" >/dev/null; then
    echo "Error: a Nextflow run is already active on this host -- stop it first." >&2
    exit 1
fi

nextflow run main.nf --input data \
    --mni_template template/mni_masked.nii.gz \
    --fs_license /home/local/USHERBROOKE/rhef1902/Libraries/freesurfer/license.txt \
    --output "$OUT" \
    -profile docker,local_dev,no_parallel \
    -resume 2>&1 | tee run_full.log
nf_status=${PIPESTATUS[0]}
echo "NEXTFLOW EXIT ${nf_status}" | tee -a run_full.log

python3 tests/validate_outputs.py "$OUT" --input data 2>&1 | tee validate_full.log
val_status=${PIPESTATUS[0]}
echo "VALIDATE EXIT ${val_status}" | tee -a validate_full.log

exit $(( nf_status != 0 ? nf_status : val_status ))
