#!/usr/bin/env python3
"""Manual post-build check for ms_chus/flames:latest.

Not run automatically during `docker build` -- run it yourself after
building to confirm all 5 weight folds are present:

    docker run --rm --entrypoint python3 \\
        -v $(pwd)/dockerfiles/flames/validate.py:/tmp/validate.py \\
        ms_chus/flames:latest /tmp/validate.py
"""
import os
import sys

base = os.path.join(
    os.environ["nnUNet_results"],
    "Dataset004_WML",
    "nnUNetTrainer_8000epochs__nnUNetPlans__3d_fullres",
)
for fold in range(5):
    p = os.path.join(base, f"fold_{fold}")
    if not os.path.isdir(p):
        print(f"ERROR: missing {p}", file=sys.stderr)
        sys.exit(1)
    print(f"  fold_{fold}/: {len(os.listdir(p))} files")
print("OK: all 5 FLAMeS weight folds verified.")
