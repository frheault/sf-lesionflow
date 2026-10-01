// Single producer of every published per-algorithm lesion file (see bin/finalize_lesion.py):
// grid check, dtype/range normalization, optional brain masking, BIDS naming + JSON sidecar.
process LESION_FINALIZE {
    tag "${meta.id}:${algo}"
    container 'frheault/sf-lesionflow-segcsvd:rc03'

    input:
    tuple val(meta), val(algo), path(binary, stageAs: 'in/binary.nii.gz'), path(prob, stageAs: 'in/prob.nii.gz'), path(brainmask, stageAs: 'in/brainmask.nii.gz'), path(template, stageAs: 'in/template.nii.gz')

    output:
    tuple val(meta), val(algo), path("${meta.id}_space-*_desc-*_mask.nii.gz")              , emit: mask
    tuple val(meta), val(algo), path("${meta.id}_space-*_desc-*_{probseg,zscore}.nii.gz")  , emit: prob
    tuple val(meta), val(algo), path("${meta.id}_space-*_desc-*_mask.json")                , emit: sidecar

    when:
    task.ext.when == null || task.ext.when

    script:
    def label       = AlgorithmSelection.BIDS_LABEL[algo]
    def space       = task.ext.space ?: 'MNI'
    def apply_mask  = task.ext.apply_brainmask ? '--apply_brainmask' : ''
    def dilation    = task.ext.dilation != null ? task.ext.dilation : 1
    def input_space = task.ext.input_space ?: 'MNI'
    def zscore      = algo == 'fast_outlier' ? '--zscore' : ''
    def prob_arg    = prob ? "--prob ${prob}" : ''
    """
    finalize_lesion.py \\
        --prefix ${meta.id} \\
        --algo ${algo} \\
        --label ${label} \\
        --space ${space} \\
        --binary ${binary} \\
        ${prob_arg} \\
        --template ${template} \\
        --brainmask ${brainmask} \\
        ${apply_mask} \\
        --dilation ${dilation} \\
        --input_space ${input_space} \\
        ${zscore}
    """

    stub:
    def label = AlgorithmSelection.BIDS_LABEL[algo]
    def space = task.ext.space ?: 'MNI'
    def kind  = algo == 'fast_outlier' ? 'zscore' : 'probseg'
    """
    touch ${meta.id}_space-${space}_desc-${label}_mask.nii.gz
    touch ${meta.id}_space-${space}_desc-${label}_${kind}.nii.gz
    echo '{}' > ${meta.id}_space-${space}_desc-${label}_mask.json
    """
}
