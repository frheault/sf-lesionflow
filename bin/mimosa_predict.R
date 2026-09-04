#!/usr/bin/env Rscript
# MIMoSA lesion segmentation inference (Valcarcel et al., 2018, doi:10.1111/jon.12506).
# Executes pretrained mimosa_model_No_PD_T2 (FLAIR and T1) from the mimosa package.

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
              help = "Binarization threshold on smoothed probability map (default: 0.30)"),
  make_option("--smooth_sigma", type = "double", default = 1.25,
              help = "Gaussian smoothing sigma in voxels for probability map (default: 1.25)"),
  make_option("--min_cluster_size", type = "integer", default = 3,
              help = "Minimum connected-component size in voxels (default: 3)")
)
opt <- parse_args(OptionParser(option_list = option_list))

T1 <- readnii(opt$t1)
FLAIR <- readnii(opt$flair)

# Derive brain mask from nonzero voxels across T1 and FLAIR sequences.
brain_mask <- niftiarr(FLAIR, as.numeric((T1 > 0) | (FLAIR > 0)))

# Return empty mask if brain mask contains zero foreground voxels.
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

# Filter connected components smaller than min_cluster_size voxels.
if (opt$min_cluster_size > 1) {
  labeled <- components(as.array(segmentation_mask), shapeKernel(c(3, 3, 3), type = "box"))
  counts <- table(labeled)
  counts <- counts[names(counts) != "0"]
  keep_labels <- as.integer(names(counts)[counts >= opt$min_cluster_size])
  filtered_arr <- array(as.numeric(labeled %in% keep_labels & !is.na(labeled)), dim = dim(labeled))
  segmentation_mask <- niftiarr(segmentation_mask, filtered_arr)
}

writenii(segmentation_mask, filename = opt$output)
