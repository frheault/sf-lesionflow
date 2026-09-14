include { QC_ENSEMBLE_METRICS                              } from '../../modules/local/qc/ensemble_metrics'
include { QC_REGISTRATION as QC_REGISTRATION_FLAIR_T1     } from '../../modules/local/qc/registration'
include { QC_REGISTRATION as QC_REGISTRATION_T1_BASELINE  } from '../../modules/local/qc/registration'
include { QC_REGISTRATION as QC_REGISTRATION_BASELINE_MNI } from '../../modules/local/qc/registration'
include { QC_LESION_SCREENSHOT                             } from '../../modules/local/qc/screenshot'
include { QC_LONGITUDINAL                                  } from '../../modules/local/qc/longitudinal'
include { QC_MULTIQC as MULTIQC_SUBJECT                    } from '../../modules/local/qc_multiqc'
include { QC_MULTIQC as MULTIQC_GLOBAL                     } from '../../modules/local/qc_multiqc'

workflow QC_PIPELINE {
    take:
    ch_t1_flair_paired      // channel: [meta, t1, flair]
    ch_all_binary_masks     // channel: [meta, [masks_13_algos]]
    ch_staple_binary        // channel: [meta, thr90_binary]
    ch_reg_flair_to_t1      // channel: [meta, fixed_t1, warped_flair]
    ch_reg_t1_to_baseline   // channel: [meta, fixed_baseline_t1, warped_t1]
    ch_reg_t1_to_mni        // channel: [meta, fixed_mni, warped_t1]
    ch_harmonize_audit      // channel: [subject, audit_csv]
    ch_collated_versions    // path: versions.yml
    ch_workflow_summary     // path: workflow_summary_mqc.yaml
    ch_methods_desc         // path: methods_description_mqc.yaml

    main:
    ch_versions = Channel.empty()

    // 1. Ensemble Metrics (Volumes, Pairwise Dice, Consensus Summary)
    ch_ens_input = ch_staple_binary
        .join(ch_all_binary_masks)
    QC_ENSEMBLE_METRICS(ch_ens_input)
    ch_versions = ch_versions.mix(QC_ENSEMBLE_METRICS.out.versions)

    // 2. Registration Diagnostic Montages & Metrics (3 stages)
    QC_REGISTRATION_FLAIR_T1(ch_reg_flair_to_t1)
    QC_REGISTRATION_T1_BASELINE(ch_reg_t1_to_baseline)
    QC_REGISTRATION_BASELINE_MNI(ch_reg_t1_to_mni)

    ch_reg_files_all = QC_REGISTRATION_FLAIR_T1.out.files
        .mix(QC_REGISTRATION_T1_BASELINE.out.files)
        .mix(QC_REGISTRATION_BASELINE_MNI.out.files)

    ch_reg_metrics_tsv_all = QC_REGISTRATION_FLAIR_T1.out.metrics_tsv
        .mix(QC_REGISTRATION_T1_BASELINE.out.metrics_tsv)
        .mix(QC_REGISTRATION_BASELINE_MNI.out.metrics_tsv)

    ch_versions = ch_versions.mix(
        QC_REGISTRATION_FLAIR_T1.out.versions,
        QC_REGISTRATION_T1_BASELINE.out.versions,
        QC_REGISTRATION_BASELINE_MNI.out.versions
    )

    // 3. Lesion Segmentation Visual Montage (Triplanar PNG)
    ch_screen_input = ch_t1_flair_paired.map { meta, t1, flair -> [meta, flair] }
        .join(ch_staple_binary)
    QC_LESION_SCREENSHOT(ch_screen_input)
    ch_versions = ch_versions.mix(QC_LESION_SCREENSHOT.out.versions)

    // 4. Longitudinal Trajectory Extraction
    QC_LONGITUDINAL(ch_harmonize_audit)
    ch_versions = ch_versions.mix(QC_LONGITUDINAL.out.versions)

    // 5. Common MultiQC Files
    ch_common_files = ch_collated_versions
        .mix(ch_workflow_summary)
        .mix(ch_methods_desc)

    // 6. Subject-Specific Reports (Single Subject Mode)
    def _session_num = { str ->
        def m = (str =~ /ses-(\d+)/)
        m ? m[0][1] as Integer : 0
    }

    ch_last_session_per_subject = ch_all_binary_masks
        .map { meta, masks -> [meta.subject, meta] }
        .groupTuple()
        .map { subject, metas ->
            def sorted = metas.unique().sort { a, b ->
                def na = _session_num(a.session ?: '')
                def nb = _session_num(b.session ?: '')
                na != nb ? na <=> nb : (a.session ?: '') <=> (b.session ?: '')
            }
            [subject, sorted[-1]]
        }

    ch_longitudinal_for_subject_report = QC_LONGITUDINAL.out.files
        .join(ch_last_session_per_subject)
        .map { subject, files, meta -> [meta, files] }

    ch_subject_qc_files = QC_ENSEMBLE_METRICS.out.files
        .mix(ch_reg_files_all)
        .mix(QC_LESION_SCREENSHOT.out.png)
        .mix(ch_longitudinal_for_subject_report)
        .groupTuple(by: 0)
        .map { meta, files -> [meta, files.flatten().unique()] }

    ch_cfg_subject = file("${projectDir}/assets/multiqc_config_subject.yml", checkIfExists: true)
    ch_cfg_global  = file("${projectDir}/assets/multiqc_config_global.yml", checkIfExists: true)
    ch_logo        = file("${projectDir}/assets/sf-lesionflow-logo.png", checkIfExists: true)

    MULTIQC_SUBJECT(
        ch_subject_qc_files,
        ch_common_files.collect(),
        ch_cfg_subject,
        [],
        ch_logo
    )
    ch_versions = ch_versions.mix(MULTIQC_SUBJECT.out.versions)

    // 7. Global Cohort Report (Population Wide)
    ch_global_qc_files = QC_ENSEMBLE_METRICS.out.summary_tsv.map { meta, tsv -> tsv }
        .mix(QC_ENSEMBLE_METRICS.out.volumes_tsv.map { meta, tsv -> tsv })
        .mix(QC_LONGITUDINAL.out.summary_tsv.map { subj, tsv -> tsv })
        .mix(QC_LONGITUDINAL.out.trajectories_tsv.map { subj, tsv -> tsv })
        .mix(ch_reg_metrics_tsv_all.map { meta, tsv -> tsv })

    MULTIQC_GLOBAL(
        [ [id: 'global'], [] ],
        ch_global_qc_files.mix(ch_common_files).collect(),
        ch_cfg_global,
        [],
        ch_logo
    )
    ch_versions = ch_versions.mix(MULTIQC_GLOBAL.out.versions)

    emit:
    subject_reports = MULTIQC_SUBJECT.out.report
    global_report   = MULTIQC_GLOBAL.out.report
    versions        = ch_versions
}
