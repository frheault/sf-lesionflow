# TrueNet (02g_truenet.sh) — Triplanar Ensemble U-Net

## Container Info

```
ms_chus/truenet:latest
```

Custom Docker image built on top of `brainlife/fsl:6.0.4-patched`. It provides **both** `truenet` and `fast` (FSL).

## Model Source & Weight Bundling

The model weights were downloaded from Google Drive:
- **Source Drive Folder**: https://drive.google.com/drive/folders/1iqO-hd27NSHHfKun125Rt-2fh1l9EiuT
- **Models Bundled**: All 18 pre-trained network weights (`MWSC_FLAIR_T1`, `MWSC_FLAIR`, `MWSC_T1`, `UKBB_FLAIR_T1`, etc.)
- **Build Instruction**:
  ```dockerfile
  COPY models /opt/truenet_models
  RUN cp -r /opt/truenet_models/MWSC_FLAIR_T1/* /opt/truenet_models/
  ENV TRUENET_PRETRAINED_MODEL_PATH=/opt/truenet_models
  ```
  Copying local pre-downloaded weights into the build context avoids Google Drive rate-limits during automated builds.

## Usage in Pipeline

1. **Create masterfile text file**:
   ```bash
   cat <<'EOF' > /tmp/truenet_in/masterfile.txt
   FLAIR T1
   /input/sub-021_ses-1_FLAIR.nii.gz /input/sub-021_ses-1_T1.nii.gz
   EOF
   ```

2. **Run TrueNet inference**:
   ```bash
   docker run --rm \
     --memory="8g" \
     --cpuset-cpus="0-3" \
     -v /tmp/truenet_in:/input \
     -v /tmp/truenet_out:/output \
     ms_chus/truenet:latest \
     apply -i /input/masterfile.txt -m mwsc -o /output -cpu True
   ```

3. **Binarize output at 0.5 threshold using FSL fslmaths**:
   ```bash
   docker run --rm -v /tmp/truenet_out:/output ms_chus/truenet:latest \
     fslmaths /output/Predicted_probmap_truenet_sub-021_ses-1.nii.gz -thr 0.5 -bin /output/sub-021_ses-1_truenet_binary.nii.gz
   ```

## Key Flags

| Flag | Purpose |
|------|---------|
| `apply` | Inference subcommand |
| `-i /input/masterfile.txt` | Masterfile list with headers `FLAIR T1` |
| `-m mwsc` | Pre-trained Multi-Site White Matter Hyperintensity model |
| `-cpu True` | Force CPU execution |
