"""Independent stdlib reconciliation of the published selection, bytes and tables.

Does not import the exporter, analysis script, experiment code, NumPy or plotting.
Original full-cache availability is a separate, explicitly local provenance check.
"""
import csv
import hashlib
import json
import math
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = HERE.parent / 'equal-vector-alignment-audit'


def read_json(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(entry):
    fmt, name = {'<f4': ('<f', 'float32'), '|b1': ('?', 'bool')}[entry['dtype_str']]
    assert entry['dtype'] == name
    assert entry['shape'] == [len(entry['values'])]
    specials = {s['index']: s for s in entry['nonfinite']}
    assert len(specials) == len(entry['nonfinite'])
    assert set(specials) == {i for i, v in enumerate(entry['values']) if v is None}
    buf, values = bytearray(), []
    for i, value in enumerate(entry['values']):
        if i in specials:
            b = bytes.fromhex(specials[i]['raw_bytes_hex'])
            value = struct.unpack(fmt, b)[0]
            assert not math.isfinite(value)
            assert specials[i]['kind'] == ('nan' if math.isnan(value) else '+inf' if value > 0 else '-inf')
        else:
            assert math.isfinite(value)
            if name == 'bool':
                assert isinstance(value, bool)
            b = struct.pack(fmt, value)
            assert struct.unpack(fmt, b)[0] == value
        buf.extend(b); values.append(value)
    assert hashlib.sha256(buf).hexdigest() == entry['raw_bytes_sha256']
    return values


def equal_cell(cell, expected, converted=False):
    if expected is None:
        assert cell == ''
    elif isinstance(expected, bool):
        assert cell == str(expected)
    else:
        actual = float(cell)
        if math.isnan(expected):
            assert math.isnan(actual)
        elif converted:
            assert math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12)
        else:
            assert actual == expected, (cell, expected)


def main():
    ids = read_json(HERE/'input_identifiers.json')
    for item in ids['exports']:
        path = HERE/item['path']
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    for item in ids['prior_audit_inputs']:
        assert sha(ROOT/item['path']) == item['sha256']
    for name, digest in ids['frozen_source_sha256'].items():
        assert sha(ROOT/'work'/name) == digest
    prior = read_json(PRIOR/'saved_inputs.json')
    selected = [(q['query_id'], i) for q in rows(PRIOR/'results/query_summary.csv')
                for i in json.loads(q['query_events_outside_saved_eligible_set'])]
    data = read_json(HERE/'saved_frames.json')
    assert [(e['query_id'], e['event_index']) for e in data['events']] == selected
    assert len(selected) == len({q for q, _ in selected}) == 10
    inv = read_json(HERE/'inventory.json')
    assert (inv['status'], inv['selected_events'], inv['exported_events'], inv['in_bound_frames']) == ('complete', 10, 10, 380)
    observed, summaries = rows(HERE/'results/frames.csv'), rows(HERE/'results/event_summary.csv')
    assert len(observed) == 380 and len(summaries) == 10
    all_counts = dict(events=10, frames=0, interior_frames=0, voiced_frames=0, phase_refined_frames=0,
                      finite_positive_pitch_frames=0, nonfinite_pitch_frames=0, absent_arrays=0)
    all_pitch, checked_arrays, cursor = [], 0, 0
    for e, inventory, summary in zip(data['events'], inv['events'], summaries):
        qid, idx = e['query_id'], e['event_index']
        assert inventory['query_id'] == summary['query_id'] == qid
        desc = prior['descriptions'][qid]
        assert e['onset_s'] == desc['event_onset_s']['values'][idx]
        assert e['offset_s'] == desc['event_offset_s']['values'][idx]
        assert e['interior_start_s'] == e['onset_s']+.018
        assert e['interior_end_s'] == e['offset_s']-.018
        assert e['absent_arrays'] == [] and set(e['arrays']) == set(data['fields'])
        a = {key: decode(value) for key, value in e['arrays'].items()}
        checked_arrays += len(a)
        times = a['frame_time_s']; n = len(times)
        assert n == inventory['in_bound_frame_count'] == 38
        assert all(len(v) == n for v in a.values())
        assert all(e['onset_s'] <= t <= e['offset_s'] for t in times)
        assert all(x < y for x, y in zip(times, times[1:]))
        assert e['original_frame_indices'] == list(range(e['original_frame_indices'][0], e['original_frame_indices'][0]+n))
        assert 0 < e['original_frame_indices'][0] < e['original_frame_indices'][-1] < e['original_frame_count']-1
        assert e['adjacent_frame_before_s'] < e['onset_s'] and e['adjacent_frame_after_s'] > e['offset_s']
        for key, values in a.items():
            assert inventory['array_inventory'][key] == dict(present=True, dtype=e['arrays'][key]['dtype'], nonfinite_count=sum(not math.isfinite(x) for x in values))
        inside = [e['interior_start_s'] <= t <= e['interior_end_s'] for t in times]
        for i, t in enumerate(times):
            row = observed[cursor]; cursor += 1
            assert row['query_id'] == qid
            for key, val in {'event_index':idx, 'frame_order_0_based':i, 'original_frame_index':e['original_frame_indices'][i],
                             'event_onset_s':e['onset_s'], 'event_offset_s':e['offset_s'],
                             'time_after_event_onset_s':t-e['onset_s'], 'inside_frozen_18ms_interior':inside[i],
                             **{k:v[i] for k,v in a.items()}}.items():
                equal_cell(row[key], val)
            for field, status_key, semi_key in [('frame_pitch_hz','pitch_status','pitch_semitones_re_220hz'),
                    ('frame_spectral_peak_hz','spectral_peak_status','spectral_peak_semitones_re_220hz')]:
                value = a[field][i]
                assert row[status_key] == ('nan' if math.isnan(value) else 'finite_positive')
                equal_cell(row[semi_key], 12*math.log2(value/220) if math.isfinite(value) and value > 0 else None, True)
        valid = [i for i,v in enumerate(a['frame_pitch_hz']) if math.isfinite(v) and v > 0]
        phase = [i for i in valid if a['frame_phase_refined'][i]]
        checks = {k:e[k] for k in ['event_index','onset_s','offset_s','interior_start_s','interior_end_s']}
        checks.update(frame_n=n, interior_frame_n=sum(inside), absent_array_n=0,
            voiced_true_n=sum(a['frame_voiced']), phase_refined_true_n=sum(a['frame_phase_refined']),
            finite_positive_pitch_n=len(valid), nonfinite_pitch_n=sum(not math.isfinite(v) for v in a['frame_pitch_hz']),
            interior_voiced_n=sum(v for i,v in enumerate(a['frame_voiced']) if inside[i]),
            interior_phase_refined_n=sum(v for i,v in enumerate(a['frame_phase_refined']) if inside[i]),
            interior_finite_positive_pitch_n=sum(inside[i] for i in valid),
            first_finite_pitch_time_s=times[valid[0]],first_finite_pitch_hz=a['frame_pitch_hz'][valid[0]],
            last_finite_pitch_time_s=times[valid[-1]],last_finite_pitch_hz=a['frame_pitch_hz'][valid[-1]],
            first_phase_refined_pitch_time_s=times[phase[0]],first_phase_refined_pitch_hz=a['frame_pitch_hz'][phase[0]])
        for key in ['frame_rms','frame_energy_dbfs','frame_pitch_hz','frame_spectral_peak_hz','frame_spectral_centroid_hz']:
            finite = [v for v in a[key] if math.isfinite(v)]
            checks.update({key+'_min':min(finite),key+'_max':max(finite),key+'_finite_n':len(finite)})
        for key, value in checks.items():
            equal_cell(summary[key], value)
        for suffix in ['min','max']:
            equal_cell(summary['pitch_semitones_'+suffix],12*math.log2(checks['frame_pitch_hz_'+suffix]/220),True)
        assert set(summary) == set(checks)|{'query_id','pitch_semitones_min','pitch_semitones_max'}
        for out_key, key in [('frames','frame_n'),('interior_frames','interior_frame_n'),('voiced_frames','voiced_true_n'),
                ('phase_refined_frames','phase_refined_true_n'),('finite_positive_pitch_frames','finite_positive_pitch_n'),
                ('nonfinite_pitch_frames','nonfinite_pitch_n')]:
            all_counts[out_key] += checks[key]
        all_pitch.extend(a['frame_pitch_hz'][i] for i in valid)
    saved_summary = read_json(HERE/'results/summary.json')
    assert all(saved_summary[k] == v for k,v in all_counts.items())
    assert saved_summary['pitch_hz_range'] == [min(all_pitch),max(all_pitch)]
    old_expectations = rows(PRIOR/'results/missing_event_hypotheses.csv')
    wanted = [dict(source_data_row_1_based=str(i+1), **r) for i,r in enumerate(old_expectations) if r['query_id'] in {q for q,_ in selected}]
    assert rows(HERE/'memory_expectations.csv') == wanted
    assert len(wanted) == inv['memory_expectation_rows'] == 130
    assessments = rows(HERE/'event_assessments.csv')
    assert [(r['query_id'],int(r['event_index'])) for r in assessments] == selected
    assert all(r['assessment'] in {'ordered_structure_visible','broad_or_unstable_trace_only','insufficient_evidence'} for r in assessments)
    print(json.dumps({'status':'pass', **all_counts, 'exact_typed_array_hashes':checked_arrays,
        'prior_input_hashes_checked':len(ids['prior_audit_inputs']), 'frozen_source_hashes_checked':len(ids['frozen_source_sha256']),
        'exact_expectation_rows':len(wanted), 'event_assessment_rows':len(assessments),
        'verification_limit':'Checks assessment coverage, not visual-interpretation truth. Full original cache hashes/digests and export completeness were additionally reconciled locally; they cannot be independently rechecked from the scoped export alone.'},indent=2))


if __name__ == '__main__':
    main()
