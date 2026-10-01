#!/usr/bin/env nextflow

// -----------------------------------------------------------------------------
// Phase 2: Independent Algorithm Modules
// -----------------------------------------------------------------------------

process SEGMENTATION_LST_AI {
    tag "$meta.id"
    label 'process_gpu'
    container 'frheault/sf-lesionflow-lst_ai:1.1.0'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1), path(flair)

    output:
    tuple val(meta), path("lst_ai.nii.gz")     , emit: binary_mask
    tuple val(meta), path("lst_ai_prob.nii.gz"), emit: probability_map
    path "versions.yml"                        , emit: versions

    stub:
    """
    touch lst_ai.nii.gz
    touch lst_ai_prob.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        lst_ai: 2.0.0
    END_VERSIONS
    """

    script:
    def use_gpu = task.ext.gpu
    def device = use_gpu ? "0" : "cpu"
    """
    export CUDA_VISIBLE_DEVICES=${use_gpu ? '0' : '-1'}
    export TF_FORCE_GPU_ALLOW_GROWTH=true
    export TF_GPU_ALLOCATOR=cuda_malloc_async
    export TF_CPP_MIN_LOG_LEVEL=2
    export OMP_NUM_THREADS=${task.cpus}
    export PYTHONNOUSERSITE=1
    unset PYTHONPATH
    export TORCH_HOME="\$(pwd)/.cache/torch"
    export MPLCONFIGDIR="\$(pwd)/.cache/matplotlib"

    # lst_ai_prob.py runs the stock `lst` driver with its joint 3-model probability
    # (thresholded at --threshold and discarded upstream) additionally saved and
    # warped back to FLAIR space -- see the script's docstring.
    mkdir -p tmp_out
    lst_ai_prob.py --output_prob lst_ai_prob.nii.gz --work_dir lst_work \
        --t1 ${t1} --flair ${flair} --output tmp_out --segment_only --stripped --device ${device} --threads ${task.cpus}

    if [ -f "tmp_out/space-flair_seg-lst.nii.gz" ]; then
        mv tmp_out/space-flair_seg-lst.nii.gz lst_ai.nii.gz
    else
        echo "Error: LST-AI output missing" >&2
        exit 1
    fi
    rm -rf tmp_out lst_work

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        lst_ai: 2.0.0
    END_VERSIONS
    """
}

process SEGMENTATION_SAMSEG {
    tag "$meta.id"
    container 'freesurfer/freesurfer:7.4.1'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_unstripped_mni), path(flair_unstripped_mni), path(fs_license)

    output:
    tuple val(meta), path("${meta.id}_samseg_binary.nii.gz"), emit: binary_mask
    tuple val(meta), path("${meta.id}_samseg_prob.nii.gz")  , emit: probability_map
    path "versions.yml"                                     , emit: versions

    stub:
    """
    touch ${meta.id}_samseg_binary.nii.gz
    touch ${meta.id}_samseg_prob.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        samseg: 7.4.1
    END_VERSIONS
    """

    script:
    """
    set +u
    export FREESURFER_HOME=/usr/local/freesurfer
    export FS_LICENSE=${fs_license}
    source /usr/local/freesurfer/SetUpFreeSurfer.sh
    set -u

    # --save-posteriors takes structure-NAME substrings (Samseg.writeResults does
    # `if searchString in name`), not label numbers: "99" would match nothing and
    # silently save no posterior. Label 99's structure name is "Lesions"
    # (samseg atlas compressionLookupTable.txt), written to posteriors/Lesions.mgz.
    mkdir -p samseg_out
    run_samseg -i ${t1_unstripped_mni} -i ${flair_unstripped_mni} \
               --out samseg_out \
               --lesion \
               --lesion-mask-pattern 0 1 \
               --pallidum-separate \
               --save-posteriors Lesions \
               --threads ${task.cpus}

    if [ -f "samseg_out/seg.mgz" ]; then
        mri_binarize --i samseg_out/seg.mgz --match 99 --o ${meta.id}_samseg_binary.nii.gz
    else
        echo "Error: SAMSEG output seg.mgz missing" >&2
        exit 1
    fi
    if [ -f "samseg_out/posteriors/Lesions.mgz" ]; then
        mri_convert samseg_out/posteriors/Lesions.mgz ${meta.id}_samseg_prob.nii.gz
    else
        echo "Error: SAMSEG lesion posterior missing (contents of samseg_out/posteriors:)" >&2
        ls samseg_out/posteriors >&2 || true
        exit 1
    fi
    rm -rf samseg_out

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        samseg: 7.4.1
    END_VERSIONS
    """
}

process SEGMENTATION_WMH_SYNTHSEG {
    tag "$meta.id"
    label 'process_gpu'
    container 'frheault/sf-lesionflow-wmh_synthseg:1.0.0'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(flair_unstripped_mni)

    output:
    tuple val(meta), path("${meta.id}_wmh-synthseg_binary.nii.gz"), emit: binary_mask
    tuple val(meta), path("${meta.id}_wmh-synthseg_prob.nii.gz")  , emit: probability_map
    path "versions.yml"                                           , emit: versions

    stub:
    """
    touch ${meta.id}_wmh-synthseg_binary.nii.gz
    touch ${meta.id}_wmh-synthseg_prob.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        wmh_synthseg: 1.0
    END_VERSIONS
    """

    script:
    def label_id = task.ext.label_id ?: 77
    def use_gpu = task.ext.gpu
    def device_args = use_gpu ? "--device cuda --crop" : "--device cpu --crop --threads 1"
    """
    set +u
    export FREESURFER_HOME=/usr/local/freesurfer
    source /usr/local/freesurfer/SetUpFreeSurfer.sh
    set -u

    export HOME="\$(pwd)"
    export TORCH_HOME="\$(pwd)/.cache/torch"
    export MPLCONFIGDIR="\$(pwd)/.cache/matplotlib"

    mri_WMHsynthseg --i ${flair_unstripped_mni} \
                    --o multiclass.nii.gz \
                    --save_lesion_probabilities \
                    ${device_args}

    fspython "\$(command -v conform_synthseg.py)" --input multiclass.nii.gz --ref ${flair_unstripped_mni} --output ${meta.id}_wmh-synthseg_binary.nii.gz --label_id ${label_id}
    # mri_WMHsynthseg writes <output stem>.lesion_probs.nii.gz, in its internal
    # (cropped, 1mm) grid like multiclass.nii.gz -- resample it onto the FLAIR grid
    # (linear) so it aligns voxel-for-voxel with the binary mask.
    fspython "\$(command -v conform_synthseg.py)" --input multiclass.lesion_probs.nii.gz --ref ${flair_unstripped_mni} --output ${meta.id}_wmh-synthseg_prob.nii.gz --continuous
    rm -f multiclass.nii.gz multiclass.lesion_probs.nii.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        wmh_synthseg: 1.0
    END_VERSIONS
    """
}

process SEGMENTATION_FAST_OUTLIER {
    tag "$meta.id"
    container 'frheault/sf-lesionflow-fast_outlier:1.0.0'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_mni), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_fast-outlier_binary.nii.gz"), emit: binary_mask
    tuple val(meta), path("${meta.id}_fast-outlier_zscore.nii.gz"), emit: probability_map
    path "versions.yml"                                          , emit: versions

    stub:
    """
    touch ${meta.id}_fast-outlier_binary.nii.gz
    touch ${meta.id}_fast-outlier_zscore.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        fast: 6.0
        fast_outlier: 1.0
    END_VERSIONS
    """

    script:
    def sigma = task.ext.sigma ?: 2.5
    def pve_thresh = task.ext.pve_threshold ?: 0.95
    def dwm_thresh = task.ext.dwm_threshold ?: 0.50
    """
    export FSLDIR=/usr/local/fsl
    export PATH=\${FSLDIR}/bin:\$PATH
    export FSLOUTPUTTYPE=NIFTI_GZ

    mkdir -p fast_out
    fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -o fast_out/fast ${t1_mni}

    fast_outlier.py --flair ${flair_mni} \
                    --wm_pve fast_out/fast_pve_2.nii.gz \
                    --output ${meta.id}_fast-outlier_binary.nii.gz \
                    --sigma ${sigma} \
                    --pve_threshold ${pve_thresh} \
                    --dwm_threshold ${dwm_thresh} \
                    --output_zscore ${meta.id}_fast-outlier_zscore.nii.gz

    rm -rf fast_out

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        fast: 6.0
        fast_outlier: 1.0
    END_VERSIONS
    """
}

// GPU disabled: the published image only has the CPU-only torch wheel baked in
// (dockerfiles/flames/Dockerfile installs torch from the CPU index), so
// `-device cuda` would fail nnU-Net's torch.cuda.is_available() check. Revisit
// once the image is rebuilt with a CUDA-enabled torch wheel.
process SEGMENTATION_FLAMES {
    tag "$meta.id"
    container 'frheault/sf-lesionflow-flames:1.0.0'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_flames_binary.nii.gz"), emit: binary_mask
    tuple val(meta), path("${meta.id}_flames_prob.nii.gz")  , emit: probability_map
    path "versions.yml"                                     , emit: versions

    stub:
    """
    touch ${meta.id}_flames_binary.nii.gz
    touch ${meta.id}_flames_prob.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        nnunet: 2.0
        flames: 1.0
    END_VERSIONS
    """

    script:
    """
    export OMP_NUM_THREADS=${task.cpus}
    export MKL_NUM_THREADS=${task.cpus}
    export OPENBLAS_NUM_THREADS=${task.cpus}
    export PYTHONNOUSERSITE=1
    unset PYTHONPATH
    export nnUNet_results=/opt/nnunet_results
    export nnUNet_raw=/opt/nnunet_raw
    export nnUNet_preprocessed=/opt/nnunet_preprocessed
    export TORCH_HOME="\$(pwd)/.cache/torch"
    export MPLCONFIGDIR="\$(pwd)/.cache/matplotlib"

    mkdir -p in_dir out_dir
    ln -s \$(realpath ${flair_mni}) in_dir/${meta.id}_0000.nii.gz

    nnUNetv2_predict -i in_dir -o out_dir -d 004 -c 3d_fullres -tr nnUNetTrainer_8000epochs -device cpu -npp 1 -nps 1 --save_probabilities

    if [ -f "out_dir/${meta.id}.nii.gz" ]; then
        mv out_dir/${meta.id}.nii.gz ${meta.id}_flames_binary.nii.gz
    else
        echo "Error: FLAMeS output missing" >&2
        exit 1
    fi
    # v2 probabilities are already un-cropped to the input's full shape (SimpleITK
    # order); geometry comes from the nnU-Net input image itself.
    nnunet_probs_to_nifti.py --npz out_dir/${meta.id}.npz \
                             --ref in_dir/${meta.id}_0000.nii.gz \
                             --output ${meta.id}_flames_prob.nii.gz \
                             --check_mask ${meta.id}_flames_binary.nii.gz
    rm -rf in_dir out_dir

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        nnunet: 2.0
        flames: 1.0
    END_VERSIONS
    """
}

process SEGMENTATION_TRUENET {
    tag "$meta.id"
    label 'process_gpu'
    container 'frheault/sf-lesionflow-truenet:1.0.0'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1), path(flair)

    output:
    tuple val(meta), path("truenet.nii.gz")     , emit: binary_mask
    tuple val(meta), path("truenet_prob.nii.gz"), emit: probability_map, optional: true
    path "versions.yml"                         , emit: versions

    stub:
    """
    touch truenet.nii.gz
    touch truenet_prob.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        truenet: 1.0
    END_VERSIONS
    """

    script:
    def threshold = task.ext.threshold ?: 0.5
    def use_gpu = task.ext.gpu
    def cpu_arg = use_gpu ? "False" : "True"
    """
    export TRUENET_PRETRAINED_MODEL_PATH=/opt/truenet_models
    export TORCH_HOME="\$(pwd)/.cache/torch"
    export MPLCONFIGDIR="\$(pwd)/.cache/matplotlib"
    mkdir -p out

    flair_path=\$(realpath ${flair} | head -n 1)
    t1_path=\$(realpath ${t1} | head -n 1)

    echo "FLAIR T1" > masterfile.txt
    echo "\$flair_path \$t1_path" >> masterfile.txt

    truenet apply -i masterfile.txt -m mwsc -o out -cpu ${cpu_arg}

    threshold_probmap.py --input_glob 'out/Predicted_probmap_truenet_*.nii.gz' \
                         --output truenet.nii.gz \
                         --threshold ${threshold}

    prob_file=\$(ls out/Predicted_probmap_truenet_*.nii.gz 2>/dev/null | head -n 1)
    if [ -n "\$prob_file" ]; then
        mv "\$prob_file" truenet_prob.nii.gz
    fi
    rm -rf masterfile.txt out

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        truenet: 1.0
    END_VERSIONS
    """
}

process SEGMENTATION_HYPERMAPP3R {
    tag "$meta.id"
    container 'mgoubran/hypermapper:latest'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_mni), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_hypermapp3r_binary.nii.gz"), emit: binary_mask
    tuple val(meta), path("${meta.id}_hypermapp3r_prob.nii.gz")  , emit: probability_map
    path "versions.yml"                                         , emit: versions

    stub:
    """
    touch ${meta.id}_hypermapp3r_binary.nii.gz
    touch ${meta.id}_hypermapp3r_prob.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        hypermapper: 1.0
    END_VERSIONS
    """

    script:
    def threshold = task.ext.threshold ?: 0.5
    def mc_samples = task.ext.mc_samples ?: 20
    """
    export OMP_NUM_THREADS=2
    export OPENBLAS_NUM_THREADS=2
    export MKL_NUM_THREADS=2
    export TMPDIR="\$(pwd)/tmp_hyper"
    export APPTAINERENV_TMPDIR="\$(pwd)/tmp_hyper"
    export SINGULARITYENV_TMPDIR="\$(pwd)/tmp_hyper"

    mkdir -p tmp_hyper
    # HyperMapp3r requires a dilated brain mask (-m argument) to avoid clipping
    # juxtacortical/peripheral lesions at the brain boundary. We dilate the mask
    # by 4 voxels (~4mm at 1mm iso) as a pragmatic approximation to its own HfBd mask.
    create_nonzero_mask.py --input ${t1_mni} --output brain_mask.nii.gz --dilate 4

    set +e
    hypermapper seg_wmh \
        -s tmp_hyper \
        -t1 ${t1_mni} \
        -fl ${flair_mni} \
        -m brain_mask.nii.gz \
        -o pred.nii.gz \
        -n ${mc_samples} \
        -th ${threshold} \
        -f
    hyper_status=\$?
    set -e
    if [ \$hyper_status -ne 0 ]; then
        echo "hypermapper exited with status \$hyper_status (likely OOM-killed)" >&2
        exit \$hyper_status
    fi

    # `-o` is already binarized by hypermapper itself (`img > -th`), so it IS the
    # binary mask -- it is not a probability map. The soft map is the mean of the
    # ${mc_samples} MC-dropout label maps (i.e. the fraction of samples voting lesion),
    # linearly resampled to the T1 grid, saved as <subj>_<model>_pred_prob.nii.gz in
    # hypermapper's pred dir (<subj> = basename of -s). Its top-level *_wmh_prob.nii.gz
    # copy is NOT used: it is cast to uchar whenever hypermapper had to reorient.
    mv pred.nii.gz ${meta.id}_hypermapp3r_binary.nii.gz
    prob_file=\$(ls tmp_hyper/pred_process_wmh/tmp_hyper_*_pred_prob.nii.gz | head -n 1)
    conform_synthseg.py --input "\$prob_file" --ref ${t1_mni} --output ${meta.id}_hypermapp3r_prob.nii.gz --continuous
    rm -rf tmp_hyper brain_mask.nii.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        hypermapper: 1.0
    END_VERSIONS
    """
}

process PREPROC_SYNTHSEG {
    tag "$meta.id"
    label 'process_gpu'
    container 'freesurfer/freesurfer:7.4.1'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(flair)

    output:
    tuple val(meta), path("${meta.id}_synthseg.nii.gz"), emit: synthseg
    path "versions.yml"                                , emit: versions

    stub:
    """
    touch ${meta.id}_synthseg.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        synthseg: 2.0
    END_VERSIONS
    """

    script:
    def threads = task.cpus ?: 4
    def use_gpu = task.ext.gpu
    def device_arg = use_gpu ? "" : "--cpu"
    """
    set +u
    export FREESURFER_HOME=/usr/local/freesurfer
    source /usr/local/freesurfer/SetUpFreeSurfer.sh
    set -u

    mri_synthseg --i ${flair} --o ${meta.id}_synthseg.nii.gz --threads ${threads} ${device_arg}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        synthseg: 2.0
    END_VERSIONS
    """
}

process SEGMENTATION_SEGCSVD {
    tag "$meta.id"
    label 'process_gpu'
    container 'frheault/sf-lesionflow-segcsvd:rc03'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(flair_mni), path(synthseg)

    output:
    tuple val(meta), path("${meta.id}_segcsvd_binary.nii.gz"), emit: binary_mask
    tuple val(meta), path("${meta.id}_segcsvd_prob.nii.gz")  , emit: probability_map
    path "versions.yml"                                      , emit: versions

    stub:
    """
    touch ${meta.id}_segcsvd_binary.nii.gz
    touch ${meta.id}_segcsvd_prob.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        segcsvd: rc03
    END_VERSIONS
    """

    script:
    def use_gpu = task.ext.gpu
    def threshold = task.ext.threshold ?: 0.35
    def patch_size = task.ext.patch_size ?: "96,128"
    """
    export OMP_NUM_THREADS=${task.cpus}
    export TORCH_HOME="\$(pwd)/.cache/torch"
    export MPLCONFIGDIR="\$(pwd)/.cache/matplotlib"

    # segment_wmh writes its soft map to <out_fn>, then its own thresholded binary to
    # out_fn with "/outdir/" rewritten to "/outdir/thr_". If out_fn does NOT contain
    # "/outdir/" (a bare "prob.nii.gz"), the binary silently OVERWRITES the soft map --
    # hence the absolute path under a directory literally named outdir.
    mkdir -p "\$PWD/outdir"
    out_prob="\$PWD/outdir/prob.nii.gz"

    if [ "${use_gpu}" = "true" ]; then
        sed 's/ -c//' /seg/tools/segment_wmh > ./segment_wmh_device
        chmod +x ./segment_wmh_device
        ./segment_wmh_device ${flair_mni} ${synthseg} "\$out_prob" 1 "${patch_size}" ${threshold} 1 true true
    else
        segment_wmh ${flair_mni} ${synthseg} "\$out_prob" 1 "${patch_size}" ${threshold} 1 true true
    fi

    test -s "\$PWD/outdir/thr_prob.nii.gz" || { echo "ERROR: segment_wmh did not write its binary to outdir/thr_prob.nii.gz" >&2; exit 1; }
    python3 -c "
import sys, nibabel as nib, numpy as np
p = np.asanyarray(nib.load('outdir/prob.nii.gz').dataobj)
n = np.unique(p[p > 0]).size
sys.exit(0 if n > 2 else 'ERROR: SegCSVD probability map is not soft (%d distinct non-zero values)' % n)
"

    threshold_probmap.py --input outdir/prob.nii.gz \
                         --output ${meta.id}_segcsvd_binary.nii.gz \
                         --threshold ${threshold}

    mv outdir/prob.nii.gz ${meta.id}_segcsvd_prob.nii.gz
    rm -rf outdir segment_wmh_device

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        segcsvd: rc03
    END_VERSIONS
    """
}

process SEGMENTATION_EMORY_ROBUST {
    tag "$meta.id"
    label 'process_gpu'
    container 'emorycn2l/emory_robust_wmh:v1.2'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_mni), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_emory_robust_binary.nii.gz"), emit: binary_mask
    tuple val(meta), path("${meta.id}_emory_robust_prob.nii.gz")  , emit: probability_map
    path "versions.yml"                                           , emit: versions

    stub:
    """
    touch ${meta.id}_emory_robust_binary.nii.gz
    touch ${meta.id}_emory_robust_prob.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        emory_robust_wmh: 1.2
    END_VERSIONS
    """

    script:
    def use_gpu = task.ext.gpu
    def gpu_flag = use_gpu ? "--gpu" : ""
    """
    export OMP_NUM_THREADS=4
    export PATH=/opt/conda/envs/nnunet/bin:/opt/conda/bin:\$PATH
    export TORCH_HOME="\$(pwd)/.cache/torch"
    export MPLCONFIGDIR="\$(pwd)/.cache/matplotlib"
    export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

    bash /app/main.sh -t \$(realpath ${t1_mni}) -f \$(realpath ${flair_mni}) -o \$(realpath ${meta.id}_emory_robust_binary.nii.gz) --no-n4 --no-coreg ${gpu_flag}

    # /app/main.sh already runs both nnUNetv2_predict calls with --save_probabilities
    # and ensembles them with nnUNetv2_ensemble (a plain mean of the two probability
    # maps); /app/inputs and /app/outputs are bind-mounted here (see nextflow.config).
    # Reproduce that mean from the kept per-model .npz files, on the nnU-Net input grid.
    nnunet_probs_to_nifti.py --npz .app_outputs/2d/wmh.npz .app_outputs/3d_fullres/wmh.npz \
                             --ref .app_inputs/wmh_0001.nii.gz \
                             --output ${meta.id}_emory_robust_prob.nii.gz \
                             --check_mask ${meta.id}_emory_robust_binary.nii.gz

    rm -rf .app_inputs .app_outputs

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        emory_robust_wmh: 1.2
    END_VERSIONS
    """
}

process SEGMENTATION_MARS_WMH {
    tag "$meta.id"
    label 'process_gpu'
    container 'ghcr.io/miac-research/wmh-nnunet:1.0.2'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_unstripped), path(flair_unstripped)

    output:
    tuple val(meta), path("mars_wmh.nii.gz")     , emit: binary_mask
    tuple val(meta), path("mars_wmh_prob.nii.gz"), emit: probability_map
    tuple val(meta), path("*_QC.html")           , emit: qc_html    , optional: true
    path "versions.yml"                          , emit: versions

    stub:
    """
    touch mars_wmh.nii.gz
    touch mars_wmh_prob.nii.gz
    touch mars_wmh_QC.html
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        mars_wmh: 1.0.2
    END_VERSIONS
    """

    script:
    def use_gpu = task.ext.gpu
    def gpu_env = use_gpu ? "export CUDA_VISIBLE_DEVICES=0" : "export CUDA_VISIBLE_DEVICES=\"\""
    """
    export OMP_NUM_THREADS=${task.cpus}
    export PYTHONNOUSERSITE=1
    unset PYTHONPATH
    export TORCH_HOME="\$(pwd)/.cache/torch"
    export MPLCONFIGDIR="\$(pwd)/.cache/matplotlib"
    export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
    ${gpu_env}

    # pipeline_nnunet.py has no probability option, but it shells out to nnU-Net v1's
    # `nnUNet_predict`, which does (-z/--save_npz). Run a copy with -z added (anchored:
    # abort if the command string ever changes) and --debug to keep its temp folder,
    # then export the softmax (cropped in v1 -> un-cropped via the .pkl) onto the
    # original FLAIR grid. PYTHONPATH lets the copy import its sibling QC modules.
    sed "s/-t Task700_WMH'/-t Task700_WMH -z'/" /opt/scripts/pipeline_nnunet.py > pipeline_nnunet_prob.py
    grep -q "Task700_WMH -z'" pipeline_nnunet_prob.py || { echo "Error: MARS-WMH nnUNet_predict call not found; cannot enable -z" >&2; exit 1; }

    PYTHONPATH=/opt/scripts python pipeline_nnunet_prob.py \
        --flair ${flair_unstripped} \
        --t1 ${t1_unstripped} \
        --fnOut mars_wmh.nii.gz \
        --overwrite \
        --debug

    mars_tmp=\$(ls -d mars_wmh_temp-* | head -n 1)
    nnunet_probs_to_nifti.py --npz \$mars_tmp/nnUNet/wmh.npz \
                             --ref \$mars_tmp/nnUNet/wmh_0000.nii.gz \
                             --target ${flair_unstripped} \
                             --output mars_wmh_prob.nii.gz \
                             --check_mask mars_wmh.nii.gz
    rm -rf "\$mars_tmp" pipeline_nnunet_prob.py

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        mars_wmh: 1.0.2
    END_VERSIONS
    """
}

// BAWIL (Bashiri Bawil M, et al., "Incorporating normal periventricular changes for
// enhanced pathological WMH segmentation: multiclass deep learning approaches,"
// Biomedical Engineering Online, 2026, PMC13202883): runs the REAL, pretrained
// Keras model (huggingface.co/Bawil/wmh_leverage_normal_abnormal_segmentation,
// scenario2_multiclass_model.h5) -- a 3-class U-Net (0: background, 1: normal WMH,
// 2: abnormal WMH) on axial FLAIR slices. Note: arXiv:2506.07123 describes a different
// 4-class GAN model from the same authors; the loaded model matches PMC13202883.
// See CITATIONS.md and bin/bawil_filter.py for details.
process SEGMENTATION_BAWIL {
    tag "$meta.id"
    label 'process_gpu'
    container 'frheault/sf-lesionflow-bawil:1.0.0'

    when:
    task.ext.when == null || task.ext.when

    input:
    // 1 mm resampled, non-N4 FLAIR (full FOV) + its SynthStrip brain mask on the same grid
    // (framing box and, with ext.strip, skull removal).
    tuple val(meta), path(flair), path(brainmask)

    output:
    tuple val(meta), path("bawil.nii.gz")     , emit: binary_mask
    tuple val(meta), path("bawil_prob.nii.gz"), emit: probability_map
    path "versions.yml"                       , emit: versions

    stub:
    """
    touch bawil.nii.gz
    touch bawil_prob.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        bawil: 1.0
    END_VERSIONS
    """

    script:
    // Defaults chosen by the calibration experiment in dockerfiles/bawil/README.md (28 input
    // presentations x 2 subjects, scored against the other 11 algorithms): axial slices rotated
    // to the training orientation (anterior at the top; the model was trained without rotation
    // augmentation), brain bounding box resized to 256x256, input zeroed outside the brain
    // (this cohort's 3D FLAIR scalp/neck contrast differs from the 2D clinical training slices
    // and produced massive false positives when shown), upstream decision rule argmax == 2.
    def framing     = task.ext.framing       ?: 'brainbox'
    def orientation = task.ext.orientation   ?: 'rot90'
    def strip       = task.ext.strip != null ? task.ext.strip : true
    def fov_fill    = task.ext.fov_fill      ?: 0.92
    def slab_mm     = task.ext.slab_mm       != null ? task.ext.slab_mm : 0
    def decision    = task.ext.decision      ?: 'argmax'
    def prob_thresh = task.ext.prob_threshold ?: 0.50
    def min_cluster = task.ext.min_cluster_size ?: 3
    def use_gpu = task.ext.gpu
    """
    export CUDA_VISIBLE_DEVICES=${use_gpu ? '0' : '-1'}
    export TF_CPP_MIN_LOG_LEVEL=2
    export MPLCONFIGDIR="\$(pwd)/.cache/matplotlib"

    bawil_filter.py --flair ${flair} \
                    --brainmask ${brainmask} \
                    --output bawil.nii.gz \
                    --output_prob bawil_prob.nii.gz \
                    --framing ${framing} \
                    ${strip ? '--strip' : ''} \
                    --orientation ${orientation} \
                    --fov_fill ${fov_fill} \
                    --slab_mm ${slab_mm} \
                    --decision ${decision} \
                    --prob_threshold ${prob_thresh} \
                    --min_cluster_size ${min_cluster}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        bawil: 1.0
    END_VERSIONS
    """
}

// MIMoSA (Valcarcel et al. 2018, doi:10.1111/jon.12506): runs the REAL, pretrained
// `mimosa_model_No_PD_T2` model shipped inside the `mimosa` R package itself
// (FLAIR + T1, matching this pipeline's inputs exactly). No training data
// required, and no heuristic proxy involved -- see CITATIONS.md.
process SEGMENTATION_MIMOSA {
    tag "$meta.id"
    container 'frheault/sf-lesionflow-mimosa:1.0.0'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_mni), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_mimosa_binary.nii.gz"), emit: binary_mask
    tuple val(meta), path("${meta.id}_mimosa_prob.nii.gz")  , emit: probability_map
    path "versions.yml"                                     , emit: versions

    stub:
    """
    touch ${meta.id}_mimosa_binary.nii.gz
    touch ${meta.id}_mimosa_prob.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        mimosa: 1.0
    END_VERSIONS
    """

    script:
    def prob_thresh = task.ext.prob_threshold ?: 0.30
    def min_cluster = task.ext.min_cluster_size ?: 3
    """
    export FSLDIR=/opt/fsl-6.0.3
    export PATH="\${FSLDIR}/bin:\${PATH}"
    export FSLOUTPUTTYPE=NIFTI_GZ

    mimosa_predict.R --t1 ${t1_mni} \
                     --flair ${flair_mni} \
                     --output ${meta.id}_mimosa_binary.nii.gz \
                     --prob_threshold ${prob_thresh} \
                     --min_cluster_size ${min_cluster} \
                     --output_prob ${meta.id}_mimosa_prob.nii.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        mimosa: 1.0
    END_VERSIONS
    """
}

// SHIVA-WMH (Tsuchida A, Boutinaud P, et al., doi:10.1002/hbm.26548): runs the REAL,
// pretrained 5-fold ResUnet3D SavedModel ensemble (github.com/pboutinaud/SHIVA_WMH,
// v2/T1+FLAIR-WMH), not a heuristic proxy -- see CITATIONS.md and
// bin/shivai_predict.py's docstring for the center-crop/normalize preprocessing this
// pipeline's MNI-space inputs need before the model's fixed 160x214x176 input shape,
// verified end-to-end before being wired in here.
process SEGMENTATION_SHIVAI {
    tag "$meta.id"
    label 'process_gpu'
    container 'frheault/sf-lesionflow-shivai:1.0.0'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_mni), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_shivai_binary.nii.gz"), emit: binary_mask
    tuple val(meta), path("${meta.id}_shivai_prob.nii.gz")  , emit: probability_map
    path "versions.yml"                                     , emit: versions

    stub:
    """
    touch ${meta.id}_shivai_binary.nii.gz
    touch ${meta.id}_shivai_prob.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        shivai: 1.0
    END_VERSIONS
    """

    script:
    def prob_thresh = task.ext.prob_threshold ?: 0.50
    def min_cluster = task.ext.min_cluster_size ?: 3
    def use_gpu = task.ext.gpu
    """
    export CUDA_VISIBLE_DEVICES=${use_gpu ? '0' : '-1'}
    export MPLCONFIGDIR="\$(pwd)/.cache/matplotlib"

    shivai_predict.py --t1 ${t1_mni} \
                     --flair ${flair_mni} \
                     --output ${meta.id}_shivai_binary.nii.gz \
                     --prob_threshold ${prob_thresh} \
                     --min_cluster_size ${min_cluster} \
                     --output_prob ${meta.id}_shivai_prob.nii.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        shivai: 1.0
    END_VERSIONS
    """
}

process SEGMENTATION_MINDGLIDE {
    tag "$meta.id"
    label 'process_gpu'
    container 'frheault/sf-lesionflow-mindglide:1.0.0'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(flair)

    output:
    tuple val(meta), path("mindglide.nii.gz")     , emit: binary_mask
    tuple val(meta), path("mindglide_prob.nii.gz"), emit: probability_map
    path "versions.yml"                           , emit: versions

    stub:
    """
    touch mindglide.nii.gz
    touch mindglide_prob.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        mindglide: 1.3.0
    END_VERSIONS
    """

    script:
    def label_id = task.ext.label_id ?: 18
    def device   = task.ext.gpu ? "cuda" : "cpu"
    """
    export HF_HUB_OFFLINE=1
    export TORCH_HOME="\$(pwd)/.cache/torch"
    export MPLCONFIGDIR="\$(pwd)/.cache/matplotlib"

    # mindglide_prob.py == `mindglide`, plus the lesion-channel softmax (argmaxed and
    # discarded upstream) saved as multiclass_prob.nii.gz -- see its docstring.
    MINDGLIDE_PROB_LABEL=${label_id} mindglide_prob.py -i ${flair} -o multiclass.nii.gz --device ${device}

    conform_synthseg.py --input multiclass.nii.gz --ref ${flair} --output mindglide.nii.gz --label_id ${label_id}
    conform_synthseg.py --input multiclass_prob.nii.gz --ref ${flair} --output mindglide_prob.nii.gz --continuous
    rm -f multiclass.nii.gz multiclass_prob.nii.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        mindglide: 1.3.0
    END_VERSIONS
    """
}


// -----------------------------------------------------------------------------
// Phase 3: STAPLE Consensus Fusion (thr90 >= 6mm3 + Watershed)
// -----------------------------------------------------------------------------

process CONSENSUS_STAPLE {
    tag "$meta.id"
    container 'frheault/sf-lesionflow-segcsvd:rc03'
    input:
    tuple val(meta), path(ref_image), path(binary_masks)

    output:
    tuple val(meta), path("${meta.id}_staple_probmap.nii.gz"), emit: staple_probmap
    tuple val(meta), path("${meta.id}_staple_thr90_binary.nii.gz"), emit: staple_thr90_binary
    tuple val(meta), path("${meta.id}_staple_thr90_labels_uint16.nii.gz"), emit: staple_thr90_labels
    path "versions.yml"                                                   , emit: versions

    stub:
    """
    touch ${meta.id}_staple_probmap.nii.gz
    touch ${meta.id}_staple_thr90_binary.nii.gz
    touch ${meta.id}_staple_thr90_labels_uint16.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        staple: 1.0
    END_VERSIONS
    """

    script:
    def threshold = task.ext.threshold ?: 0.90
    def min_cluster = task.ext.min_cluster_size ?: 6
    def min_dist = task.ext.min_distance ?: 3
    def g_sigma = task.ext.gaussian_sigma ?: 0.8
    """
    staple_consensus.py --ref_image ${ref_image} \
                        --masks ${binary_masks} \
                        --out_probmap ${meta.id}_staple_probmap.nii.gz \
                        --out_binary ${meta.id}_staple_thr90_binary.nii.gz \
                        --out_labels ${meta.id}_staple_thr90_labels_uint16.nii.gz \
                        --threshold ${threshold} \
                        --min_cluster_size ${min_cluster} \
                        --min_distance ${min_dist} \
                        --gaussian_sigma ${g_sigma}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        sf-lesionflow: "${workflow.manifest.version}"
        python: "\$(python3 --version 2>&1 | awk '{print \$2}')"
        SimpleITK: "\$(python3 -c 'import SimpleITK; print(SimpleITK.Version_VersionString())' 2>/dev/null || echo unknown)"
        nibabel: "\$(python3 -c 'import nibabel; print(nibabel.__version__)')"
        scikit-image: "\$(python3 -c 'import skimage; print(skimage.__version__)')"
    END_VERSIONS
    """
}

// -----------------------------------------------------------------------------
// Phase 4: Longitudinal Harmonization & Tracking Audit Trail
// -----------------------------------------------------------------------------

process HARMONIZATION_STAPLE {
    tag "$subject"
    container 'frheault/sf-lesionflow-segcsvd:rc03'
    input:
    tuple val(subject), val(metas), path(staple_masks)

    output:
    tuple val(subject), path("*_staple_thr90_harmonized_binary.nii.gz"), emit: harmonized_binary
    tuple val(subject), path("*_staple_thr90_harmonized_labels_uint16.nii.gz"), emit: harmonized_labels
    tuple val(subject), path("${subject}_staple_harmonized_lesion_tracking.csv"), emit: audit_csv
    path "versions.yml"                                                         , emit: versions

    stub:
    """
    for m in ${staple_masks}; do
        fname=\$(basename \$m)
        ses_name=\$(echo \$fname | grep -o 'ses-[0-9a-zA-Z]*')
        if [ -n "\$ses_name" ]; then
            ses_suffix="_\${ses_name}"
        else
            ses_suffix=""
        fi
        touch ${subject}\${ses_suffix}_staple_thr90_harmonized_binary.nii.gz
        touch ${subject}\${ses_suffix}_staple_thr90_harmonized_labels_uint16.nii.gz
    done
    touch ${subject}_staple_harmonized_lesion_tracking.csv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        harmonization: 1.0
    END_VERSIONS
    """

    script:
    def min_cluster = task.ext.min_cluster_size ?: 6
    def min_dist = task.ext.min_distance ?: 3
    def g_sigma = task.ext.gaussian_sigma ?: 0.8
    def pct_thresh = task.ext.pct_change_threshold ?: 20.0
    """
    harmonize_staple.py --subject ${subject} \
                        --masks ${staple_masks} \
                        --out_csv ${subject}_staple_harmonized_lesion_tracking.csv \
                        --min_cluster_size ${min_cluster} \
                        --min_distance ${min_dist} \
                        --gaussian_sigma ${g_sigma} \
                        --pct_change_threshold ${pct_thresh}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        sf-lesionflow: "${workflow.manifest.version}"
        python: "\$(python3 --version 2>&1 | awk '{print \$2}')"
        SimpleITK: "\$(python3 -c 'import SimpleITK; print(SimpleITK.Version_VersionString())' 2>/dev/null || echo unknown)"
        nibabel: "\$(python3 -c 'import nibabel; print(nibabel.__version__)')"
        scikit-image: "\$(python3 -c 'import skimage; print(skimage.__version__)')"
    END_VERSIONS
    """
}
