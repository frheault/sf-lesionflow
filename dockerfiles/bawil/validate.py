#!/usr/bin/env python3
"""Manual post-build check for ms_chus/bawil:latest.

Not run automatically during `docker build` -- run it yourself after
building (or after pulling) to confirm the model actually loads and predicts:

    docker run --rm \\
        -v $(pwd)/dockerfiles/bawil/validate.py:/tmp/validate.py \\
        ms_chus/bawil:latest python3 /tmp/validate.py
"""
import numpy as np
from tensorflow import keras

model = keras.models.load_model("/opt/bawil/scenario2_multiclass_model.h5", compile=False)
x = np.random.rand(1, 256, 256, 1).astype(np.float32)
y = model.predict(x, verbose=0)
assert y.shape == (1, 256, 256, 3), f"unexpected output shape: {y.shape}"
print("OK: BAWIL model loads and predicts with the expected (256, 256, 3) output shape.")
