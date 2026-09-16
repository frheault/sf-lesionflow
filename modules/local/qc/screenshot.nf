process QC_LESION_SCREENSHOT {
    tag "$meta.id"
    label 'process_single'

    container 'frheault/sf-lesionflow-segcsvd:rc03'

    input:
    tuple val(meta), path(flair), path(mask)

    output:
    tuple val(meta), path("${meta.id}_lesion_consensus_mqc.png"), emit: png
    path "versions.yml"                                         , emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    """
    qc_lesion_screenshot.py \\
        --meta_id ${meta.id} \\
        --anat ${flair} \\
        --mask ${mask} \\
        --out_png ${meta.id}_lesion_consensus_mqc.png \\
        ${args}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "\$(python3 --version 2>&1 | awk '{print \$2}')"
        nibabel: "\$(python3 -c "import nibabel; print(nibabel.__version__)")"
        matplotlib: "\$(python3 -c "import matplotlib; print(matplotlib.__version__)")"
    END_VERSIONS
    """

    stub:
    """
    touch ${meta.id}_lesion_consensus_mqc.png

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "3.10.0"
        nibabel: "5.0.0"
        matplotlib: "3.7.0"
    END_VERSIONS
    """
}
