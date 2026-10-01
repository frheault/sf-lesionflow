/**
 * Published (BIDS-derivatives style) names for every file sf-lesionflow publishes.
 *
 * Used from conf/output.config `publishDir.saveAs`, so the names in results/ are decoupled
 * from the names processes produce in work/ (renaming here never invalidates -resume).
 * Every method returns a path RELATIVE to the publishDir root (e.g. "anat/<name>"), or null
 * to not publish that file.
 */
class OutputNaming {

    // Rules for native preprocessing outputs: [work-dir suffix (after "<id>_<mod>"), published desc/suffix]
    static final List<List<String>> PREPROC_RULES = [
        ['_resampled.nii.gz',      'desc-resampled_%MOD%.nii.gz'],
        ['__bet_image.nii.gz',     'desc-synthstrip_%MOD%.nii.gz'],
        ['__brain_mask.nii.gz',    'desc-brain_mask.nii.gz'],
        ['_mask_cropped.nii.gz',   'desc-cropbrain_mask.nii.gz'],
        ['_mask_cropped_bbox.json','desc-crop_bbox.json'],
        ['_raw_cropped.nii.gz',    'desc-crop_%MOD%.nii.gz'],
        ['__image_n4.nii.gz',      'desc-n4_%MOD%.nii.gz'],
        ['_pren4_masked.nii.gz',   'desc-brain_%MOD%.nii.gz'],
        ['_masked.nii.gz',         'desc-n4brain_%MOD%.nii.gz'],
    ]

    /** RESAMPLE_*, SYNTHSTRIP_*, CROP_*, N4_*, MASK_* -> preproc/<id>_space-<T1w|FLAIR>_desc-..._<suffix> */
    static String preproc(String fn, Map meta, String modality) {
        if (fn == 'versions.yml') return null
        def token = modality == 'T1w' ? 't1' : 'flair'
        def head = "${meta.id}_${token}"
        if (!fn.startsWith(head)) return null
        def rest = fn.substring(head.length())
        for (rule in PREPROC_RULES) {
            if (rest == rule[0]) {
                return "preproc/${meta.id}_space-${modality}_${rule[1].replace('%MOD%', modality)}"
            }
        }
        return null
    }

    /** REGISTER_{FLAIR_TO_T1,T1_TO_BASELINE,BASELINE_TO_MNI} -> xfm/ transforms (+ one warped image in preproc/). */
    static String registration(String fn, Map meta, String stage, String space) {
        if (fn == 'versions.yml') return null
        def map = [
            flair_to_t1    : ['FLAIR', 'T1w'],
            t1_to_baseline : ['T1w', 'baseline'],
            baseline_to_mni: ['T1w', space],
        ]
        def (src, dst) = map[stage]
        if (fn.endsWith('_forward1_affine.mat'))  return "xfm/${meta.id}_from-${src}_to-${dst}_mode-image_xfm.mat"
        if (fn.endsWith('_backward0_affine.mat')) return "xfm/${meta.id}_from-${dst}_to-${src}_mode-image_xfm.mat"
        if (fn.endsWith('_warped.nii.gz')) {
            // FLAIR->T1w: the registered FLAIR is TrueNet's input and a useful product.
            // T1w->baseline / baseline->MNI: duplicates of anat/ outputs, not published.
            return stage == 'flair_to_t1' ? "preproc/${meta.id}_space-T1w_desc-n4brain_FLAIR.nii.gz" : null
        }
        return null
    }

    /** MNI anatomicals (TRANSFORM_*_TO_MNI, brain mask, SynthSeg) -> anat/ */
    static String anat(String fn, Map meta, String space) {
        if (fn == 'versions.yml') return null
        def id = meta.id
        def rules = [
            "${id}_t1_masked_space-MNI.nii.gz"                   : "desc-brain_T1w.nii.gz",
            "${id}_flair_masked_space-MNI.nii.gz"                : "desc-brain_FLAIR.nii.gz",
            "${id}_t1__image_n4_unstripped_space-MNI.nii.gz"     : "desc-head_T1w.nii.gz",
            "${id}_flair__image_n4_unstripped_space-MNI.nii.gz"  : "desc-head_FLAIR.nii.gz",
            "${id}_t1_mask_cropped_space-MNI.nii.gz"             : "desc-brain_mask.nii.gz",
            "${id}_synthseg.nii.gz"                              : "desc-synthseg_dseg.nii.gz",
        ].collectEntries { k, v -> [(k.toString()): v] }
        def out = rules[fn]
        return out ? "anat/${id}_space-${space}_${out}" : null
    }

    /** CONSENSUS_STAPLE -> consensus/ */
    static String consensus(String fn, Map meta, String space) {
        def id = meta.id
        if (fn == "${id}_staple_probmap.nii.gz")            return "consensus/${id}_space-${space}_desc-staple_probseg.nii.gz"
        if (fn == "${id}_staple_thr90_binary.nii.gz")       return "consensus/${id}_space-${space}_desc-staple_mask.nii.gz"
        if (fn == "${id}_staple_thr90_labels_uint16.nii.gz") return "consensus/${id}_space-${space}_desc-staple_dseg.nii.gz"
        return null
    }

    /** HARMONIZATION_STAPLE -> <subject>/longitudinal/ */
    static String harmonized(String fn, String subject, String space) {
        def m = fn =~ /^(${subject}_ses-[0-9A-Za-z]+)_staple_thr90_harmonized_(binary|labels_uint16)\.nii\.gz$/
        if (m.matches()) {
            return "${m.group(1)}_space-${space}_desc-harmonized_${m.group(2) == 'binary' ? 'mask' : 'dseg'}.nii.gz"
        }
        if (fn == "${subject}_staple_harmonized_lesion_tracking.csv") return "${subject}_space-${space}_desc-lesiontracking.csv"
        return null
    }

    /** Session QC TSV/PNG (QC_ENSEMBLE_METRICS, QC_REGISTRATION_*, QC_LESION_SCREENSHOT) -> qc/ */
    static String sessionQc(String fn, Map meta) {
        if (fn == 'versions.yml') return null
        def id = meta.id
        def fixed = [
            "${id}_ensemble_volumes_mqc.tsv"  : 'desc-ensemblevolumes_qc.tsv',
            "${id}_pairwise_dice_mqc.tsv"     : 'desc-pairwisedice_qc.tsv',
            "${id}_staple_summary_mqc.tsv"    : 'desc-staplesummary_qc.tsv',
            "${id}_lesion_brainmask_mqc.tsv"  : 'desc-brainmaskremoval_qc.tsv',
            "${id}_lesion_consensus_mqc.png"  : 'desc-consensus_qc.png',
        ].collectEntries { k, v -> [(k.toString()): v] }
        if (fixed[fn]) return "qc/${id}_${fixed[fn]}"
        def m = fn =~ /^${id}_(flair_to_t1|t1_to_baseline|baseline_to_mni)_registration_metrics_mqc\.tsv$/
        if (m.matches()) return "qc/${id}_desc-reg${m.group(1).replace('_', '')}_qc.tsv"
        m = fn =~ /^${id}_registration_(flair_to_t1|t1_to_baseline|baseline_to_mni)_mqc\.png$/
        if (m.matches()) return "qc/${id}_desc-reg${m.group(1).replace('_', '')}_qc.png"
        return null
    }

    /** QC_LONGITUDINAL -> <subject>/longitudinal/qc/ */
    static String longitudinalQc(String fn, String subject) {
        def m = fn =~ /^${subject}_(longitudinal_summary|trajectory_distribution|lesion_instances)_mqc\.tsv$/
        return m.matches() ? "qc/${subject}_desc-${m.group(1).replace('_', '')}_qc.tsv" : null
    }

    /** MultiQC report + data dir: stable names instead of a per-run timestamp. */
    static String multiqc(String fn, String stem) {
        if (fn == 'versions.yml') return null
        if (fn.endsWith('.html')) return "${stem}_multiqc_report.html"
        if (fn.endsWith('_data'))  return "${stem}_multiqc_report_data"
        if (fn.endsWith('_plots')) return "${stem}_multiqc_report_plots"
        return null
    }

    /** Raw native-space outputs of LST-AI/TrueNet/MARS-WMH/BAWIL/mindGlide (`<algo>.nii.gz`,
     *  `<algo>_prob.nii.gz`) -> native/ (only with --publish_native). */
    static String nativeOutput(String fn, Map meta) {
        def m = fn =~ /^(lst_ai|truenet|mars_wmh|bawil|mindglide)(_prob)?\.nii\.gz$/
        if (!m.matches()) return null
        def algo = m.group(1)
        def label = algo.replace('_', '')
        def space = algo == 'truenet' ? 'T1w' : 'FLAIR'
        def kind = fn.contains('prob') ? 'probseg' : 'mask'
        return "native/${meta.id}_space-${space}_desc-${label}_${kind}.nii.gz"
    }

    /** SEGMENTATION_MARS_WMH's own HTML QC report -> qc/ */
    static String marsQc(String fn, Map meta) {
        return fn == 'mars_wmh_QC.html' ? "qc/${meta.id}_desc-marswmh_qc.html" : null
    }
}
