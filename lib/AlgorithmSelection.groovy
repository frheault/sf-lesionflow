class AlgorithmSelection {
    static final List<String> ALL = [
        'lst_ai', 'samseg', 'wmh_synthseg', 'fast_outlier', 'flames', 'truenet',
        'hypermapp3r', 'segcsvd', 'emory_robust', 'mars_wmh', 'bawil', 'mimosa', 'shivai',
        'mindglide'
    ]

    static final List<String> DEFAULT = [
        'lst_ai', 'samseg', 'wmh_synthseg', 'flames',
        'hypermapp3r', 'segcsvd', 'emory_robust', 'mars_wmh', 'bawil', 'mimosa', 'shivai',
        'mindglide'
    ]

    // BIDS-derivatives `desc-` label of each algorithm (alphanumeric only, as BIDS requires).
    // Mirrored in bin/_lesion_utils.py (BIDS_LABEL) -- tests/test_qc_metrics.py asserts both match.
    static final Map<String, String> BIDS_LABEL = [
        lst_ai: 'lstai', samseg: 'samseg', wmh_synthseg: 'wmhsynthseg', fast_outlier: 'fastoutlier',
        flames: 'flames', truenet: 'truenet', hypermapp3r: 'hypermapp3r', segcsvd: 'segcsvd',
        emory_robust: 'emoryrobust', mars_wmh: 'marswmh', bawil: 'bawil', mimosa: 'mimosa',
        shivai: 'shivai', mindglide: 'mindglide'
    ]

    // Algorithms whose input image still contains the skull/scalp (see the `// input:` comments
    // in main.nf). Their MNI predictions are multiplied by the MNI brain mask in LESION_FINALIZE
    // (--lesion_brainmask unstripped, the default).
    static final Set<String> UNSTRIPPED_INPUT = ['samseg', 'wmh_synthseg', 'mars_wmh', 'bawil', 'mindglide'] as Set

    // Container image of each algorithm's SEGMENTATION_* process (used by PROBE_VERSIONS to report
    // versions from inside the very same image). Keep in sync with modules/local/lesion_segmentation.nf
    // -- tests/validate_outputs.py --check-containers compares the two.
    static final Map<String, String> CONTAINER = [
        lst_ai      : 'frheault/sf-lesionflow-lst_ai:1.1.0',
        samseg      : 'freesurfer/freesurfer:7.4.1',
        wmh_synthseg: 'frheault/sf-lesionflow-wmh_synthseg:1.0.0',
        fast_outlier: 'frheault/sf-lesionflow-fast_outlier:1.0.0',
        flames      : 'frheault/sf-lesionflow-flames:1.0.0',
        truenet     : 'frheault/sf-lesionflow-truenet:1.0.0',
        hypermapp3r : 'mgoubran/hypermapper:latest',
        segcsvd     : 'frheault/sf-lesionflow-segcsvd:rc03',
        emory_robust: 'emorycn2l/emory_robust_wmh:v1.2',
        mars_wmh    : 'ghcr.io/miac-research/wmh-nnunet:1.0.2',
        bawil       : 'frheault/sf-lesionflow-bawil:1.0.0',
        mimosa      : 'frheault/sf-lesionflow-mimosa:1.0.0',
        shivai      : 'frheault/sf-lesionflow-shivai:1.0.0',
        mindglide   : 'frheault/sf-lesionflow-mindglide:1.0.0',
        synthseg    : 'freesurfer/freesurfer:7.4.1'   // PREPROC_SYNTHSEG (SegCSVD's parcellation input)
    ]

    // Space each algorithm's own input lives in (reported in the LESION_FINALIZE sidecar).
    static final Map<String, String> INPUT_SPACE = [
        lst_ai: 'native-FLAIR', truenet: 'native-T1w', mars_wmh: 'native-FLAIR', bawil: 'native-FLAIR',
        mindglide: 'native-FLAIR'
    ].withDefault { 'MNI' }

    // Process name whose placeholder versions.yml PROBE_VERSIONS replaces.
    static String processName(String key) {
        return key == 'synthseg' ? 'PREPROC_SYNTHSEG' : "SEGMENTATION_${key.toUpperCase()}"
    }

    static Set<String> brainmaskTargets(params) {
        def mode = (params.lesion_brainmask ?: 'unstripped').toString()
        switch (mode) {
            case 'all':        return ALL as Set
            case 'none':       return [] as Set
            case 'unstripped': return UNSTRIPPED_INPUT
            default: throw new IllegalArgumentException("--lesion_brainmask must be one of unstripped|all|none (got '${mode}')")
        }
    }

    static Set<String> resolveActive(params) {
        if (params.algorithms && params.skip_algorithms) {
            throw new IllegalArgumentException("Specify either --algorithms or --skip_algorithms, not both.")
        }
        def active = params.algorithms
            ? (params.algorithms.toString() == 'all'
                ? (ALL as Set)
                : (params.algorithms.toString().tokenize(',').collect { it.trim() } as Set))
            : params.skip_algorithms
                ? (DEFAULT as Set) - (params.skip_algorithms.toString().tokenize(',').collect { it.trim() } as Set)
                : (DEFAULT as Set)

        def unknown = active - (ALL as Set)
        if (unknown) {
            throw new IllegalArgumentException(
                "Unknown algorithm(s): ${unknown.join(', ')}. Valid options: ${ALL.join(', ')}")
        }
        if (active.isEmpty()) {
            throw new IllegalArgumentException("--skip_algorithms excludes every algorithm -- nothing left to run.")
        }
        return active
    }

    static boolean isActive(String key, params) {
        return key in resolveActive(params)
    }
}
