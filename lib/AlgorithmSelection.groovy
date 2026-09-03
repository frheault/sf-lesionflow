class AlgorithmSelection {
    static final List<String> ALL = [
        'lst_ai', 'samseg', 'wmh_synthseg', 'fast_outlier', 'flames', 'truenet',
        'hypermapp3r', 'segcsvd', 'emory_robust', 'mars_wmh', 'bawil', 'mimosa', 'shivai'
    ]

    static Set<String> resolveActive(params) {
        if (params.algorithms && params.skip_algorithms) {
            throw new IllegalArgumentException("Specify either --algorithms or --skip_algorithms, not both.")
        }
        def active = params.algorithms
            ? (params.algorithms.toString().tokenize(',').collect { it.trim() } as Set)
            : params.skip_algorithms
                ? (ALL as Set) - (params.skip_algorithms.toString().tokenize(',').collect { it.trim() } as Set)
                : (ALL as Set)

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
