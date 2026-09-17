process QC_LONGITUDINAL {
    tag "$subject"

    container 'frheault/sf-lesionflow-segcsvd:rc03'

    input:
    tuple val(subject), path(audit_csv)

    output:
    tuple val(subject), path("${subject}_longitudinal_summary_mqc.tsv")  , emit: summary_tsv
    tuple val(subject), path("${subject}_trajectory_distribution_mqc.tsv"), emit: trajectories_tsv
    tuple val(subject), path("${subject}_lesion_instances_mqc.tsv")       , emit: instances_tsv
    tuple val(subject), path("*_mqc.tsv")                                 , emit: files
    path "versions.yml"                                                   , emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    """
    qc_longitudinal_summary.py \\
        --subject ${subject} \\
        --audit_csv ${audit_csv} \\
        --out_summary ${subject}_longitudinal_summary_mqc.tsv \\
        --out_trajectories ${subject}_trajectory_distribution_mqc.tsv \\
        --out_instances ${subject}_lesion_instances_mqc.tsv \\
        ${args}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "\$(python3 --version 2>&1 | awk '{print \$2}')"
        pandas: "\$(python3 -c "import pandas; print(pandas.__version__)")"
    END_VERSIONS
    """

    stub:
    """
    touch ${subject}_longitudinal_summary_mqc.tsv
    touch ${subject}_trajectory_distribution_mqc.tsv
    touch ${subject}_lesion_instances_mqc.tsv

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: "3.10.0"
        pandas: "2.0.0"
    END_VERSIONS
    """
}
