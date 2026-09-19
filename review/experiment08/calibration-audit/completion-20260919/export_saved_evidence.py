"""Export existing pair evidence only; never imports or runs an experiment pipeline."""
import argparse, hashlib, json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--snapshot-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    src, snap, out = args.source_root, args.snapshot_root, args.out
    out.mkdir(parents=True, exist_ok=True)
    config = json.loads((src/'work/accounts_results/frozen_config.json').read_text())
    # Match source-hash provenance and the published frozen configuration.
    for name, expected in config['source_sha256'].items():
        assert digest(src/'work'/name) == expected == digest(snap/'work'/name), name
    for rel in ['work/accounts_results/frozen_config.json', 'work/accounts_results/protocol.json']:
        assert digest(src/rel) == digest(snap/rel), rel
    assert digest(src/'work/accounts_results/protocol.json') == config['protocol_sha256']
    manifest = json.loads((src/'work/accounts_stimuli/manifest.json').read_text())
    published = json.loads((snap/'work/accounts_stimuli/manifest.json').read_text())
    # Publication changed only machine-specific audio paths; no other metadata changes.
    for data in (manifest, published):
        for block in data['blocks']:
            block.pop('audio_path', None)
    assert manifest == published
    groups = {g['id']: g for g in manifest['groups']}
    tables = {split: json.loads((src/rel).read_text()) for split, rel in [
        ('calibration', 'work/accounts_results/development_pairs.json'),
        ('held_out', 'work/accounts_results/held_out_pairs.json')]}
    rows = []
    for q in manifest['blocks']:
        if q['role'] != 'query' or q['split'] not in tables:
            continue
        if q['split'] == 'calibration' and q['phase'] != 'core':
            continue
        g = groups[q['group_id']]
        present = [q['reference_id']] + g['distractor_ids']
        other = g['reference_b_id'] if q['source'] == 'a' else g['reference_a_id']
        absent = [other] + g['distractor_ids']
        # All ten ordinary-history candidates; the separate ambiguity twin is excluded.
        ids = sorted(set(present + absent))
        candidates = {}
        for rid in ids:
            ev = tables[q['split']][q['id']][rid]['evidence']
            candidates[rid] = {k: ev[k] for k in ['available', 'features', 'reference_events', 'query_events']}
        rows.append(dict(query_id=q['id'], group_id=q['group_id'], split=q['split'],
                         length=g['length'], family=q['family'], phase=q['phase'], source=q['source'],
                         true_reference=q['reference_id'], present_history=present,
                         absent_history=absent, candidates=candidates))
    rows.sort(key=lambda r: (r['split'], r['query_id']))
    assert sum(r['split']=='calibration' for r in rows) == 120
    assert sum(r['split']=='held_out' for r in rows) == 576
    target = out/'candidate_evidence.jsonl'
    target.write_text(''.join(json.dumps(r, separators=(',', ':'), allow_nan=False)+'\n' for r in rows))
    rels = ['work/accounts_results/development_pairs.json', 'work/accounts_results/held_out_pairs.json',
            'work/accounts_stimuli/manifest.json', 'work/accounts_results/frozen_config.json',
            'work/accounts_results/protocol.json', 'work/accounts_results/trials.json',
            'work/accounts_results/posthoc_diagnostics.json']
    provenance = dict(parent_snapshot='b8b6e85ab184d8e243b1e40b7aea6500a31ac105',
        original_execution_git_revision=None,
        original_inputs=[dict(path=rel, sha256=digest(src/rel), bytes=(src/rel).stat().st_size) for rel in rels],
        frozen_source_sha256=config['source_sha256'],
        export=dict(path=target.name, sha256=digest(target), bytes=target.stat().st_size,
                    queries=len(rows), candidate_pairs=sum(len(r['candidates']) for r in rows)),
        method='Exact selection of saved numeric evidence features and evaluation metadata. No score fitting, acoustic extraction, alignment search, or audio regeneration.',
        exclusions='Fit groups, ambiguity-only twin, raw audio, full alignment paths, machine-local audio paths.',
        scoring_contract='Only available and features enter the frozen arithmetic. Group/family/source/length/history metadata route evaluation and stratification only.',
        provenance_limit='Pair-file hashes were captured for this export, after the original run; they identify these local saved originals but are not pre-run commitments. Frozen source/protocol hashes are the original recorded commitments.')
    (out/'input_identifiers.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(json.dumps(provenance['export'], indent=2))


if __name__ == '__main__':
    main()
