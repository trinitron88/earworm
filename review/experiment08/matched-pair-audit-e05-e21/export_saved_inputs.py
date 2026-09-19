"""Select existing saved evidence and descriptions; no audio or experiment execution."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np

QUERIES=[f'{g}_query_{s}_delete_closed' for g in ('e05','e21') for s in ('a','b')]
PREVIOUS='review/experiment08/calibration-audit/completion-20260919'
EVENT_KEYS=['event_onset_s','event_offset_s','event_pitch_semitones','event_pitch_span_cents','event_phase_fraction','event_bend_peak_cents']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def score(e,c):
    return float(np.dot((np.asarray(e['features'])-c['mean'])/c['scale'],c['coef'])+c['intercept']) if e['available'] else -1e6

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--snapshot-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    src,snap,out=a.source_root,a.snapshot_root,a.out;out.mkdir(parents=True,exist_ok=True)
    c=json.loads((src/'work/accounts_results/frozen_config.json').read_text());previous=json.loads((snap/PREVIOUS/'input_identifiers.json').read_text())
    inputs=[]
    for rel in ['work/accounts_results/development_pairs.json','work/accounts_results/held_out_pairs.json','work/accounts_results/frozen_config.json','work/accounts_results/protocol.json']:
        expected=next(x['sha256'] for x in previous['original_inputs'] if x['path']==rel)
        assert sha(src/rel)==expected,rel
        if (snap/rel).exists():assert sha(snap/rel)==expected,rel
        inputs.append(dict(path=rel,sha256=expected,bytes=(src/rel).stat().st_size))
    for name,h in c['source_sha256'].items():assert sha(src/'work'/name)==h==sha(snap/'work'/name)
    compact=snap/PREVIOUS/'candidate_evidence.jsonl';assert sha(compact)==previous['export']['sha256']
    exported={x['query_id']:x for x in map(json.loads,compact.read_text().splitlines())}
    tables={g:json.loads((src/'work/accounts_results'/f).read_text()) for g,f in [('e05','development_pairs.json'),('e21','held_out_pairs.json')]}
    timings=json.loads((src/'work/accounts_features/timings.json').read_text())
    selected=[];needed=set(QUERIES)
    for qid in QUERIES:
        q=exported[qid];original=tables[qid[:3]][qid]
        for rid,e in q['candidates'].items():
            assert all(original[rid]['evidence'][k]==v for k,v in e.items()),(qid,rid)
        scores={rid:score(e,c) for rid,e in q['candidates'].items()}
        mx=max(scores[rid] for rid in q['absent_history'])
        distractors=[rid for rid in q['present_history'] if rid!=q['true_reference']]
        dm=max(scores[rid] for rid in distractors)
        exact_abs=[rid for rid in q['absent_history'] if scores[rid]==mx]
        near_abs=[rid for rid in q['absent_history'] if abs(scores[rid]-mx)<1e-9]
        exact_d=[rid for rid in distractors if scores[rid]==dm]
        near_d=[rid for rid in distractors if abs(scores[rid]-dm)<1e-9]
        ids=sorted(set([q['true_reference']]+exact_abs+near_abs+exact_d+near_d));needed.update(ids)
        selected.append(dict(query=q,selected_candidate_ids=ids,
            selection=dict(absent_exact_maxima=exact_abs,absent_within_1e_9_of_max=near_abs,present_distractor_exact_maxima=exact_d,present_distractor_within_1e_9_of_max=near_d),
            saved_candidate_evidence={rid:original[rid]['evidence'] for rid in ids}))
    descriptions={};digests=[]
    for bid in sorted(needed):
        rel=f'work/accounts_features/{bid}.npz';p=src/rel
        if not p.exists():raise FileNotFoundError('Required saved description missing: '+rel)
        with np.load(p,allow_pickle=False) as z:d={k:z[k] for k in z.files}
        h=hashlib.sha256()
        for k in sorted(d):
            v=np.asarray(d[k]);h.update(k.encode());h.update(str(v.dtype).encode());h.update(str(v.shape).encode());h.update(v.tobytes())
        original_digest=h.hexdigest();assert original_digest==timings[bid]['description_digest'],bid
        keys=EVENT_KEYS+(['frame_time_s','frame_rms'] if bid in QUERIES else [])
        descriptions[bid]={k:dict(dtype=str(d[k].dtype),values=d[k].tolist()) for k in keys}
        inputs.append(dict(path=rel,sha256=sha(p),bytes=p.stat().st_size))
        digests.append(dict(block_id=bid,saved_description_digest=original_digest,matched_original_timing_record=True))
    rel='work/accounts_features/timings.json';inputs.append(dict(path=rel,sha256=sha(src/rel),bytes=(src/rel).stat().st_size))
    write(out/'saved_inputs.json',dict(queries=selected,descriptions=descriptions))
    write(out/'input_identifiers.json',dict(instruction_id='earworm-e05-e21-matched-pair-v1',instruction_comment_id=5743879321,
        reviewed_snapshot='3da31dacd1abda91a37a8a8cb5d9c200335ea3f6',base_merge='f463c0673035bdf4b0b20bdb715d5442b398ddb4',
        original_execution_git_revision=None,original_inputs=inputs,
        frozen_source_sha256=c['source_sha256'],original_description_digest_checks=digests,
        prior_compact_export=dict(path=str(Path(PREVIOUS)/'candidate_evidence.jsonl'),sha256=sha(compact)),
        selected_export=dict(path='saved_inputs.json',sha256=sha(out/'saved_inputs.json'),bytes=(out/'saved_inputs.json').stat().st_size),
        method='Exact selection of existing pair evidence, retained paths, and typed acoustic-description arrays; no acoustic extraction, alignment search, training, or regeneration.',
        hash_timing='Local input hashes identify the files used now; they are not newly asserted pre-run commitments. Full cached-description digests also match original extraction timing records.'))
    print(json.dumps({'queries':len(selected),'selected_descriptions':len(descriptions),'export_bytes':(out/'saved_inputs.json').stat().st_size}))

if __name__=='__main__':main()
