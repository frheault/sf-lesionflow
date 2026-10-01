"""Geometry round-trip tests for bin/bawil_filter.py (no TensorFlow / OpenCV needed)."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))
import bawil_filter as bf  # noqa: E402


@pytest.mark.parametrize("orientation", bf.ORIENTATIONS)
def test_orientation_round_trip(orientation):
    sl = np.random.RandomState(0).rand(7, 11)
    assert np.array_equal(bf.orient_inverse(bf.orient_forward(sl, orientation), orientation), sl)


def test_rot90_puts_anterior_at_top():
    # RAS slice: rows = x (left->right), cols = y (posterior->anterior). Mark the most anterior column.
    sl = np.zeros((5, 8))
    sl[:, -1] = 1
    frame = bf.orient_forward(sl, "rot90")
    assert frame[0].all() and not frame[1:].any()  # anterior row is the top row


def test_window_round_trip_and_padding():
    sl = np.arange(20 * 30, dtype=np.float32).reshape(20, 30)
    x0, y0, side = -5, 3, 32
    win = bf.extract_window(sl, x0, y0, side, fill_value=-1)
    assert win.shape == (side, side)
    assert (win[:5] == -1).all()  # rows before the image are padding
    back = bf.paste_window(win, sl.shape, x0, y0)
    assert np.array_equal(back[:, 3:30], sl[:, 3:30])


def test_square_window_is_head_centred_and_isotropic():
    m = np.zeros((200, 250), bool)
    m[40:160, 30:230] = True  # head extent 120 (x) x 200 (y)
    x0, y0, side = bf.square_window(m, 0.92)
    assert side == int(np.ceil(200 / 0.92))
    assert abs((x0 + side / 2) - 100) <= 1 and abs((y0 + side / 2) - 130) <= 1


def test_slab_average():
    vol = np.stack([np.full((2, 2), z, float) for z in range(10)], axis=2)
    assert bf.slab_average(vol, 5, 1)[0, 0] == 5
    assert bf.slab_average(vol, 5, 5)[0, 0] == pytest.approx(5)
    assert bf.slab_average(vol, 0, 5)[0, 0] == pytest.approx(1)  # clipped at the volume edge
