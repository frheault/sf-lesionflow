#!/usr/bin/env python3
"""Manual post-build check for frheault/sf-lesionflow-mindglide:1.0.0.

Not run automatically during `docker build` -- run it yourself after
building to confirm the model actually loads and predicts:

    docker run --rm \
        -v $(pwd)/dockerfiles/mindglide/validate.py:/tmp/validate.py \
        frheault/sf-lesionflow-mindglide:1.0.0 python3 /tmp/validate.py
"""
import os
from pathlib import Path

import torch
from mindglide.infer import resolve_model_path
from mindglide.network import get_network

# 1. Verify model weights location
model_path = resolve_model_path()
assert Path(model_path).is_file(), f"Model path does not exist: {model_path}"
print(f"OK: Model path resolved to {model_path} ({os.path.getsize(model_path)} bytes)")

# 2. Verify model network initialization and checkpoint load
model = get_network(device="cpu", checkpoint_path=str(model_path))
model.eval()
print("OK: mindGlide network initialized and weights loaded on CPU successfully.")

# 3. Quick forward pass check on dummy patch (1, 1, 128, 128, 64)
with torch.no_grad():
    x = torch.zeros(1, 1, 128, 128, 64, dtype=torch.float32)
    y = model(x)
    assert y.shape[1] == 20, f"Expected 20 output classes, got {y.shape[1]}"
print("OK: Forward pass on dummy tensor produced expected 20 output channels.")
