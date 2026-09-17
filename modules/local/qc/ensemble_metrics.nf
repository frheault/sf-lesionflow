process QC_ENSEMBLE_METRICS {
    tag "$meta.id"

    container 'frheault/sf-lesionflow-segcsvd:rc03'

    input:
    tuple val(meta), path(consensus), path(masks)

    output:
    tuple val(meta), path("${meta.id}_ensemble_volumes_mqc.tsv"), emit: volumes_tsv
    tuple val(meta), path("${meta.id}_pairwise_dice_mqc.tsv")    , emit: dice_tsv
    tuple val(meta), path("${meta.id}_staple_summary_mqc.tsv")   , emit: summary_tsv
    tuple val(meta), path("*.tsv")                              , emit: files
    path "versions.yml"                                         , emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    """
    qc_ensemble_metrics.py \\
        --meta_id ${meta.id} \\
        --consensus ${consensus} \\
        --masks ${masks} \\
        --out_volumes ${meta.id}_ensemble_volumes_mqc.tsv \\
        --out_dice ${meta.id}_pairwise_dice_mqc.tsv \\
        --out_summary ${meta.id}_staple_summary_mqc.tsv \\
        ${args}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "\$(python3 --version 2>&1 | awk '{print \$2}')"
        nibabel: "\$(python3 -c "import nibabel; print(nibabel.__version__)")"
        scipy: "\$(python3 -c "import scipy; print(scipy.__version__)")"
    END_VERSIONS
    """

    stub:
    """
    touch ${meta.id}_ensemble_volumes_mqc.tsv
    touch ${meta.id}_pairwise_dice_mqc.tsv
    touch ${meta.id}_staple_summary_mqc.tsv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "3.10.0"
        nibabel: "5.0.0"
        scipy: "1.10.0"
    END_VERSIONS
    """
}
