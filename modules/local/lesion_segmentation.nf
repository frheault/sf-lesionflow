#!/usr/bin/env nextflow

// -----------------------------------------------------------------------------
// Phase 2: Independent Algorithm Modules
// -----------------------------------------------------------------------------

process SEGMENTATION_LST_AI {
    tag "$meta.id"
    label 'process_medium'
    container 'ms_chus/lst_ai:latest'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_mni), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_lst_ai_binary.nii.gz"), emit: binary_mask
    path "versions.yml"                                     , emit: versions

    stub:
    """
    touch ${meta.id}_lst_ai_binary.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        lst_ai: 2.0.0
    END_VERSIONS
    """

    script:
    """
    export CUDA_VISIBLE_DEVICES=-1
    export TF_FORCE_GPU_ALLOW_GROWTH=true
    export TF_GPU_ALLOCATOR=cuda_malloc_async
    export TF_CPP_MIN_LOG_LEVEL=2
    export OMP_NUM_THREADS=${task.cpus}

    mkdir -p tmp_out
    lst --t1 ${t1_mni} --flair ${flair_mni} --output tmp_out --segment_only --stripped --threads ${task.cpus}

    if [ -f "tmp_out/space-flair_seg-lst.nii.gz" ]; then
        mv tmp_out/space-flair_seg-lst.nii.gz ${meta.id}_lst_ai_binary.nii.gz
    else
        echo "Error: LST-AI output missing" >&2
        exit 1
    fi
    rm -rf tmp_out

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        lst_ai: 2.0.0
    END_VERSIONS
    """
}

process SEGMENTATION_SAMSEG {
    tag "$meta.id"
    label 'process_high_memory'
    container 'freesurfer/freesurfer:7.4.1'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_unstripped_mni), path(flair_unstripped_mni), path(fs_license)

    output:
    tuple val(meta), path("${meta.id}_samseg_binary.nii.gz"), emit: binary_mask
    path "versions.yml"                                     , emit: versions

    stub:
    """
    touch ${meta.id}_samseg_binary.nii.gz
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

    mkdir -p samseg_out
    run_samseg -i ${t1_unstripped_mni} -i ${flair_unstripped_mni} \
               --out samseg_out \
               --lesion \
               --lesion-mask-pattern 0 1 \
               --pallidum-separate \
               --threads ${task.cpus}

    if [ -f "samseg_out/seg.mgz" ]; then
        mri_binarize --i samseg_out/seg.mgz --match 77 99 --o ${meta.id}_samseg_binary.nii.gz
    else
        echo "Error: SAMSEG output seg.mgz missing" >&2
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
    label 'process_high_memory'
    container 'ms_chus/wmh_synthseg:latest'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(flair_unstripped_mni)

    output:
    tuple val(meta), path("${meta.id}_wmh-synthseg_binary.nii.gz"), emit: binary_mask
    path "versions.yml"                                           , emit: versions

    stub:
    """
    touch ${meta.id}_wmh-synthseg_binary.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        wmh_synthseg: 1.0
    END_VERSIONS
    """

    script:
    def label_id = task.ext.label_id ?: 77
    """
    set +u
    export FREESURFER_HOME=/usr/local/freesurfer
    source /usr/local/freesurfer/SetUpFreeSurfer.sh
    set -u

    mri_WMHsynthseg --i ${flair_unstripped_mni} \
                    --o multiclass.nii.gz \
                    --save_lesion_probabilities \
                    --device cpu \
                    --threads 1

    fspython "\$(command -v conform_synthseg.py)" --input multiclass.nii.gz --ref ${flair_unstripped_mni} --output ${meta.id}_wmh-synthseg_binary.nii.gz --label_id ${label_id}
    rm -f multiclass.nii.gz *.lesion_probs.nii.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        wmh_synthseg: 1.0
    END_VERSIONS
    """
}

process SEGMENTATION_FAST_OUTLIER {
    tag "$meta.id"
    label 'process_single'
    container 'ms_chus/fast_outlier:latest'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_mni), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_fast-outlier_binary.nii.gz"), emit: binary_mask
    path "versions.yml"                                          , emit: versions

    stub:
    """
    touch ${meta.id}_fast-outlier_binary.nii.gz
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
                    --dwm_threshold ${dwm_thresh}

    rm -rf fast_out

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        fast: 6.0
        fast_outlier: 1.0
    END_VERSIONS
    """
}

process SEGMENTATION_FLAMES {
    tag "$meta.id"
    label 'process_medium'
    container 'ms_chus/flames:latest'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_flames_binary.nii.gz"), emit: binary_mask
    path "versions.yml"                                     , emit: versions

    stub:
    """
    touch ${meta.id}_flames_binary.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        nnunet: 2.0
        flames: 1.0
    END_VERSIONS
    """

    script:
    """
    export nnUNet_results=/opt/nnunet_results
    export nnUNet_raw=/opt/nnunet_raw
    export nnUNet_preprocessed=/opt/nnunet_preprocessed

    mkdir -p in_dir out_dir
    ln -s \$(realpath ${flair_mni}) in_dir/${meta.id}_0000.nii.gz

    nnUNetv2_predict -i in_dir -o out_dir -d 004 -c 3d_fullres -tr nnUNetTrainer_8000epochs --disable_tta -device cpu

    if [ -f "out_dir/${meta.id}.nii.gz" ]; then
        mv out_dir/${meta.id}.nii.gz ${meta.id}_flames_binary.nii.gz
    else
        echo "Error: FLAMeS output missing" >&2
        exit 1
    fi
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
    label 'process_medium'
    container 'ms_chus/truenet:latest'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_mni), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_truenet_binary.nii.gz"), emit: binary_mask
    path "versions.yml"                                      , emit: versions

    stub:
    """
    touch ${meta.id}_truenet_binary.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        truenet: 1.0
    END_VERSIONS
    """

    script:
    def threshold = task.ext.threshold ?: 0.5
    """
    export TRUENET_PRETRAINED_MODEL_PATH=/opt/truenet_models
    mkdir -p out

    flair_path=\$(realpath ${flair_mni} | head -n 1)
    t1_path=\$(realpath ${t1_mni} | head -n 1)

    echo "FLAIR T1" > masterfile.txt
    echo "\$flair_path \$t1_path" >> masterfile.txt

    truenet apply -i \$(realpath masterfile.txt) -m mwsc -o out -cpu True

    threshold_probmap.py --input_glob 'out/Predicted_probmap_truenet_*.nii.gz' \
                         --output ${meta.id}_truenet_binary.nii.gz \
                         --threshold ${threshold}

    rm -rf masterfile.txt out

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        truenet: 1.0
    END_VERSIONS
    """
}

process SEGMENTATION_HYPERMAPP3R {
    tag "$meta.id"
    label 'process_high_memory'
    container 'mgoubran/hypermapper:latest'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_mni), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_hypermapp3r_binary.nii.gz"), emit: binary_mask
    path "versions.yml"                                         , emit: versions

    stub:
    """
    touch ${meta.id}_hypermapp3r_binary.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        hypermapper: 1.0
    END_VERSIONS
    """

    script:
    def threshold = task.ext.threshold ?: 0.5
    def mc_samples = task.ext.mc_samples ?: 1
    """
    export OMP_NUM_THREADS=2
    export OPENBLAS_NUM_THREADS=2
    export MKL_NUM_THREADS=2

    create_nonzero_mask.py --input ${t1_mni} --output brain_mask.nii.gz

    mkdir -p tmp_hyper
    (
        cd tmp_hyper
        hypermapper seg_wmh -t1 \$(realpath ../${t1_mni}) -fl \$(realpath ../${flair_mni}) -m \$(realpath ../brain_mask.nii.gz) -o \$(realpath ../prob.nii.gz) -n ${mc_samples} -f
    )

    threshold_probmap.py --input prob.nii.gz \
                         --output ${meta.id}_hypermapp3r_binary.nii.gz \
                         --threshold ${threshold}

    rm -rf tmp_hyper brain_mask.nii.gz prob.nii.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        hypermapper: 1.0
    END_VERSIONS
    """
}

process SEGMENTATION_SEGCSVD {
    tag "$meta.id"
    label 'process_medium'
    container 'segcsvd_rc03:latest'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_segcsvd_binary.nii.gz"), emit: binary_mask
    path "versions.yml"                                      , emit: versions

    stub:
    """
    touch ${meta.id}_segcsvd_binary.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        segcsvd: rc03
    END_VERSIONS
    """

    script:
    def threshold = task.ext.threshold ?: 0.5
    def patch_size = task.ext.patch_size ?: "96,128"
    """
    export OMP_NUM_THREADS=${task.cpus}

    create_nonzero_mask.py --input ${flair_mni} --output temp_mask.nii.gz

    segment_wmh \$(realpath ${flair_mni}) \$(realpath temp_mask.nii.gz) \$(realpath prob.nii.gz) 1 "${patch_size}" ${threshold} 1 true true

    threshold_probmap.py --input prob.nii.gz \
                         --output ${meta.id}_segcsvd_binary.nii.gz \
                         --threshold ${threshold}

    rm -f temp_mask.nii.gz prob.nii.gz

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        segcsvd: rc03
    END_VERSIONS
    """
}

process SEGMENTATION_EMORY_ROBUST {
    tag "$meta.id"
    label 'process_high_memory'
    container 'emorycn2l/emory_robust_wmh:v1.2'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_mni), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_emory_robust_binary.nii.gz"), emit: binary_mask
    path "versions.yml"                                           , emit: versions

    stub:
    """
    touch ${meta.id}_emory_robust_binary.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        emory_robust_wmh: 1.2
    END_VERSIONS
    """

    script:
    """
    export OMP_NUM_THREADS=4
    export PATH=/opt/conda/envs/nnunet/bin:/opt/conda/bin:\$PATH

    bash /app/main.sh -t \$(realpath ${t1_mni}) -f \$(realpath ${flair_mni}) -o \$(realpath ${meta.id}_emory_robust_binary.nii.gz) --no-n4 --no-coreg

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        emory_robust_wmh: 1.2
    END_VERSIONS
    """
}

process SEGMENTATION_MARS_WMH {
    tag "$meta.id"
    label 'process_medium'
    container 'ghcr.io/miac-research/wmh-nnunet:latest'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_mni), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_mars_wmh_binary.nii.gz"), emit: binary_mask
    path "versions.yml"                                       , emit: versions

    stub:
    """
    touch ${meta.id}_mars_wmh_binary.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        mars_wmh: 1.0
    END_VERSIONS
    """

    script:
    """
    export OMP_NUM_THREADS=${task.cpus}

    python /opt/scripts/pipeline_nnunet.py \
        --flair \$(realpath ${flair_mni}) \
        --t1 \$(realpath ${t1_mni}) \
        --fnOut \$(realpath ${meta.id}_mars_wmh_binary.nii.gz) \
        --skipRegistration \
        --overwrite \
        --omitQC

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        mars_wmh: 1.0
    END_VERSIONS
    """
}

// BAWIL (Bashiri Bawil M, et al., arXiv:2506.07123): runs the REAL, pretrained
// Keras model (huggingface.co/Bawil/wmh_leverage_normal_abnormal_segmentation),
// not a heuristic proxy -- see CITATIONS.md and bin/bawil_filter.py's docstring
// for the full preprocessing story (per-slice axial inference, no official
// NIfTI CLI exists upstream so this reimplements the paper's own preprocessing,
// verified end-to-end before being wired in here).
process SEGMENTATION_BAWIL {
    tag "$meta.id"
    label 'process_medium'
    container 'ms_chus/bawil:latest'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_bawil_binary.nii.gz"), emit: binary_mask
    path "versions.yml"                                    , emit: versions

    stub:
    """
    touch ${meta.id}_bawil_binary.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        bawil: 1.0
    END_VERSIONS
    """

    script:
    def prob_thresh = task.ext.prob_threshold ?: 0.50
    def min_cluster = task.ext.min_cluster_size ?: 3
    """
    export CUDA_VISIBLE_DEVICES=-1
    export TF_CPP_MIN_LOG_LEVEL=2

    bawil_filter.py --flair ${flair_mni} \
                    --output ${meta.id}_bawil_binary.nii.gz \
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
    label 'process_medium'
    container 'ms_chus/mimosa:latest'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_mni), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_mimosa_binary.nii.gz"), emit: binary_mask
    path "versions.yml"                                     , emit: versions

    stub:
    """
    touch ${meta.id}_mimosa_binary.nii.gz
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
                     --min_cluster_size ${min_cluster}

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
    label 'process_medium'
    container 'ms_chus/shivai:latest'

    when:
    task.ext.when == null || task.ext.when

    input:
    tuple val(meta), path(t1_mni), path(flair_mni)

    output:
    tuple val(meta), path("${meta.id}_shivai_binary.nii.gz"), emit: binary_mask
    path "versions.yml"                                     , emit: versions

    stub:
    """
    touch ${meta.id}_shivai_binary.nii.gz
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        shivai: 1.0
    END_VERSIONS
    """

    script:
    def prob_thresh = task.ext.prob_threshold ?: 0.50
    def min_cluster = task.ext.min_cluster_size ?: 3
    """
    export CUDA_VISIBLE_DEVICES=-1

    shivai_predict.py --t1 ${t1_mni} \
                     --flair ${flair_mni} \
                     --output ${meta.id}_shivai_binary.nii.gz \
                     --prob_threshold ${prob_thresh} \
                     --min_cluster_size ${min_cluster}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        shivai: 1.0
    END_VERSIONS
    """
}

// -----------------------------------------------------------------------------
// Phase 3: STAPLE Consensus Fusion (thr90 >= 6mm3 + Watershed)
// -----------------------------------------------------------------------------

process CONSENSUS_STAPLE {
    tag "$meta.id"
    label 'process_single'
    container 'segcsvd_rc03:latest'
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
        staple: 1.0
    END_VERSIONS
    """
}

// -----------------------------------------------------------------------------
// Phase 4: Longitudinal Harmonization & Tracking Audit Trail
// -----------------------------------------------------------------------------

process HARMONIZATION_STAPLE {
    tag "$subject"
    label 'process_medium'
    container 'segcsvd_rc03:latest'
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
        harmonization: 1.0
    END_VERSIONS
    """
}
