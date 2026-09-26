"""Array-only temporal matching; no fitting, audio access, or probability output.

Reference for subsequence initialization and the slope-constrained step set:
https://www.audiolabs-erlangen.de/resources/MIR/FMP/C7/C7S2_SubsequenceDTW.html

This follows the notebook's UNWEIGHTED (1,1)/(1,2)/(2,1) recurrence exactly:

    D[n,m] = C[n,m] + min(D[n-1,m-1], D[n-1,m-2], D[n-2,m-1])

The first row starts a subsequence at any history frame: D[0,m] = C[0,m].
All other out-of-bounds predecessors are forbidden. As in that FMP example,
skipped query rows and skipped history columns are NOT charged local costs.
Consequently paths with different numbers of anchors can have different
total cost weights. This known property is retained for a literal established
baseline, not represented as complete evidence coverage or a corrected metric.
Final accumulated cost is divided by N, NOT by the number of path anchors.
Costs are dissimilarities in [0,2], not probabilities or calibrated confidence.
Zero-norm frames have similarity zero even when both frames are zero.

``path`` lists the slope-constrained anchor pairs; summing their local costs
reproduces the numerator. Every input row is unit-L2 normalized before the
cosine comparison, with zero rows left zero.
History endpoints are inclusive. Timestamps and real-duration acceptance
(including the caller's [0.65,1.5] query/history duration limit) belong to the
caller. No frame-count ratio is silently substituted for duration here.
Removal-separated history segments must be matched in separate calls.
"""

from __future__ import annotations

import numpy as np


VARIANT = "fmp_unweighted_sdtw_11_12_21"
_STEPS = ((1, 1), (1, 2), (2, 1))


def _features(values: np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] == 0:
        raise ValueError(f"{name} must be a two-dimensional frames-by-features array")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _unit_rows(array: np.ndarray) -> np.ndarray:
    # Scaling first also permits finite inputs whose unscaled squares overflow.
    scale = np.max(np.abs(array), axis=1, keepdims=True)
    scaled = np.divide(array, scale, out=np.zeros_like(array), where=scale > 0)
    norms = np.linalg.norm(scaled, axis=1, keepdims=True)
    return np.divide(scaled, norms, out=np.zeros_like(scaled), where=norms > 0)


def _no_match() -> dict:
    return {
        "cost": float("inf"),
        "start_index": None,
        "end_index": None,
        "path": [],
        "accumulated_cost": float("inf"),
        "variant": VARIANT,
    }


def subsequence_dtw(query: np.ndarray, history: np.ndarray) -> dict:
    """Align query endpoints to one history subsequence with FMP step skips.

    Inputs are N-by-D and M-by-D. Empty sequences and unreachable alignments
    return infinite distance, null bounds, and empty paths. Malformed inputs
    raise ValueError. Equal-cost choices prefer (1,1), then (1,2), then (2,1);
    equal-cost endpoints prefer the earliest history endpoint.

    The recurrence is vectorized across each history row, with no same-row
    dependency: three rolling accumulated-cost rows and an N-by-M int8
    backpointer matrix supplement the N-by-M local-cost matrix. Runtime is
    O(N*M*D + N*M); retained array space is O(N*M + (N+M)*D).

    This returns the unconstrained best subsequence. The caller must validate
    duration and timestamps before accepting it; rejecting it is not evidence
    that no duration-valid alternative alignment exists.
    """
    q = _features(query, "query")
    h = _features(history, "history")
    if q.shape[1] != h.shape[1]:
        raise ValueError("query and history must have the same feature dimension")
    n_frames, m_frames = len(q), len(h)
    if n_frames == 0 or m_frames == 0:
        return _no_match()

    costs = np.clip(1.0 - _unit_rows(q) @ _unit_rows(h).T, 0.0, 2.0)
    predecessors = np.full((n_frames, m_frames), -1, dtype=np.int8)
    two_back = np.full(m_frames, np.inf)
    previous = costs[0].copy()
    for n in range(1, n_frames):
        options = np.full((3, m_frames), np.inf)
        options[0, 1:] = previous[:-1] + costs[n, 1:]
        options[1, 2:] = previous[:-2] + costs[n, 2:]
        if n >= 2:
            options[2, 1:] = two_back[:-1] + costs[n, 1:]
        winner = np.argmin(options, axis=0)
        current = np.take_along_axis(options, winner[None, :], axis=0)[0]
        predecessors[n] = np.where(np.isfinite(current), winner, -1)
        two_back, previous = previous, current

    end = int(np.argmin(previous))
    numerator = float(previous[end])
    if not np.isfinite(numerator):
        return _no_match()

    n, m = n_frames - 1, end
    reverse_path = [(n, m)]
    while n > 0:
        step_index = int(predecessors[n, m])
        if step_index < 0:
            raise RuntimeError("finite DTW endpoint has an unreachable predecessor")
        dn, dm = _STEPS[step_index]
        n, m = n - dn, m - dm
        reverse_path.append((n, m))
    path = list(reversed(reverse_path))
    return {
        "cost": numerator / n_frames,
        "start_index": int(path[0][1]),
        "end_index": end,
        "path": path,
        "accumulated_cost": numerator,
        "variant": VARIANT,
    }


def align(query: np.ndarray, history: np.ndarray, roll_chroma: bool = False) -> dict:
    """Return the lowest-distance alignment; optionally search -5..5 semitones.

    Chroma must have exactly 12 ascending pitch-class bins. Positive ``shift``
    rolls the HISTORY toward higher bins to match the query, so a query three
    semitones above stored history is reported as +3 (modulo pitch class).
    This search does not cover the tritone or infer octave displacement.
    Non-chroma calls only try shift zero; MERT coordinates are never rolled.
    Equal distances prefer zero, then smaller absolute shift, then negative
    shift. ``cost`` remains a distance, not a posterior over shifts or memories.
    """
    q = _features(query, "query")
    h = _features(history, "history")
    if q.shape[1] != h.shape[1]:
        raise ValueError("query and history must have the same feature dimension")
    if roll_chroma and q.shape[1] != 12:
        raise ValueError("roll_chroma requires exactly 12 pitch-class features")
    shifts = sorted(range(-5, 6), key=lambda s: (abs(s), s)) if roll_chroma else (0,)
    best = None
    for shift in shifts:
        result = subsequence_dtw(q, np.roll(h, shift, axis=1) if shift else h)
        result["shift"] = int(shift)
        if best is None or result["cost"] < best["cost"]:
            best = result
    return best


if __name__ == "__main__":
    # Tiny deterministic NON-AUDIO checks only; no experiment/session is run.
    import json
    import time

    began = time.perf_counter()
    basis = np.eye(12)
    query = basis[[0, 2, 4, 7]]
    history = basis[[10, 11, 0, 2, 4, 7, 9]]
    exact = subsequence_dtw(query, history)
    assert exact["cost"] == 0 and (exact["start_index"], exact["end_index"]) == (2, 5)
    shifted = align(np.roll(query, 3, axis=1), history, roll_chroma=True)
    assert shifted["cost"] == 0 and shifted["shift"] == 3
    skipped = subsequence_dtw(basis[[0, 1, 2]], basis[[0, 2]])
    assert skipped["cost"] == 0  # Literal FMP baseline skips query row 1.
    assert skipped["path"] == [(0, 0), (2, 1)]
    print(json.dumps({"passed": True, "probe_count": 3,
                      "dtw_calls": 13, "audio_or_model_runs": 0,
                      "runtime_seconds": time.perf_counter() - began,
                      "variant": VARIANT}))
