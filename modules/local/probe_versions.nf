// Reports the real software/model versions of one algorithm from inside its own container.
// Runs once per pipeline run (not per session) and replaces the placeholder versions.yml of
// the SEGMENTATION_* processes in the collated software versions -- editing those processes'
// own version heredocs would invalidate their -resume cache.
process PROBE_VERSIONS {
    tag "$algo"
    container { AlgorithmSelection.CONTAINER[algo] }

    input:
    val(algo)

    output:
    path("${algo}_versions.yml"), emit: versions

    script:
    """
    probe_versions.sh ${algo} ${AlgorithmSelection.processName(algo)} "${task.container}" > ${algo}_versions.yml
    """

    stub:
    """
    printf '"%s":\\n    container: "%s"\\n' "${AlgorithmSelection.processName(algo)}" "${task.container ?: 'none'}" > ${algo}_versions.yml
    """
}
