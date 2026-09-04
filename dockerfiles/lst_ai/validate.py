#!/usr/bin/env python3
"""Manual post-build check for ms_chus/lst_ai:latest.

Not run automatically during `docker build` -- run it yourself after
building to confirm all data directories are present and non-empty:

    docker run --rm --entrypoint python3 \\
        -v $(pwd)/dockerfiles/lst_ai/validate.py:/tmp/validate.py \\
        ms_chus/lst_ai:latest /tmp/validate.py
"""
import os
import sys

base = "/opt/LST-AI/LST_AI"
ok = True
for d in ("atlas", "binaries", "model"):
    path = os.path.join(base, d)
    files = os.listdir(path) if os.path.isdir(path) else []
    print(f"  {d}/: {len(files)} file(s), {files[:3]}")
    if not files:
        print(f"ERROR: {path} is empty or missing!", file=sys.stderr)
        ok = False
if not ok:
    sys.exit(1)
print("OK: all LST-AI data directories verified.")
