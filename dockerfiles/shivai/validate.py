#!/usr/bin/env python3
"""Manual post-build check for ms_chus/shivai:latest.

Not run automatically during `docker build` -- run it yourself after
building to confirm all 5 folds load and predict with the expected shape:

    docker run --rm \\
        -v $(pwd)/dockerfiles/shivai/validate.py:/tmp/validate.py \\
        ms_chus/shivai:latest python3 /tmp/validate.py

Run this as the same non-root user Nextflow uses (`-u $(id -u):$(id -g)`),
not as root -- a permission issue on a stray file/directory baked into the
image can silently pass under root but fail at runtime.
"""
from pathlib import Path
import numpy as np
import tensorflow as tf


def _is_fold_dir(p):
    try:
        return p.is_dir() and (p / "saved_model.pb").exists()
    except OSError:
        return False


fold_dirs = sorted(p for p in Path("/opt/shivai/T1.FLAIR-WMH").iterdir() if _is_fold_dir(p))
assert len(fold_dirs) == 5, f"expected 5 folds, found {len(fold_dirs)}: {fold_dirs}"

x = np.zeros((1, 160, 214, 176, 2), dtype=np.float32)
for fold_dir in fold_dirs:
    model = tf.saved_model.load(str(fold_dir))
    y = model.serve(tf.constant(x))
    assert tuple(y.shape) == (1, 160, 214, 176, 1), f"unexpected output shape: {y.shape}"
print(f"OK: all {len(fold_dirs)} SHIVA-WMH folds load and predict with the expected (1, 160, 214, 176, 1) output shape.")
