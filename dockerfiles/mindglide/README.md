# mindGlide (`SEGMENTATION_MINDGLIDE`)

## What this runs

Goebl et al. *Enabling new insights from old scans by repurposing clinical MRI archives for multiple sclerosis research*. Nature Communications 16(1):3149, 2025. https://doi.org/10.1038/s41467-025-58274-8

- Tool: `mindglide` v1.3.0
- Repo: https://github.com/MS-PINPOINT/mindGlide
- Model weights: Hugging Face repository `MS-PINPOINT/mindglide` (`_20240404_conjurer_trained_dice_7733.pt`, commit `a1969821c0a4a37ae54f649a9a0c6fd1b8a48e26`, ~123 MB)
- Output label 18: Lesion (conformed and binarized via `bin/conform_synthseg.py --label_id 18`).

## Container Info

```
frheault/sf-lesionflow-mindglide:1.0.0
```

`python:3.11-slim` + `torch==2.3.1+cu118` + `monai==1.4.0` + `mindglide==1.3.0`. Model weights are baked into `/opt/mindglide/models/` at build time.

## Build

```bash
docker build -t frheault/sf-lesionflow-mindglide:1.0.0 dockerfiles/mindglide/
```

After building, verify the model actually loads and predicts:
```bash
docker run --rm -v $(pwd)/dockerfiles/mindglide/validate.py:/tmp/validate.py \
    frheault/sf-lesionflow-mindglide:1.0.0 python3 /tmp/validate.py
```
