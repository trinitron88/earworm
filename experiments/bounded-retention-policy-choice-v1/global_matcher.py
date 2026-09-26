"""Frozen S1-inspired global transform reference and richer exact-event diagnostic.

Only arrived, retained observation arrays are accepted. No file, network, score
loader, generator, true source interval, or persistent cache is used here.
See GLOBAL_METHOD.md for the observation model and its limitations.
"""
from __future__ import annotations

import numpy as np

SCALE_RANGE = (0.65, 1.5)
SHIFTS = tuple(range(-5, 6))
QUERY_SECONDS = 2.0
GAP_LIMIT = 0.10001
SILENCE = 128
ROUND_EPS = 64.0 * np.finfo(np.float64).eps


def _tol(*values):
    """Arithmetic roundoff allowance, never a musical timing tolerance."""
    return ROUND_EPS * (1.0 + sum(abs(float(x)) for x in values))


def _interval(lo, hi, lower_open=False):
    return (float(lo), float(hi), bool(lower_open))


def _segments(times):
    if not len(times):
        return []
    cuts = np.r_[0, np.flatnonzero(np.diff(times) > GAP_LIMIT) + 1, len(times)]
    return [(int(a), int(b)) for a, b in zip(cuts[:-1], cuts[1:])]


def _row_runs(t, labels, ids):
    """Lossless run index: keep row IDs; only identical adjacent labels merge."""
    cuts = np.r_[0, np.flatnonzero(np.diff(labels) != 0) + 1, len(labels)]
    runs = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        a, b = int(a), int(b)
        left = _interval(t[0], t[0]) if a == 0 else _interval(t[a-1], t[a], True)
        right = (_interval(t[-1], t[-1]) if b == len(t)
                 else _interval(t[b-1], t[b], True))
        runs.append({"pitch": int(labels[a]), "first": float(t[a]),
                     "last": float(t[b-1]), "left": left, "right": right,
                     "row_ids": [int(x) for x in ids[a:b]],
                     "left_censored": a == 0, "right_censored": b == len(t)})
    return runs


def _event_at(events, time):
    for i, (on, off, pitch) in enumerate(events):
        if on <= time < off:
            return int(pitch), int(i)
    return SILENCE, None


def _exact_runs(events, lo, hi):
    """Piecewise exact support, retaining true repeated-note onsets.

    Outer edges are censored. The right endpoint's point observation is retained
    if an event changes exactly there, via a zero-duration terminal run.
    """
    raw = []
    cursor = float(lo)
    for i, (on, off, pitch) in enumerate(events):
        if off <= lo:
            continue
        if on > hi:
            break
        a, b = max(float(on), lo), min(float(off), hi)
        if a > cursor:
            raw.append([cursor, a, SILENCE, None])
            cursor = a
        if b > a:
            raw.append([a, b, int(pitch), i])
            cursor = b
    if cursor < hi:
        raw.append([cursor, hi, SILENCE, None])
    terminal_pitch, terminal_token = _event_at(events, hi)
    if not raw or raw[-1][2:] != [terminal_pitch, terminal_token]:
        raw.append([hi, hi, terminal_pitch, terminal_token])
    runs = []
    for i, (a, b, pitch, token) in enumerate(raw):
        runs.append({"pitch": pitch, "first": a, "last": b,
                     "left": _interval(a, a), "right": _interval(b, b),
                     "event_index": token, "row_ids": [],
                     "left_censored": i == 0, "right_censored": i == len(raw)-1})
    return runs


def _dedup_vertices(poly):
    out = []
    for p in poly:
        p = np.asarray(p, dtype=np.float64)
        if not out or np.max(np.abs(p-out[-1])) > _tol(*p, *out[-1]):
            out.append(p)
    if len(out) > 1 and np.max(np.abs(out[0]-out[-1])) <= _tol(*out[0], *out[-1]):
        out.pop()
    return out


def _clip(poly, aa, bb, limit):
    """Intersect a convex polygon with aa*scale+bb*offset <= limit.

    Retains line/point intersections, needed for exact correspondence. Open
    constraints are checked after choosing a relative-interior representative.
    """
    if not poly:
        return []
    normal = np.array([aa, bb], dtype=np.float64)
    output = []
    for p, q in zip(poly, poly[1:] + poly[:1]):
        fp, fq = float(normal @ p - limit), float(normal @ q - limit)
        ep, eq = _tol(*(normal*p), limit), _tol(*(normal*q), limit)
        pin, qin = fp <= ep, fq <= eq
        if pin:
            output.append(p)
        if pin != qin:
            denom = fp - fq
            if denom != 0.0:
                fraction = min(1.0, max(0.0, fp / denom))
                output.append(p + fraction * (q-p))
    return _dedup_vertices(output)


def _satisfies(point, constraints):
    for aa, bb, limit, strict, _ in constraints:
        lhs = aa*point[0] + bb*point[1]
        allowance = _tol(aa*point[0], bb*point[1], limit)
        if strict:
            if not lhs < limit-allowance:
                return False
        elif lhs > limit+allowance:
            return False
    return True


def _pitch_ok(query_pitch, history_pitch, shift):
    if query_pitch == SILENCE or history_pitch == SILENCE:
        return query_pitch == history_pitch == SILENCE
    return query_pitch == history_pitch + shift


def _matched_boundary(qbracket, hbracket, scale, offset, qorigin, horigin):
    qlo, qhi, qopen = qbracket
    hlo, hhi, hopen = hbracket
    alo = scale*(hlo-horigin) + offset + qorigin
    ahi = scale*(hhi-horigin) + offset + qorigin
    low, high = max(qlo, alo), min(qhi, ahi)
    eps = _tol(low, high)
    if low > high+eps:
        raise ArithmeticError("selected transform lacks a boundary witness")
    # A tiny inverted closed intersection is arithmetic equality only.
    value = (low+high)/2.0
    if (qopen and value <= qlo) or (hopen and value <= alo):
        raise ArithmeticError("selected transform hits an excluded sample boundary")
    return {"query_boundary": float(value),
            "history_boundary": float((value-qorigin-offset)/scale+horigin),
            "query_bracket": list(qbracket), "history_bracket": list(hbracket)}


def _solve_candidate(qruns, hruns, qtimes, qlabels, htimes, hlabels, hids,
                     qids, history_support, shift, exact):
    """One consecutive run correspondence; all its inequalities are retained."""
    qorigin, horigin = float(qtimes[0]), float(htimes[0])
    qend = float(qtimes[-1]-qorigin)
    hstart, hend = (float(x-horigin) for x in history_support)
    amin, amax = SCALE_RANGE
    # Finite enclosure derived from retained support, not a search grid.
    bmin = min(-amin*hend, -amax*hend)
    bmax = max(qend-amin*hstart, qend-amax*hstart)
    polygon = [np.array(p, dtype=np.float64) for p in
               [(amin,bmin), (amax,bmin), (amax,bmax), (amin,bmax)]]
    constraints = []
    def add(aa, bb, limit, strict, name):
        constraints.append((float(aa), float(bb), float(limit), bool(strict), name))
    # Mapped query support must remain inside one retained component.
    add(hstart, 1, 0, False, "retained-support-start")
    add(-hend, -1, -qend, False, "retained-support-end")
    # The first and final run may be clipped, but cannot contradict a sample.
    firstlo, _, firstopen = hruns[0]["left"]
    _, lasthi, _ = hruns[-1]["right"]
    add(firstlo-horigin, 1, 0, firstopen, "first-run-coverage")
    add(-(lasthi-horigin), -1, -qend,
        not hruns[-1]["right_censored"], "last-run-coverage")
    for i, (qrun, hrun) in enumerate(zip(qruns[:-1], hruns[:-1])):
        qlo, qhi, qopen = qrun["right"]
        hlo, hhi, hopen = hrun["right"]
        add(hlo-horigin, 1, qhi-qorigin, hopen, f"transition-{i}-upper")
        add(-(hhi-horigin), -1, -(qlo-qorigin), qopen, f"transition-{i}-lower")
    for aa, bb, limit, _, _ in constraints:
        polygon = _clip(polygon, aa, bb, limit)
        if not polygon:
            return None
    representative = np.mean(np.stack(polygon), axis=0)
    if not _satisfies(representative, constraints):
        return None
    scale, offset = map(float, representative)
    boundaries = [_matched_boundary(qr["right"], hr["right"], scale, offset,
                                    qorigin, horigin)
                  for qr, hr in zip(qruns[:-1], hruns[:-1])]
    bq = np.array([b["query_boundary"] for b in boundaries], dtype=np.float64)
    # Independently visit every query row, and every retained history row within
    # the mapped query support, after establishing the continuous run witness.
    qrun_index = np.searchsorted(bq, qtimes, side="right")
    qpitches = np.array([r["pitch"] for r in qruns], dtype=int)
    if not np.array_equal(qpitches[qrun_index], qlabels):
        raise ArithmeticError("query-row contradiction in feasible correspondence")
    mapped_h = scale*(htimes-horigin)+offset+qorigin
    inside = (mapped_h >= qtimes[0]) & (mapped_h <= qtimes[-1])
    hrun_index = np.searchsorted(bq, mapped_h[inside], side="right")
    converted_h = np.where(hlabels[inside] == SILENCE, SILENCE, hlabels[inside]+shift)
    if not np.array_equal(qpitches[hrun_index], converted_h):
        raise ArithmeticError("history-row contradiction in feasible correspondence")
    start = horigin-offset/scale
    end = horigin+(qend-offset)/scale
    global_offset = qorigin+offset-scale*horigin
    vertices = np.stack(polygon)
    starts = horigin-vertices[:,1]/vertices[:,0]
    ends = horigin+(qend-vertices[:,1])/vertices[:,0]
    offsets = qorigin+vertices[:,1]-vertices[:,0]*horigin
    correspondence = []
    for qr, hr in zip(qruns, hruns):
        correspondence.append({"query_pitch": qr["pitch"], "history_pitch": hr["pitch"],
                               "query_row_ids": qr["row_ids"],
                               "history_row_ids": hr["row_ids"],
                               "query_interval": [qr["first"], qr["last"]],
                               "history_interval": [hr["first"], hr["last"]]})
    return {"start": float(start), "end": float(end), "center": float((start+end)/2),
            "shift": int(shift), "scale": scale, "stretch": scale,
            "scale_range": [float(vertices[:,0].min()), float(vertices[:,0].max())],
            "offset": float(global_offset),
            "offset_range": [float(offsets.min()), float(offsets.max())],
            "start_range": [float(starts.min()), float(starts.max())],
            "end_range": [float(ends.min()), float(ends.max())],
            "parameter_uncertain": bool(np.ptp(vertices[:,0]) > _tol(*vertices[:,0]) or
                                        np.ptp(offsets) > _tol(*offsets)),
            "feasible_polygon": [[float(a), float(qorigin+b-a*horigin)] for a,b in vertices],
            "polygon_coordinate_order": ["scale", "global_offset"],
            "polygon_is_closure": True,
            "constraints": [{"scale_coefficient": aa, "offset_coefficient": bb,
                             "upper_bound": limit, "strict": strict, "reason": name}
                            for aa,bb,limit,strict,name in constraints],
            "constraint_coordinate_origins": {"query": qorigin, "history": horigin},
            "local_representative": [scale, offset], "boundary_witnesses": boundaries,
            "correspondence": correspondence,
            "history_support": [float(x) for x in history_support],
            "verified_query_rows": [int(x) for x in qids],
            "verified_history_rows": [int(x) for x in hids[inside]],
            "query_rows_verified": int(len(qids)), "query_rows_skipped": 0,
            "query_runs_verified": len(qruns), "query_runs_skipped": 0,
            "history_rows_verified": int(inside.sum()), "contradictions": 0,
            "continuous_exact_support_verified": bool(exact), "evidence_score": 1.0}


def _validate_input(state, exact):
    allowed = {"t", "rms", "unit", "clean", "available_at"}
    if exact:
        allowed |= {"events", "segments", "event_left_clipped", "event_right_clipped"}
    if set(state)-allowed:
        raise ValueError("unexpected predictor input keys: "+str(sorted(set(state)-allowed)))
    for key in ("t", "rms", "unit", "clean"):
        if key not in state:
            raise ValueError("missing observation array: "+key)
    t = np.asarray(state["t"], dtype=np.float64)
    rms = np.asarray(state["rms"], dtype=np.float64)
    unit = np.asarray(state["unit"])
    clean = np.asarray(state["clean"], dtype=np.float64)
    if t.ndim != 1 or rms.shape != t.shape or unit.shape != t.shape or clean.shape != (len(t),129):
        raise ValueError("invalid observation array shapes")
    if not all(np.isfinite(a).all() for a in (t,rms,unit,clean)):
        raise ValueError("nonfinite observation")
    if len(t)>1 and not np.all(np.diff(t)>0):
        raise ValueError("timestamps must be unique and increasing")
    if len(t)>1 and not np.all(np.diff(unit)>=0):
        raise ValueError("completed-unit availability must be monotone")
    if not np.all(unit == np.floor(unit)):
        raise ValueError("nonintegral unit number")
    if len(t) and not (np.all((clean == 0)|(clean == 1)) and np.all(clean.sum(1)==1)):
        raise ValueError("clean input must be one-hot monophonic pitch/silence")
    if np.any(t < unit) or np.any(t >= unit+1):
        raise ValueError("sample is outside its completed one-second unit")
    if "available_at" in state:
        available = np.asarray(state["available_at"],dtype=np.float64)
        if available.shape != t.shape or not np.isfinite(available).all():
            raise ValueError("invalid availability array")
        if not np.array_equal(available,unit+1):
            raise ValueError("observation must become available at completed unit end")
    labels = np.argmax(clean,axis=1) if len(t) else np.array([],dtype=int)
    events = None
    if exact:
        if "events" not in state or "segments" not in state:
            raise ValueError("exact diagnostic requires events and retained segments")
        events = np.asarray(state["events"],dtype=np.float64)
        support = np.asarray(state["segments"],dtype=np.float64)
        if events.ndim != 2 or events.shape[1] != 3 or not np.isfinite(events).all():
            raise ValueError("events must be finite N by 3 [on,off,MIDI]")
        if support.ndim != 2 or support.shape[1] != 2 or not np.isfinite(support).all():
            raise ValueError("segments must be finite N by 2")
        if len(support) and (np.any(support[:,1] <= support[:,0]) or
                            np.any(support[1:,0] < support[:-1,1])):
            raise ValueError("retained segments must be positive, sorted, disjoint")
        if len(events) and (np.any(events[:,1] <= events[:,0]) or
                           np.any(events[1:,0] < events[:-1,1]) or
                           np.any(events[:,2] < 0) or np.any(events[:,2] > 127) or
                           np.any(events[:,2] != np.floor(events[:,2]))):
            raise ValueError("exact events must be ordered, positive, nonoverlapping MIDI intervals")
        for on,off,_ in events:
            if not any(lo <= on and off <= hi for lo,hi in support):
                raise ValueError("exact event is outside a single retained segment")
        for time,label in zip(t,labels):
            if not any(lo <= time < hi for lo,hi in support):
                raise ValueError("row outside exact retained support")
            if _event_at(events,time)[0] != label:
                raise ValueError("exact events disagree with received sample evidence")
        for key in ("event_left_clipped", "event_right_clipped"):
            if key in state and np.asarray(state[key]).shape != (len(events),):
                raise ValueError("event clipping flag shape")
    return t,rms,unit,clean,labels,events


def predict(state, exact=False):
    """Return all fully consistent occurrences; accept only one distinct region.

    Unexpected/invalid inputs raise ValueError: callers must record INVALID, not
    count malformed input as a scientific rejection. No hidden repair is used.
    """
    t,rms,unit,clean,labels,events = _validate_input(state,exact)
    base = {"method": "G-exact-score" if exact else "G", "accepted": False,
            "selected": None, "hypothesis": None, "candidates": [],
            "distance": None, "reason": None, "candidate_count": 0,
            "query_rows_skipped": 0, "contradictions": 0,
            "parameter_uncertain": None,
            "transform_convention": "query_time=scale*history_time+offset;query_pitch=history_pitch+shift"}
    loud = np.flatnonzero(rms>1e-4)
    if not len(loud):
        base["reason"] = "no observed query"
        return base
    end = t[loud[-1]]
    qi = np.flatnonzero((t>end-QUERY_SECONDS+1e-8)&(t<=end+1e-8))
    base["query_row_ids"] = [int(x) for x in qi]
    base["query_rows_available"] = int(len(qi))
    if len(qi)<12:
        base["reason"] = "insufficient query"
        return base
    base["query_support"] = [float(t[qi[0]]),float(t[qi[-1]])]
    base["query_display_bin_support"] = [float(t[qi[0]]-.05),float(t[qi[-1]]+.05)]
    if len(_segments(t[qi])) != 1:
        base["reason"] = "query contains missing observation support"
        return base
    hi = np.flatnonzero(unit<unit[qi[0]])
    base["history_row_ids"] = [int(x) for x in hi]
    base["history_rows_available"] = int(len(hi))
    if not len(hi):
        base["reason"] = "no earlier retained observations"
        return base
    qtimes,qlabels = t[qi],labels[qi]
    qruns = (_exact_runs(events, float(qtimes[0]), float(qtimes[-1])) if exact
             else _row_runs(qtimes,qlabels,qi))
    base["query_run_count"] = len(qruns)
    base["query_pitch_runs"] = [r["pitch"] for r in qruns]
    candidates = []
    total_windows = 0
    pitch_consistent = 0
    components = _segments(t[hi])
    base["history_component_supports"] = [[float(t[hi[a]]),float(t[hi[b-1]])]
                                         for a,b in components]
    for component,(a,b) in enumerate(components):
        ids = hi[a:b]
        # A component with one point cannot cover a positive-duration query.
        if len(ids)<2:
            continue
        htimes,hlabels = t[ids],labels[ids]
        support = [float(htimes[0]),float(htimes[-1])]
        hruns = (_exact_runs(events,*support) if exact else _row_runs(htimes,hlabels,ids))
        for start_run in range(len(hruns)-len(qruns)+1):
            window = hruns[start_run:start_run+len(qruns)]
            for shift in SHIFTS:
                total_windows += 1
                if not all(_pitch_ok(q["pitch"],h["pitch"],shift) for q,h in zip(qruns,window)):
                    continue
                pitch_consistent += 1
                candidate = _solve_candidate(qruns,window,qtimes,qlabels,htimes,hlabels,
                                             ids,qi,support,shift,exact)
                if candidate is not None:
                    candidate["occurrence_key"] = [component,start_run,start_run+len(qruns)-1,shift]
                    candidate["history_component"] = component
                    candidate["history_run_range"] = [start_run,start_run+len(qruns)-1]
                    candidates.append(candidate)
    # Ordering only serializes evidence; it does not choose an identity.
    candidates.sort(key=lambda x: tuple(x["occurrence_key"]))
    base["candidates"] = candidates
    base["candidate_count"] = len(candidates)
    base["search"] = {"run_windows_with_shifts": total_windows,
                      "pitch_consistent_windows": pitch_consistent,
                      "feasible_windows": len(candidates), "all_windows_enumerated": True}
    if not candidates:
        base["reason"] = "no full-consistent occurrence"
    elif len(candidates)>1:
        base["reason"] = "ambiguous distinct full-consistent occurrences"
    else:
        selected = candidates[0]
        base.update(accepted=True, selected=selected, hypothesis=selected, distance=0.0,
                    reason="unique full-consistent occurrence",
                    parameter_uncertain=selected["parameter_uncertain"],
                    query_rows_verified=selected["query_rows_verified"],
                    query_runs_verified=selected["query_runs_verified"])
    return base
