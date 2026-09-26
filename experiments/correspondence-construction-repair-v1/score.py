"""Saved-response arithmetic only. Never imports or executes a matcher."""
from __future__ import annotations
import datetime
import json
from pathlib import Path

METHODS = ('D', 'G', 'G-exact')
POSITIVE = ('unchanged', 'transpose', 'stretch')

def read(path):
    return json.loads(Path(path).read_text())

def expected_readouts(root, suite):
    base = Path(root) / 'inputs' / suite
    manifest = read(base / 'input-manifest.json')
    for session in manifest['sessions']:
        sid = session['session_id']
        folder = base / session.get('path', sid)
        labels = read(folder / 'evaluatorlabels.json')
        modes = ('full', 'recent', 'removed') if suite == 'panel' and labels['positive'] else ('full',)
        for method in METHODS:
            for mode in modes:
                yield sid, folder, labels, method, mode, Path(root) / 'outputs' / suite / sid / method / mode

def record_score(suite, sid, labels, method, mode, answer):
    accepted = bool(answer.get('accepted'))
    h = answer.get('selected') if accepted else None
    source = labels.get('source_interval')
    center = h.get('center', (h['start'] + h['end']) / 2) if h else None
    positive = bool(labels.get('positive', False))
    correct = bool(positive and accepted and h and source and source[0] <= center < source[1] and mode == 'full')
    shift = labels.get('truth_shift', labels.get('expected_shift'))
    scale = labels.get('truth_stretch', labels.get('expected_scale'))
    estimate = h.get('scale', h.get('stretch')) if h else None
    scale_error = abs(estimate / scale - 1) if estimate is not None and scale not in (None, 0) else None
    shift_ok = bool(correct and shift is not None and h.get('shift') == shift)
    scale_ok = bool(correct and scale_error is not None and scale_error <= .1)
    localization = None
    # D reports outer 100-ms bin edges; G reports observed sample centers.
    query_support = answer.get('query_support')
    if h and query_support and source and labels.get('query_interval') and scale:
        target = [source[0] + (x - labels['query_interval'][0]) / scale for x in query_support]
        errors = [abs(h['start'] - target[0]), abs(h['end'] - target[1])]
        localization = {'expected_mapped_fragment': target, 'endpoint_errors_seconds': errors,
                        'both_within_0_1_seconds': all(x <= .1 for x in errors),
                        'scope': 'diagnostic only; method-specific query support, not a gate'}
    return {'suite': suite, 'session_id': sid, 'group': labels.get('group', sid),
            'stratum': labels.get('stratum', 'diagnostic'), 'cell': labels.get('cell', sid),
            'method': method, 'mode': mode, 'positive': positive, 'accepted': accepted,
            'correct_source': correct, 'accepted_correct_source_exact_shift': shift_ok,
            'accepted_correct_source_scale_within_10_percent': scale_ok,
            'joint_identity_shift_scale': bool(shift_ok and scale_ok),
            'source_center': center, 'estimated_shift': h.get('shift') if h else None,
            'true_shift': shift, 'estimated_scale': estimate, 'true_scale': scale,
            'scale_relative_error': scale_error,
            'parameter_uncertain': h.get('parameter_uncertain') if h else None,
            'scale_range': h.get('scale_range') if h else None,
            'localization': localization, 'candidate_count': answer.get('candidate_count', len(answer.get('candidates', []))),
            'reason': answer.get('reason'), 'coverage': answer.get('coverage', {
                'query_rows_available': answer.get('query_rows_available'),
                'query_rows_verified': h.get('query_rows_verified') if h else 0,
                'query_rows_skipped': answer.get('query_rows_skipped'),
                'query_runs_verified': h.get('query_runs_verified') if h else 0}),
            'response_path': f'outputs/{suite}/{sid}/{method}/{mode}/response.json'}

def counts(rows):
    n = len(rows)
    fields = ('accepted', 'correct_source', 'accepted_correct_source_exact_shift',
              'accepted_correct_source_scale_within_10_percent', 'joint_identity_shift_scale')
    out = {'denominator': n, **{k: sum(bool(r[k]) for r in rows) for k in fields}}
    retrieved = [r for r in rows if r['correct_source']]
    out['conditional_on_correct_source'] = {
        'denominator': len(retrieved),
        'exact_shift': sum(r['accepted_correct_source_exact_shift'] for r in retrieved),
        'scale_within_10_percent': sum(r['accepted_correct_source_scale_within_10_percent'] for r in retrieved)}
    out['uncertain_accepted'] = sum(r['accepted'] and r['parameter_uncertain'] is True for r in rows)
    out['localization'] = {'denominator': sum(r['localization'] is not None for r in rows),
                          'within_0_1_seconds': sum(r['localization'] is not None and r['localization']['both_within_0_1_seconds'] for r in rows)}
    return out

def score_all(root, validation=None):
    root = Path(root)
    start_time = datetime.datetime.now(datetime.timezone.utc)
    started = start_time.isoformat()
    response_files = list((root/'outputs').glob('**/response.json'))
    latest_response = max((p.stat().st_mtime for p in response_files), default=0)
    if validation is None:
        validation = read(root / 'validation.json')
    records, errors = [], []
    if latest_response > start_time.timestamp():
        errors.append({'path':'outputs','error':'A response file became available after scoring began'})
    for suite in ('panel', 'diagnostics'):
        for sid, folder, labels, method, mode, out in expected_readouts(root, suite):
            try:
                records.append(record_score(suite, sid, labels, method, mode, read(out / 'response.json')))
            except Exception as e:
                errors.append({'path': str(out.relative_to(root)), 'error': type(e).__name__ + ': ' + str(e)})
    panel = [r for r in records if r['suite'] == 'panel']
    summaries = {}
    for method in METHODS:
        rr = [r for r in panel if r['method'] == method]
        cells = {c: counts([r for r in rr if r['mode'] == 'full' and r['cell'] == c]) for c in POSITIVE}
        foils = counts([r for r in rr if r['mode'] == 'full' and not r['positive']])
        removed = counts([r for r in rr if r['mode'] == 'removed'])
        recent = counts([r for r in rr if r['mode'] == 'recent'])
        gates = {f'{c}/{field}': cells[c]['denominator'] == 8 and cells[c][field] >= 7
                 for c in POSITIVE for field in ('correct_source', 'accepted_correct_source_exact_shift', 'accepted_correct_source_scale_within_10_percent')}
        gates.update(foil_refusal=foils['denominator'] == 16 and foils['accepted'] <= 1,
                     removed_refusal=removed['denominator'] == 24 and removed['accepted'] <= 2,
                     recent_refusal=recent['denominator'] == 24 and recent['accepted'] <= 2,
                     complete_readouts=len(rr) == 88, integrity=bool(validation.get('passed')))
        strata = {s: {c: counts([r for r in rr if r['stratum'] == s and r['mode'] == 'full' and r['cell'] == c])
                      for c in (*POSITIVE, 'inventory_foil', 'near_foil')}
                  for s in sorted({r['stratum'] for r in rr})}
        for s in strata:
            strata[s]['source_removal'] = counts([r for r in rr if r['stratum']==s and r['mode']=='removed'])
            strata[s]['recent_only'] = counts([r for r in rr if r['stratum']==s and r['mode']=='recent'])
        families = {g: {f'{c}/{m}': counts([r for r in rr if r['group']==g and r['cell']==c and r['mode']==m])
                        for c,m in sorted({(r['cell'],r['mode']) for r in rr if r['group']==g})}
                    for g in sorted({r['group'] for r in rr})}
        summaries[method] = {'positive_cells': cells, 'foils': foils, 'source_removal': removed,
                             'recent_only': recent, 'gates': gates, 'meets_all_gates': all(gates.values()),
                             'eligible_equal_observation_candidate': method in ('D', 'G'), 'strata': strata, 'families': families}
    certificate = root / 'inputs/diagnostics/ambiguity-certificate.json'
    cert = read(certificate) if certificate.exists() else {}
    witness = bool(validation.get('ambiguity_certificate_verified'))
    selected = None
    if errors or not validation.get('passed') or len(records) != 288:
        branch, disposition = 'INVALID', 'Withhold scientific disposition; inspect saved software, completeness, access or resource failures.'
    elif summaries['D']['meets_all_gates'] or summaries['G']['meets_all_gates']:
        selected = 'D' if summaries['D']['meets_all_gates'] else 'G'
        branch, disposition = 'A', 'Select ' + selected + ' as the development diagnostic reference; no held-out or audio-route qualification.'
    elif witness and len([r for r in records if r['suite'] == 'diagnostics']) == 24:
        branch, disposition = 'B', 'Withhold method qualification; revise only the witnessed origin contract to permit equivalent occurrence sets or abstention for observationally identical origins.'
    else:
        branch, disposition = 'C', 'Withhold both implementations; retain D for historical comparability and separate identity, pitch, scale and refusal failures.'
    return {'schema': 'correspondence-saved-response-scoring-v1', 'scoring_started_utc': started,
            'response_files_present_before_scoring':len(response_files),
            'latest_response_mtime_utc':datetime.datetime.fromtimestamp(latest_response,datetime.timezone.utc).isoformat(),
            'output_before_label_scoring':len(response_files)==288 and latest_response<=start_time.timestamp(),
            'branch': branch, 'disposition': disposition, 'selected_method': selected,
            'development_only': True, 'panel_readouts': len(panel), 'diagnostic_readouts': len(records)-len(panel),
            'summaries': summaries, 'records': records, 'errors': errors,
            'ambiguity_certificate_verified': witness,
            'ambiguity_scope': cert.get('scope', 'Separate deliberately constructed diagnostic; does not establish a musical-panel ambiguity.'),
            'exact_score_not_selectable': True,
            'localization_threshold_seconds': .1, 'localization_is_gate': False,
            'validation_passed': bool(validation.get('passed'))}

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('root', nargs='?', default=Path(__file__).parent)
    args = p.parse_args(); result = score_all(args.root)
    (Path(args.root)/'score.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: result[k] for k in ('branch', 'selected_method', 'panel_readouts', 'diagnostic_readouts')}))
