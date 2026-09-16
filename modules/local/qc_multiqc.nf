process QC_MULTIQC {
    tag "$meta.id"
    label 'process_single'

    container "gagnonanthony/multiqc-neuroimaging:0.1.4"
    containerOptions((workflow.containerEngine == 'docker') ? '--entrypoint "" --user $(id -u):$(id -g)' : '')

    input:
    tuple val(meta), path(qc_files)
    path  multiqc_files
    path(multiqc_config)
    path(extra_multiqc_config)
    path(multiqc_logo)

    output:
    val(meta)           , emit: meta
    path("*.html")      , emit: report
    path("*_data")      , emit: data
    path("*_plots")     , optional: true, emit: plots
    path("versions.yml"), emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ? "${task.ext.prefix}-${workflow.start.format('yyMMdd-HHmm')}" : "${meta.id}-${workflow.start.format('yyMMdd-HHmm')}"
    def config = multiqc_config ? "--config ${multiqc_config}" : ''
    def extra_config = extra_multiqc_config ? "--config ${extra_multiqc_config}" : ''
    def logo = multiqc_logo ? "--cl-config 'custom_logo: \"${multiqc_logo}\"'" : ''
    def single_subject = task.ext.single_subject ? "--single-subject-report" : ""

    """
    multiqc \\
        --force \\
        ${args} \\
        ${config} \\
        --filename ${prefix}.html \\
        ${extra_config} \\
        ${logo} \\
        ${single_subject} \\
        .

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        multiqc: "\$(multiqc --version | sed -e "s/multiqc, version //g")"
        neuroimaging: "\$(pip list | grep neuroimaging | awk '{print \$2}')"
    END_VERSIONS
    """

    stub:
    def prefix = task.ext.prefix ? "${task.ext.prefix}-${workflow.start.format('yyMMdd-HHmm')}" : "${meta.id}-${workflow.start.format('yyMMdd-HHmm')}"
    """
    mkdir ${prefix}_data
    mkdir ${prefix}_plots
    touch ${prefix}.html

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        multiqc: "1.35"
        neuroimaging: "0.1.4"
    END_VERSIONS
    """
}
