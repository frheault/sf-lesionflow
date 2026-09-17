process QC_REGISTRATION {
    tag "$meta.id"

    container 'frheault/sf-lesionflow-segcsvd:rc03'

    input:
    tuple val(meta), path(fixed), path(moving_warped)

    output:
    tuple val(meta), path("*_registration_metrics_mqc.tsv"), emit: metrics_tsv
    tuple val(meta), path("*_registration_*_mqc.png")      , emit: png
    tuple val(meta), path("*_mqc.*")                       , emit: files
    path "versions.yml"                                    , emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def stage = task.ext.stage ?: 'flair_to_t1'
    def args = task.ext.args ?: ''
    """
    qc_registration.py \\
        --meta_id ${meta.id} \\
        --stage ${stage} \\
        --fixed ${fixed} \\
        --moving_warped ${moving_warped} \\
        --out_metrics ${meta.id}_${stage}_registration_metrics_mqc.tsv \\
        --out_png ${meta.id}_registration_${stage}_mqc.png \\
        ${args}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "\$(python3 --version 2>&1 | awk '{print \$2}')"
        nibabel: "\$(python3 -c "import nibabel; print(nibabel.__version__)")"
        matplotlib: "\$(python3 -c "import matplotlib; print(matplotlib.__version__)")"
    END_VERSIONS
    """

    stub:
    def stage = task.ext.stage ?: 'flair_to_t1'
    """
    touch ${meta.id}_${stage}_registration_metrics_mqc.tsv
    touch ${meta.id}_registration_${stage}_mqc.png

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "3.10.0"
        nibabel: "5.0.0"
        matplotlib: "3.7.0"
    END_VERSIONS
    """
}
