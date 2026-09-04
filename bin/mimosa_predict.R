#!/usr/bin/env Rscript
# Real MIMoSA inference (Valcarcel AM, et al. 2018, doi:10.1111/jon.12506)
# using the pretrained `mimosa_model_No_PD_T2` model (FLAIR + T1, no T2/PD)
# shipped inside the `mimosa` R package itself -- no training data required.

suppressMessages({
  library(optparse)
  library(neurobase)
  library(mimosa)
  library(fslr)
  library(mmand)
})

option_list <- list(
  make_option("--t1", type = "character"),
  make_option("--flair", type = "character"),
  make_option("--output", type = "character"),
  make_option("--prob_threshold", type = "double", default = 0.30,
              help = "Binarization threshold on the smoothed probability map. The package vignette only documents an optimal-threshold search range of [0.25, 0.35] for the full (FLAIR+T1+T2+PD) model trained from scratch; there is no published default specifically for the pretrained FLAIR+T1-only model used here, so 0.30 (midpoint of that range) is used as a reasonable default -- tune via this flag if needed."),
  make_option("--smooth_sigma", type = "double", default = 1.25,
              help = "Gaussian smoothing sigma (voxels) applied to the probability map before thresholding, matching the package vignette."),
  make_option("--min_cluster_size", type = "integer", default = 3,
              help = "Minimum connected-component size (voxels) to keep in the final binary mask.")
)
opt <- parse_args(OptionParser(option_list = option_list))

T1 <- readnii(opt$t1)
FLAIR <- readnii(opt$flair)

# Inputs arrive already skull-stripped/masked (background == 0). Derive the
# brain mask the same way the mimosa package's own vignette does: the union
# of nonzero voxels across the available sequences.
brain_mask <- niftiarr(FLAIR, as.numeric((T1 > 0) | (FLAIR > 0)))

if (sum(brain_mask) == 0) {
  writenii(niftiarr(FLAIR, 0), filename = opt$output)
  quit(save = "no", status = 0)
}

data("mimosa_model_No_PD_T2", package = "mimosa", envir = environment())

md <- mimosa_data(
  brain_mask = brain_mask,
  FLAIR = FLAIR,
  T1 = T1,
  T2 = NULL,
  PD = NULL,
  tissue = FALSE,
  gold_standard = NULL,
  normalize = "Z",
  cand_mask = NULL,
  cores = 1,
  verbose = TRUE
)

predictions <- predict(mimosa_model_No_PD_T2, newdata = md$mimosa_dataframe, type = "response")

probability_map <- niftiarr(brain_mask, 0)
probability_map[md$top_voxels == 1] <- predictions
probability_map <- fslsmooth(probability_map, sigma = opt$smooth_sigma, mask = brain_mask,
                              retimg = TRUE, smooth_mask = TRUE)

segmentation_mask <- probability_map > opt$prob_threshold

if (opt$min_cluster_size > 1) {
  labeled <- components(as.array(segmentation_mask), shapeKernel(c(3, 3, 3), type = "box"))
  counts <- table(labeled)
  counts <- counts[names(counts) != "0"]
  keep_labels <- as.integer(names(counts)[counts >= opt$min_cluster_size])
  filtered_arr <- array(as.numeric(labeled %in% keep_labels & !is.na(labeled)), dim = dim(labeled))
  segmentation_mask <- niftiarr(segmentation_mask, filtered_arr)
}

writenii(segmentation_mask, filename = opt$output)
