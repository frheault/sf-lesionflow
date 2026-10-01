#!/usr/bin/env nextflow

def helpMessage() {
    log.info"""
    ================================================================================
    Multiple Sclerosis Lesion Segmentation Pipeline (sf-lesionflow) v${workflow.manifest.version}
    ================================================================================

    Usage:
    nextflow run main.nf --input /path/to/bids_dataset \\
                         --mni_template /path/to/mni_masked.nii.gz \\
                         --fs_license /path/to/license.txt \\
                         -profile docker -resume

    Mandatory arguments:
      --input [path]                Input directory containing BIDS subjects (sub-*/ses-*/anat/*).
      --mni_template [path]         Path to standard MNI reference template (nii.gz).
      --fs_license [path]           Path to FreeSurfer license file (required for SAMSEG).

    Optional arguments:
      --participant_label [str]     Filter subjects by comma-separated IDs (e.g. 'sub-001,sub-002').
      --output [path]               Directory to publish results (default: '${params.output}').
      --algorithms [str]            Comma-separated allow-list of algorithms to run (e.g. 'lst_ai,samseg').
                                    Valid options: ${AlgorithmSelection.ALL.join(', ')}.
      --skip_algorithms [str]       Comma-separated deny-list of algorithms to skip (e.g. 'emory_robust').
      --max_memory [str]            Warn about algorithms exceeding this memory limit (e.g. '20.GB').
      --staple_threshold [float]    STAPLE consensus probability threshold (default: 0.90).
      --staple_min_cluster_size [int] Minimum lesion cluster size in voxels/mm3 (default: 6).
      --staple_min_distance [int]   Minimum peak distance for watershed instances (default: 3).
      --staple_gaussian_sigma [float] Gaussian smoothing sigma for distance transform (default: 0.8).
      --pct_change_threshold [float] Percentage volume change threshold for trajectory status (default: 20.0).
      --lesion_brainmask [str]      Brain-mask lesion predictions: 'unstripped' (algorithms fed images with skull,
                                    default), 'all' or 'none'.
      --lesion_brainmask_dilation [int] Brain mask dilation in voxels before masking (default: 1).
      --template_space [str]        BIDS space- label of the template grid (default: 'MNI').
      --publish_dir_mode [str]      Nextflow publishDir mode (default: 'symlink'; use 'copy' to archive results).
      --publish_intermediates [bool] Publish native-space preprocessing under ses-*/preproc/ (default: true).
      --publish_native [bool]       Also publish native-space lesion outputs under ses-*/native/ (default: false).
      --help                        Display this help message.
    """.stripIndent()
}

// Default parameters
params.input                   = false
params.mni_template            = false
params.fs_license              = false
params.participant_label       = false
params.output                  = "results"
params.help                    = false
params.algorithms              = false
params.skip_algorithms         = false
params.max_memory              = false
params.staple_threshold        = 0.90
params.staple_min_cluster_size = 6
params.staple_min_distance     = 3
params.staple_gaussian_sigma   = 0.8
params.pct_change_threshold    = 20.0
params.lesion_brainmask        = 'unstripped'
params.lesion_brainmask_dilation = 1
params.template_space          = 'MNI'
params.publish_dir_mode        = 'symlink'
params.publish_intermediates   = true
params.publish_native          = false

if (params.help) {
    helpMessage()
    exit 0
}

// -----------------------------------------------------------------------------
// Standard Module Imports (nf-neuro)
// -----------------------------------------------------------------------------
include { IMAGE_RESAMPLE as RESAMPLE_T1 }                  from './modules/nf-neuro/image/resample/main'
include { IMAGE_RESAMPLE as RESAMPLE_FLAIR }               from './modules/nf-neuro/image/resample/main'
include { BETCROP_SYNTHSTRIP as SYNTHSTRIP_T1 }            from './modules/nf-neuro/betcrop/synthstrip/main'
include { BETCROP_SYNTHSTRIP as SYNTHSTRIP_FLAIR }         from './modules/nf-neuro/betcrop/synthstrip/main'
include { PREPROC_N4 as N4_T1 }                            from './modules/nf-neuro/preproc/n4/main'
include { PREPROC_N4 as N4_FLAIR }                         from './modules/nf-neuro/preproc/n4/main'
include { IMAGE_APPLYMASK as MASK_T1 }                     from './modules/nf-neuro/image/applymask/main'
include { IMAGE_APPLYMASK as MASK_FLAIR }                  from './modules/nf-neuro/image/applymask/main'
include { IMAGE_CROPVOLUME as CROP_T1_MASK }               from './modules/nf-neuro/image/cropvolume/main'
include { IMAGE_CROPVOLUME as CROP_T1_RAW }                from './modules/nf-neuro/image/cropvolume/main'
include { IMAGE_CROPVOLUME as CROP_FLAIR_RAW }             from './modules/nf-neuro/image/cropvolume/main'
include { IMAGE_CROPVOLUME as CROP_FLAIR_MASK }            from './modules/nf-neuro/image/cropvolume/main'

include { REGISTRATION_ANTS as REGISTER_FLAIR_TO_T1 }      from './modules/nf-neuro/registration/ants/main'
include { REGISTRATION_ANTS as REGISTER_T1_TO_BASELINE }   from './modules/nf-neuro/registration/ants/main'
include { REGISTRATION_ANTS as REGISTER_BASELINE_TO_MNI }  from './modules/nf-neuro/registration/ants/main'

include { IMAGE_APPLYMASK as MASK_T1_PRE_N4 }                                     from './modules/nf-neuro/image/applymask/main'
include { IMAGE_APPLYMASK as MASK_FLAIR_PRE_N4 }                                  from './modules/nf-neuro/image/applymask/main'

include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_T1W_TO_MNI }            from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_FLAIR_TO_MNI }          from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_T1W_UNSTRIPPED_TO_MNI } from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_FLAIR_UNSTRIPPED_TO_MNI } from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_MARS_WMH_MASK_TO_MNI }   from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_LST_AI_MASK_TO_MNI }     from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_MINDGLIDE_MASK_TO_MNI }   from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_BAWIL_MASK_TO_MNI }       from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_TRUENET_MASK_TO_MNI }     from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_MARS_WMH_PROB_TO_MNI }   from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_LST_AI_PROB_TO_MNI }     from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_MINDGLIDE_PROB_TO_MNI }   from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_BAWIL_PROB_TO_MNI }       from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_TRUENET_PROB_TO_MNI }     from './modules/nf-neuro/registration/antsapplytransforms/main'
include { REGISTRATION_ANTSAPPLYTRANSFORMS as TRANSFORM_T1_BRAINMASK_TO_MNI }     from './modules/nf-neuro/registration/antsapplytransforms/main'

// -----------------------------------------------------------------------------
// Local Module Imports (Phase 2 to 5)
// -----------------------------------------------------------------------------
include {
    SEGMENTATION_LST_AI;
    SEGMENTATION_SAMSEG;
    SEGMENTATION_WMH_SYNTHSEG;
    SEGMENTATION_FAST_OUTLIER;
    SEGMENTATION_FLAMES;
    SEGMENTATION_TRUENET;
    SEGMENTATION_HYPERMAPP3R;
    PREPROC_SYNTHSEG;
    SEGMENTATION_SEGCSVD;
    SEGMENTATION_EMORY_ROBUST;
    SEGMENTATION_MARS_WMH;
    SEGMENTATION_BAWIL;
    SEGMENTATION_MIMOSA;
    SEGMENTATION_SHIVAI;
    SEGMENTATION_MINDGLIDE;
    CONSENSUS_STAPLE;
    HARMONIZATION_STAPLE
} from './modules/local/lesion_segmentation'

include { LESION_FINALIZE } from './modules/local/lesion_finalize'
include { PROBE_VERSIONS  } from './modules/local/probe_versions'
include { QC_PIPELINE     } from './subworkflows/local/qc_pipeline'

// -----------------------------------------------------------------------------
// Channel Ingestion Workflow
// -----------------------------------------------------------------------------
workflow get_data {
    main:
        if (!params.input) {
            error "Mandatory argument --input missing. Please provide the BIDS dataset directory."
        }
        if (!params.mni_template) {
            error "Mandatory argument --mni_template missing. Please provide the MNI reference template."
        }
        if (!params.fs_license) {
            error "Mandatory argument --fs_license missing. Please provide the FreeSurfer license file."
        }

        input_dir = file(params.input)

        def allowed_participants = params.participant_label
            ? (params.participant_label.toString().tokenize(',').collect { it.trim().replaceFirst('^sub-', '') } as Set)
            : null

        // Loading T1w files (BIDS structure: sub-*/ses-*/anat/*T1w.nii.gz)
        ch_t1 = Channel.fromPath("${input_dir}/sub-*/ses-*/anat/*T1w.nii.gz")
            .map { f ->
                def sid = f.parent.parent.parent.name
                def ses = f.parent.parent.name
                [ [id: "${sid}_${ses}", subject: sid, session: ses], f ]
            }
            .filter { meta, f ->
                !allowed_participants || allowed_participants.contains(meta.subject.replaceFirst('^sub-', ''))
            }
            .ifEmpty { error "No T1w files found in ${input_dir} matching sub-*/ses-*/anat/*T1w.nii.gz${params.participant_label ? " for participant(s): ${params.participant_label}" : ''}" }

        // Loading FLAIR files (BIDS structure: sub-*/ses-*/anat/*FLAIR.nii.gz)
        ch_flair = Channel.fromPath("${input_dir}/sub-*/ses-*/anat/*FLAIR.nii.gz")
            .map { f ->
                def sid = f.parent.parent.parent.name
                def ses = f.parent.parent.name
                [ [id: "${sid}_${ses}", subject: sid, session: ses], f ]
            }
            .filter { meta, f ->
                !allowed_participants || allowed_participants.contains(meta.subject.replaceFirst('^sub-', ''))
            }
            .ifEmpty { error "No FLAIR files found in ${input_dir} matching sub-*/ses-*/anat/*FLAIR.nii.gz${params.participant_label ? " for participant(s): ${params.participant_label}" : ''}" }

        ch_mni_template = Channel.fromPath(params.mni_template, checkIfExists: true)
        ch_fs_license   = Channel.fromPath(params.fs_license, checkIfExists: true)

    emit:
        t1           = ch_t1
        flair        = ch_flair
        mni_template = ch_mni_template
        fs_license   = ch_fs_license
}

// -----------------------------------------------------------------------------
// Algorithm Selection & Resource Preflight Check
// -----------------------------------------------------------------------------
// Resolved once at parse time (params are CLI-time, not channel/runtime values) --
// active_algorithms.size() below is therefore a plain constant by the time
// groupTuple(size:) sees it. Do NOT replace this with anything computed from a
// channel (e.g. `.count()`) -- Nextflow's groupTuple(size:) only accepts a
// resolved-at-parse-time value, confirmed via nextflow-io/nextflow#1702.
def active_algorithms = AlgorithmSelection.resolveActive(params)  // throws immediately if params are invalid
log.info "Active segmentation algorithms (${active_algorithms.size()}/${AlgorithmSelection.ALL.size()}): ${active_algorithms.join(', ')}"
if (active_algorithms.size() == 1) {
    log.warn "Only one algorithm active (${active_algorithms[0]}) -- CONSENSUS_STAPLE will degenerate to that single mask, not a real consensus."
}

// Declared, hand-maintained approximation of each algorithm's peak memory need,
// mirroring the labels in conf/base.config / conf/local_dev.config. NOT introspected
// live from the active Nextflow config -- if those files' memory values change,
// update this table too, or this check will quietly go stale.
def ALGORITHM_MEMORY_GB = [
    lst_ai: 8, samseg: 16, wmh_synthseg: 16, fast_outlier: 8, flames: 8,
    truenet: 16, hypermapp3r: 16, segcsvd: 8, emory_robust: 16, mars_wmh: 8,
    bawil: 8, mimosa: 8, shivai: 8, mindglide: 8
]
assert ALGORITHM_MEMORY_GB.keySet() == AlgorithmSelection.ALL as Set  // fails loudly if the two lists ever diverge
assert AlgorithmSelection.BIDS_LABEL.keySet() == AlgorithmSelection.ALL as Set
assert AlgorithmSelection.UNSTRIPPED_INPUT.every { it in AlgorithmSelection.ALL }
assert AlgorithmSelection.ALL.every { AlgorithmSelection.CONTAINER.containsKey(it) }
def brainmask_targets = AlgorithmSelection.brainmaskTargets(params)  // validates --lesion_brainmask
log.info "Lesion brain masking (--lesion_brainmask ${params.lesion_brainmask}): ${(active_algorithms.intersect(brainmask_targets) ?: ['none']).join(', ')}"

if (params.max_memory) {
    def max_gb = (params.max_memory as nextflow.util.MemoryUnit).toGiga()
    def oversized = active_algorithms.findAll { ALGORITHM_MEMORY_GB[it] > max_gb }
    if (oversized) {
        log.warn """\
        --max_memory ${params.max_memory} is below the declared requirement for:
        ${oversized.collect { "  - ${it} (~${ALGORITHM_MEMORY_GB[it]}GB)" }.join('\n')}
        These will likely fail or be OOM-killed under this limit.
        Exclude them with --skip_algorithms ${oversized.join(',')}, or raise --max_memory.
        """.stripIndent()
    }
}

// -----------------------------------------------------------------------------
// Main Pipeline Execution DAG
// -----------------------------------------------------------------------------
workflow {
    data = get_data()

    // =========================================================================
    // PHASE 1: Preprocessing, Coregistration & Standard Space Projection
    // =========================================================================

    // 1. Resample T1w & FLAIR to isotropic 1x1x1mm
    RESAMPLE_T1(data.t1.map { meta, t1 -> [meta, t1, []] })
    RESAMPLE_FLAIR(data.flair.map { meta, flair -> [meta, flair, []] })

    // 2. Skull Strip via SynthStrip
    SYNTHSTRIP_T1(RESAMPLE_T1.out.image.map { meta, img -> [meta, img, []] })
    SYNTHSTRIP_FLAIR(RESAMPLE_FLAIR.out.image.map { meta, img -> [meta, img, []] })

    // 3. Native Space Bounding-Box Cropping (nf-neuro IMAGE_CROPVOLUME)
    // Each modality is cropped using a bounding box computed from its OWN brain
    // mask, not a shared one — T1 and FLAIR are not yet co-registered at this
    // point, and their acquisitions can differ enough in orientation/obliqueness
    // that a world-space box from one collapses to a near-empty crop on the other.
    CROP_T1_MASK(SYNTHSTRIP_T1.out.brain_mask.map { meta, mask -> [meta, mask, []] })
    CROP_T1_RAW(RESAMPLE_T1.out.image.join(CROP_T1_MASK.out.bounding_box))
    CROP_FLAIR_MASK(SYNTHSTRIP_FLAIR.out.brain_mask.map { meta, mask -> [meta, mask, []] })
    CROP_FLAIR_RAW(RESAMPLE_FLAIR.out.image.join(CROP_FLAIR_MASK.out.bounding_box))

    // 4. N4 Bias Field Correction (Optimized on Cropped Native FOV)
    ch_n4_t1_in = CROP_T1_RAW.out.image
        .join(CROP_T1_MASK.out.image)
        .map { meta, img, mask -> [meta, img, [], [], mask] }
    N4_T1(ch_n4_t1_in)

    ch_n4_flair_in = CROP_FLAIR_RAW.out.image
        .join(CROP_FLAIR_MASK.out.image)
        .map { meta, img, mask -> [meta, img, [], [], mask] }
    N4_FLAIR(ch_n4_flair_in)

    // 5. Extract skull-stripped masked images
    MASK_T1(N4_T1.out.image.join(CROP_T1_MASK.out.image))
    MASK_FLAIR(N4_FLAIR.out.image.join(CROP_FLAIR_MASK.out.image))

    // Pre-N4 skull-stripped images for algorithms that deliberately exclude N4 bias correction (LST-AI)
    MASK_T1_PRE_N4(CROP_T1_RAW.out.image.join(CROP_T1_MASK.out.image))
    MASK_FLAIR_PRE_N4(CROP_FLAIR_RAW.out.image.join(CROP_FLAIR_MASK.out.image))

    // 6. Intra-session FLAIR to T1w Rigid Registration
    ch_flair_to_t1 = MASK_T1.out.image
        .join(MASK_FLAIR.out.image)
        .map { meta, t1, flair -> [meta, t1, flair, [], []] }
    REGISTER_FLAIR_TO_T1(ch_flair_to_t1)

    // 7. Longitudinal Registration: Session T1w to Baseline T1w
    // Baseline is defined as the first chronological session (e.g. ses-1)
    ch_grouped_t1 = MASK_T1.out.image
        .map { meta, img -> [meta.subject, meta, img] }
        .groupTuple(by: 0)
        .flatMap { subject, metas, imgs ->
            def sorted = [metas, imgs].transpose().sort { a, b -> a[0].session <=> b[0].session }
            def baseline_meta = sorted[0][0]
            def baseline_img  = sorted[0][1]
            sorted.collect { meta, img ->
                [ meta, baseline_img, img, (meta.session == baseline_meta.session) ]
            }
        }

    // Separate baseline session from follow-up sessions
    ch_baseline_t1 = ch_grouped_t1.filter { meta, base_img, cur_img, is_base -> is_base }
        .map { meta, base_img, cur_img, is_base -> [meta, cur_img] }
    ch_followup_t1 = ch_grouped_t1.filter { meta, base_img, cur_img, is_base -> !is_base }
        .map { meta, base_img, cur_img, is_base -> [meta, base_img, cur_img, [], []] }

    REGISTER_T1_TO_BASELINE(ch_followup_t1)

    // 8. Standard Space Registration: Baseline T1w to MNI Template
    ch_base_to_mni = ch_baseline_t1
        .combine(data.mni_template)
        .map { meta, t1, mni -> [meta, mni, t1, [], []] }
    REGISTER_BASELINE_TO_MNI(ch_base_to_mni)

    // 9. Transform Composition & MNI Warping
    // Baseline MNI transform channel
    ch_mni_affine = REGISTER_BASELINE_TO_MNI.out.forward_affine
        .map { meta, aff -> [meta.subject, aff] }

    // Followup intra-subject transform channel
    ch_intra_affine = REGISTER_T1_TO_BASELINE.out.forward_affine
        .map { meta, aff -> [meta.id, aff] }

    // Assemble transformation lists per session for T1w & FLAIR
    ch_session_transforms = MASK_T1.out.image
        .map { meta, img -> [meta.subject, meta] }
        .combine(ch_mni_affine, by: 0)
        .map { subject, meta, mni_aff ->
            [meta.id, meta, mni_aff]
        }
        // Left join intra-subject affine (if followup session)
        .join(ch_intra_affine, remainder: true)
        .join(REGISTER_FLAIR_TO_T1.out.forward_affine.map { meta, aff -> [meta.id, aff] })
        .map { id, meta, mni_aff, intra_aff, flair_aff ->
            def t1_transforms    = intra_aff ? [mni_aff, intra_aff] : [mni_aff]
            def flair_transforms = intra_aff ? [mni_aff, intra_aff, flair_aff] : [mni_aff, flair_aff]
            [ meta, t1_transforms, flair_transforms ]
        }

    // Apply Transforms to Stripped Volumes
    ch_warp_t1 = MASK_T1.out.image
        .join(ch_session_transforms.map { meta, t1_tx, fl_tx -> [meta, t1_tx] })
        .combine(data.mni_template)
        .map { meta, img, txs, mni -> [meta, img, mni, txs] }
    TRANSFORM_T1W_TO_MNI(ch_warp_t1)

    ch_warp_flair = MASK_FLAIR.out.image
        .join(ch_session_transforms.map { meta, t1_tx, fl_tx -> [meta, fl_tx] })
        .combine(data.mni_template)
        .map { meta, img, txs, mni -> [meta, img, mni, txs] }
    TRANSFORM_FLAIR_TO_MNI(ch_warp_flair)

    // Apply Transforms to Unstripped Volumes (for SAMSEG & WMH-SynthSeg)
    ch_warp_t1_unstripped = N4_T1.out.image
        .join(ch_session_transforms.map { meta, t1_tx, fl_tx -> [meta, t1_tx] })
        .combine(data.mni_template)
        .map { meta, img, txs, mni -> [meta, img, mni, txs] }
    TRANSFORM_T1W_UNSTRIPPED_TO_MNI(ch_warp_t1_unstripped)

    ch_warp_flair_unstripped = N4_FLAIR.out.image
        .join(ch_session_transforms.map { meta, t1_tx, fl_tx -> [meta, fl_tx] })
        .combine(data.mni_template)
        .map { meta, img, txs, mni -> [meta, img, mni, txs] }
    TRANSFORM_FLAIR_UNSTRIPPED_TO_MNI(ch_warp_flair_unstripped)

    // Helper closure to reliably extract the 3D MNI warped NIfTI when ANTs emits multiple files
    def toMniSpace = { meta, imgs -> [meta, imgs instanceof List ? imgs.find { it.name.endsWith('space-MNI.nii.gz') } : imgs] }

    ch_t1_mni               = TRANSFORM_T1W_TO_MNI.out.warped_image.map(toMniSpace)
    ch_flair_mni            = TRANSFORM_FLAIR_TO_MNI.out.warped_image.map(toMniSpace)
    ch_t1_unstripped_mni    = TRANSFORM_T1W_UNSTRIPPED_TO_MNI.out.warped_image.map(toMniSpace)
    ch_flair_unstripped_mni = TRANSFORM_FLAIR_UNSTRIPPED_TO_MNI.out.warped_image.map(toMniSpace)

    // T1 SynthStrip brain mask (cropped T1 grid) -> MNI, NearestNeighbor. Used to restrict the
    // predictions of algorithms fed unstripped images (LESION_FINALIZE) and published in anat/.
    ch_warp_brainmask = CROP_T1_MASK.out.image
        .join(ch_session_transforms.map { meta, t1_tx, fl_tx -> [meta, t1_tx] })
        .combine(data.mni_template)
        .map { meta, img, txs, mni -> [meta, img, mni, txs] }
    TRANSFORM_T1_BRAINMASK_TO_MNI(ch_warp_brainmask)
    ch_brainmask_mni = TRANSFORM_T1_BRAINMASK_TO_MNI.out.warped_image.map(toMniSpace)

    // Channel bundles for MNI inputs
    ch_mni_paired     = ch_t1_mni.join(ch_flair_mni)
    ch_mni_flair_only = ch_flair_mni
    ch_mni_unstripped = ch_t1_unstripped_mni.join(ch_flair_unstripped_mni)

    // =========================================================================
    // PHASE 2: Independent Algorithm Execution (Parallelized)
    // =========================================================================

    // Helper closure to extract single 3D mask from ANTs transformation output
    def toSingleMask = { meta, imgs -> [meta, imgs instanceof List ? imgs[0] : imgs] }

    // [meta, native_image] -> [meta, native_image, mni_template, transforms] using the FLAIR
    // (fl_tx) or T1 (t1_tx) transform chain of the session.
    def withTransforms = { ch, which ->
        ch.join(ch_session_transforms.map { meta, t1_tx, fl_tx -> [meta, which == 't1' ? t1_tx : fl_tx] })
          .combine(data.mni_template)
          .map { meta, img, txs, mni -> [meta, img, mni, txs] }
    }

    // LST-AI: runs on native pre-N4 skull-stripped T1+FLAIR, output mask is warped to MNI space
    ch_lst_ai_in = MASK_T1_PRE_N4.out.image.join(MASK_FLAIR_PRE_N4.out.image)
    SEGMENTATION_LST_AI(ch_lst_ai_in)

    ch_warp_lst_ai_mask = SEGMENTATION_LST_AI.out.binary_mask
        .join(ch_session_transforms.map { meta, t1_tx, fl_tx -> [meta, fl_tx] })
        .combine(data.mni_template)
        .map { meta, mask, txs, mni -> [meta, mask, mni, txs] }
    TRANSFORM_LST_AI_MASK_TO_MNI(ch_warp_lst_ai_mask)
    ch_lst_ai_mni_mask = TRANSFORM_LST_AI_MASK_TO_MNI.out.warped_image.map(toSingleMask)
    TRANSFORM_LST_AI_PROB_TO_MNI(withTransforms(SEGMENTATION_LST_AI.out.probability_map, 'flair'))
    ch_lst_ai_mni_prob = TRANSFORM_LST_AI_PROB_TO_MNI.out.warped_image.map(toSingleMask)

    SEGMENTATION_SAMSEG(ch_mni_unstripped.combine(data.fs_license))   // input: MNI unstripped
    SEGMENTATION_WMH_SYNTHSEG(ch_flair_unstripped_mni)                 // input: MNI unstripped
    SEGMENTATION_FAST_OUTLIER(ch_mni_paired)                           // input: MNI stripped
    SEGMENTATION_FLAMES(ch_mni_flair_only)                             // input: MNI stripped

    // TrueNet: runs on native skull-stripped co-registered T1+FLAIR, output mask is warped to MNI space
    ch_native_truenet_in = MASK_T1.out.image.join(REGISTER_FLAIR_TO_T1.out.image_warped)
    SEGMENTATION_TRUENET(ch_native_truenet_in)

    ch_warp_truenet_mask = SEGMENTATION_TRUENET.out.binary_mask
        .join(ch_session_transforms.map { meta, t1_tx, fl_tx -> [meta, t1_tx] })
        .combine(data.mni_template)
        .map { meta, mask, txs, mni -> [meta, mask, mni, txs] }
    TRANSFORM_TRUENET_MASK_TO_MNI(ch_warp_truenet_mask)
    ch_truenet_mni_mask = TRANSFORM_TRUENET_MASK_TO_MNI.out.warped_image.map(toSingleMask)
    TRANSFORM_TRUENET_PROB_TO_MNI(withTransforms(SEGMENTATION_TRUENET.out.probability_map, 't1'))
    ch_truenet_mni_prob = TRANSFORM_TRUENET_PROB_TO_MNI.out.warped_image.map(toSingleMask)

    SEGMENTATION_HYPERMAPP3R(ch_mni_paired)                            // input: MNI stripped

    // SegCSVD: requires real FreeSurfer SynthSeg parcellation as documented
    PREPROC_SYNTHSEG(ch_mni_flair_only)
    ch_segcsvd_in = ch_mni_flair_only.join(PREPROC_SYNTHSEG.out.synthseg)
    SEGMENTATION_SEGCSVD(ch_segcsvd_in)

    SEGMENTATION_EMORY_ROBUST(ch_mni_paired)                           // input: MNI stripped

    // MARS-WMH: runs on native-space unstripped inputs, then output mask is warped to MNI space
    ch_native_unstripped_paired = N4_T1.out.image.join(N4_FLAIR.out.image)
    SEGMENTATION_MARS_WMH(ch_native_unstripped_paired)                 // input: native unstripped

    ch_warp_mars_wmh_mask = SEGMENTATION_MARS_WMH.out.binary_mask
        .join(ch_session_transforms.map { meta, t1_tx, fl_tx -> [meta, fl_tx] })
        .combine(data.mni_template)
        .map { meta, mask, txs, mni -> [meta, mask, mni, txs] }
    TRANSFORM_MARS_WMH_MASK_TO_MNI(ch_warp_mars_wmh_mask)
    ch_mars_wmh_mni_mask = TRANSFORM_MARS_WMH_MASK_TO_MNI.out.warped_image.map(toSingleMask)
    TRANSFORM_MARS_WMH_PROB_TO_MNI(withTransforms(SEGMENTATION_MARS_WMH.out.probability_map, 'flair'))
    ch_mars_wmh_mni_prob = TRANSFORM_MARS_WMH_PROB_TO_MNI.out.warped_image.map(toSingleMask)

    // BAWIL: 2D model trained on whole-head clinical axial FLAIR slices (unstripped, non-N4,
    // native space) -- fed the full-FOV 1 mm resampled FLAIR, NOT the brain-bbox crop, so
    // bin/bawil_filter.py can present each slice with the head framed as in training. The
    // SynthStrip mask (same grid) only helps locate the head. Output warped to MNI below.
    ch_bawil_in = RESAMPLE_FLAIR.out.image.join(SYNTHSTRIP_FLAIR.out.brain_mask)
    SEGMENTATION_BAWIL(ch_bawil_in)                                    // input: native unstripped

    ch_warp_bawil_mask = SEGMENTATION_BAWIL.out.binary_mask
        .join(ch_session_transforms.map { meta, t1_tx, fl_tx -> [meta, fl_tx] })
        .combine(data.mni_template)
        .map { meta, mask, txs, mni -> [meta, mask, mni, txs] }
    TRANSFORM_BAWIL_MASK_TO_MNI(ch_warp_bawil_mask)
    ch_bawil_mni_mask = TRANSFORM_BAWIL_MASK_TO_MNI.out.warped_image.map(toSingleMask)
    TRANSFORM_BAWIL_PROB_TO_MNI(withTransforms(SEGMENTATION_BAWIL.out.probability_map, 'flair'))
    ch_bawil_mni_prob = TRANSFORM_BAWIL_PROB_TO_MNI.out.warped_image.map(toSingleMask)

    SEGMENTATION_MIMOSA(ch_mni_paired)                                 // input: MNI stripped
    SEGMENTATION_SHIVAI(ch_mni_paired)                                 // input: MNI stripped

    // mindGlide: runs on unstripped, non-N4 native FLAIR, then output mask is warped to MNI space
    SEGMENTATION_MINDGLIDE(CROP_FLAIR_RAW.out.image)                   // input: native unstripped

    ch_warp_mindglide_mask = SEGMENTATION_MINDGLIDE.out.binary_mask
        .join(ch_session_transforms.map { meta, t1_tx, fl_tx -> [meta, fl_tx] })
        .combine(data.mni_template)
        .map { meta, mask, txs, mni -> [meta, mask, mni, txs] }
    TRANSFORM_MINDGLIDE_MASK_TO_MNI(ch_warp_mindglide_mask)
    ch_mindglide_mni_mask = TRANSFORM_MINDGLIDE_MASK_TO_MNI.out.warped_image.map(toSingleMask)
    TRANSFORM_MINDGLIDE_PROB_TO_MNI(withTransforms(SEGMENTATION_MINDGLIDE.out.probability_map, 'flair'))
    ch_mindglide_mni_prob = TRANSFORM_MINDGLIDE_PROB_TO_MNI.out.warped_image.map(toSingleMask)

    // =========================================================================
    // PHASE 3: STAPLE Consensus Fusion (thr90 >= 6mm3 + Watershed)
    // =========================================================================

    // Every algorithm's MNI binary + MNI probability map, tagged with its key:
    // [meta, algo, binary_mni, prob_mni (or [] if the algorithm has none)]
    def tagged = { String algo, ch_bin, ch_prob ->
        ch_bin.join(ch_prob, remainder: true)
              .filter { it[1] != null }
              .map { meta, bin, prob -> [meta, algo, bin, prob ?: []] }
    }
    ch_lesions_mni = tagged('lst_ai',       ch_lst_ai_mni_mask,                    ch_lst_ai_mni_prob)
        .mix(tagged('samseg',       SEGMENTATION_SAMSEG.out.binary_mask,       SEGMENTATION_SAMSEG.out.probability_map))
        .mix(tagged('wmh_synthseg', SEGMENTATION_WMH_SYNTHSEG.out.binary_mask, SEGMENTATION_WMH_SYNTHSEG.out.probability_map))
        .mix(tagged('fast_outlier', SEGMENTATION_FAST_OUTLIER.out.binary_mask, SEGMENTATION_FAST_OUTLIER.out.probability_map))
        .mix(tagged('flames',       SEGMENTATION_FLAMES.out.binary_mask,       SEGMENTATION_FLAMES.out.probability_map))
        .mix(tagged('truenet',      ch_truenet_mni_mask,                       ch_truenet_mni_prob))
        .mix(tagged('hypermapp3r',  SEGMENTATION_HYPERMAPP3R.out.binary_mask,  SEGMENTATION_HYPERMAPP3R.out.probability_map))
        .mix(tagged('segcsvd',      SEGMENTATION_SEGCSVD.out.binary_mask,      SEGMENTATION_SEGCSVD.out.probability_map))
        .mix(tagged('emory_robust', SEGMENTATION_EMORY_ROBUST.out.binary_mask, SEGMENTATION_EMORY_ROBUST.out.probability_map))
        .mix(tagged('mars_wmh',     ch_mars_wmh_mni_mask,                      ch_mars_wmh_mni_prob))
        .mix(tagged('bawil',        ch_bawil_mni_mask,                         ch_bawil_mni_prob))
        .mix(tagged('mimosa',       SEGMENTATION_MIMOSA.out.binary_mask,       SEGMENTATION_MIMOSA.out.probability_map))
        .mix(tagged('shivai',       SEGMENTATION_SHIVAI.out.binary_mask,       SEGMENTATION_SHIVAI.out.probability_map))
        .mix(tagged('mindglide',    ch_mindglide_mni_mask,                     ch_mindglide_mni_prob))

    // Grid check, brain masking (--lesion_brainmask), BIDS naming: the only published lesion files.
    ch_finalize_in = ch_lesions_mni
        .combine(ch_brainmask_mni, by: 0)
        .combine(data.mni_template)
    LESION_FINALIZE(ch_finalize_in)

    // Per session, sorted by file name so STAPLE's input order (and its task hash) is deterministic.
    def groupSorted = { ch ->
        ch.map { meta, algo, f -> [meta, f] }
          .groupTuple(by: 0, size: active_algorithms.size())
          .map { meta, files -> [meta, files.sort { it.name }] }
    }
    ch_all_binary_masks = groupSorted(LESION_FINALIZE.out.mask)
    ch_all_sidecars     = groupSorted(LESION_FINALIZE.out.sidecar)

    ch_staple_input = ch_flair_mni
        .join(ch_all_binary_masks)

    CONSENSUS_STAPLE(ch_staple_input)

    // =========================================================================
    // PHASE 4: Longitudinal Harmonization & Tracking Audit Trail
    // =========================================================================

    ch_harmonize_input = CONSENSUS_STAPLE.out.staple_thr90_binary
        .map { meta, bin_mask -> [meta.subject, meta, bin_mask] }
        .groupTuple(by: 0)

    HARMONIZATION_STAPLE(ch_harmonize_input)

    // =========================================================================
    // PHASE 5: Quality Control & MultiQC Reporting
    // =========================================================================

    def summary_html = "<dl>" +
        "<dt>Input</dt><dd>${params.input ?: ''}</dd>" +
        "<dt>Active Algorithms</dt><dd>" + active_algorithms.join(', ') + "</dd>" +
        "<dt>STAPLE Threshold</dt><dd>${params.staple_threshold}</dd>" +
        "<dt>Min Cluster Size</dt><dd>${params.staple_min_cluster_size}</dd>" +
        "<dt>Pct Change Threshold</dt><dd>${params.pct_change_threshold}</dd>" +
        "<dt>Lesion Brain Mask</dt><dd>${params.lesion_brainmask} (dilation ${params.lesion_brainmask_dilation} vox): ${active_algorithms.intersect(brainmask_targets).join(', ') ?: 'none'}</dd>" +
        "<dt>Volumes</dt><dd>MNI-normalized (template grid, affine normalization of the baseline T1w)</dd>" +
        "</dl>"

    def summary_yaml = """\
id: sf-lesionflow-summary
section_name: Workflow Parameters
plot_type: html
data: '${summary_html}'
"""
    ch_workflow_summary = Channel.value(summary_yaml)
        .collectFile(name: 'workflow_summary_mqc.yaml')

    ch_methods_desc = Channel.fromPath("${projectDir}/assets/methods_description_template.yml")
        .collectFile(name: 'methods_description_mqc.yaml')

    // Real versions of every algorithm, probed once per run inside its own container. The
    // SEGMENTATION_* processes' own versions.yml are placeholders and are NOT collated.
    def probe_keys = active_algorithms.toList().sort() + (('segcsvd' in active_algorithms) ? ['synthseg'] : [])
    PROBE_VERSIONS(Channel.fromList(probe_keys))

    ch_software_versions = PROBE_VERSIONS.out.versions
        .mix(
            RESAMPLE_T1.out.versions, SYNTHSTRIP_T1.out.versions, CROP_T1_MASK.out.versions,
            N4_T1.out.versions, MASK_T1.out.versions,
            REGISTER_FLAIR_TO_T1.out.versions, REGISTER_BASELINE_TO_MNI.out.versions,
            REGISTER_T1_TO_BASELINE.out.versions, TRANSFORM_T1W_TO_MNI.out.versions,
            CONSENSUS_STAPLE.out.versions, HARMONIZATION_STAPLE.out.versions
        )
        .map { f -> f.text.trim() }
        .unique()

    ch_collated_versions = ch_software_versions
        .collectFile(name: 'collated_versions_mqc_versions.yml', newLine: true, sort: true)
    ch_software_versions
        .collectFile(name: 'software_versions.yml', newLine: true, sort: true,
                     storeDir: "${params.output}/pipeline_info")

    // Registration QC channels (one [meta, fixed, warped] triple per stage)
    ch_reg_flair_to_t1 = MASK_T1.out.image
        .join(REGISTER_FLAIR_TO_T1.out.image_warped)
        .join(REGISTER_FLAIR_TO_T1.out.forward_affine)

    ch_followup_base_t1 = ch_grouped_t1.filter { meta, base_img, cur_img, is_base -> !is_base }
        .map { meta, base_img, cur_img, is_base -> [meta, base_img] }
    ch_reg_t1_to_baseline = ch_followup_base_t1
        .join(REGISTER_T1_TO_BASELINE.out.image_warped)
        .join(REGISTER_T1_TO_BASELINE.out.forward_affine)

    ch_reg_t1_to_mni = REGISTER_BASELINE_TO_MNI.out.image_warped
        .combine(data.mni_template)
        .map { meta, warped_t1, mni -> [meta, mni, warped_t1] }
        .join(REGISTER_BASELINE_TO_MNI.out.forward_affine)

    QC_PIPELINE(
        ch_mni_paired,
        ch_all_binary_masks,
        ch_all_sidecars,
        CONSENSUS_STAPLE.out.staple_thr90_binary,
        ch_reg_flair_to_t1,
        ch_reg_t1_to_baseline,
        ch_reg_t1_to_mni,
        HARMONIZATION_STAPLE.out.audit_csv,
        ch_collated_versions,
        ch_workflow_summary,
        ch_methods_desc
    )
}

