#!/usr/bin/env python3
"""Manual post-build check for ms_chus/truenet:latest.

Not run automatically during `docker build` -- run it yourself after
building to confirm the model files are actually present:

    docker run --rm --entrypoint python3 \\
        -v $(pwd)/dockerfiles/truenet/validate.py:/tmp/validate.py \\
        ms_chus/truenet:latest /tmp/validate.py
"""
import os
import sys

base = os.environ["TRUENET_PRETRAINED_MODEL_PATH"]
files = []
for root, dirs, fs in os.walk(base):
    files.extend(fs)
print(f"  {len(files)} model file(s) found under {base}")
if not files:
    print("ERROR: No model files found!", file=sys.stderr)
    sys.exit(1)
print("OK: TrueNet models verified.")
