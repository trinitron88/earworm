"""Read-only saved-evidence audit. No experiment-module imports, fitting, or audio I/O."""
import argparse, csv, hashlib, json, math
from collections import defaultdict
from pathlib import Path
import numpy as np


def load(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write_json(p, value): p.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
def write_csv(p, rows):
    with p.open('w', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)


def support(ev, config):
    # Unchanged arithmetic from frozen accounts_reader.score; only acoustic evidence enters.
    if not ev['available']: return -1e6
    x=(np.asarray(ev['features'])-config['mean'])/config['scale']
    return float(np.dot(x, config['coef'])+config['intercept'])


def metrics(rows, threshold):
    return dict(n=len(rows), correct_singletons=sum(r['true_score']>=threshold and r['present_distractor_max']<threshold for r in rows),
                absent_false_acceptances=sum(r['absent_max_score']>=threshold for r in rows))


def choose_threshold(rows):
    # Same candidate levels, <=5% constraint, and lexicographic tie-break as frozen runner.
    vals=np.unique([v for r in rows for v in r['scores'].values()])
    levels=np.r_[vals, np.nextafter(vals[-1], np.inf)]
    best=None
    for t in levels:
        m=metrics(rows, t)
        if m['absent_false_acceptances']/m['n'] > .05+1e-12: continue
        candidate=(m['correct_singletons'], -m['absent_false_acceptances'], float(t))
        if best is None or candidate>best: best=candidate
    return dict(threshold=best[2], **metrics(rows,best[2]))


def summarize(rows, threshold):
    out=metrics(rows, threshold)
    out['groups']=len(set(r['group_id'] for r in rows))
    out['unique_top_in_present_history']=sum(r['unique_top'] for r in rows)
    out['unique_top_but_rejected']=sum(r['unique_top'] and not r['accepted_correct'] for r in rows)
    for field in ['true_score', 'absent_max_score', 'true_margin', 'absent_margin', 'true_minus_absent_max']:
        v=[r[field] for r in rows]
        out[field]={k:float(n) for k,n in zip(['min','q25','median','q75','max'],np.quantile(v,[0,.25,.5,.75,1]))}
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--input',type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists() and any(a.out.iterdir()): raise ValueError('Choose a new empty output directory')
    a.out.mkdir(parents=True,exist_ok=True)
    config=load(a.root/'work/accounts_results/frozen_config.json');threshold=config['threshold']
    identifiers=load(a.input/'input_identifiers.json')
    assert sha(a.input/'candidate_evidence.jsonl')==identifiers['export']['sha256']
    for rel in ['work/accounts_results/frozen_config.json','work/accounts_results/protocol.json']:
        expected=next(i['sha256'] for i in identifiers['original_inputs'] if i['path']==rel)
        assert sha(a.root/rel)==expected,rel
    for name,expected in config['source_sha256'].items(): assert sha(a.root/'work'/name)==expected
    raw=[json.loads(line) for line in (a.input/'candidate_evidence.jsonl').read_text().splitlines()]
    manifest=load(a.root/'work/accounts_stimuli/manifest.json');blocks={b['id']:b for b in manifest['blocks']}
    groups={g['id']:g for g in manifest['groups']}
    scores_csv=[];rows=[];max_scalar_difference=0.
    for q in raw:
        b=blocks[q['query_id']];g=groups[q['group_id']]
        assert (q['split'],q['length'],q['family'],q['true_reference'])==(b['split'],g['length'],b['family'],b['reference_id'])
        assert q['present_history']==[b['reference_id']]+g['distractor_ids']
        other=g['reference_b_id'] if b['source']=='a' else g['reference_a_id']
        assert q['absent_history']==[other]+g['distractor_ids']
        assert set(q['candidates'])==set(q['present_history']+q['absent_history'])
        scores={rid:support(ev,config) for rid,ev in q['candidates'].items()}
        for rid,ev in q['candidates'].items():
            scalar=(math.fsum((v-m)/s*w for v,m,s,w in zip(ev['features'],config['mean'],config['scale'],config['coef']))+config['intercept']) if ev['available'] else -1e6
            max_scalar_difference=max(max_scalar_difference,abs(scalar-scores[rid]))
            scores_csv.append(dict(query_id=q['query_id'],candidate_id=rid,available=ev['available'],support_logit=scores[rid],in_present_history=rid in q['present_history'],in_absent_history=rid in q['absent_history']))
        pos=[rid for rid in q['present_history'] if scores[rid]>=threshold]
        neg=[rid for rid in q['absent_history'] if scores[rid]>=threshold]
        true=scores[q['true_reference']];mx=max(scores[rid] for rid in q['absent_history'])
        present_max=max(scores[rid] for rid in q['present_history'])
        top=[rid for rid in q['present_history'] if abs(scores[rid]-present_max)<1e-9]
        row={k:q[k] for k in ['query_id','group_id','split','length','family','true_reference']}
        row.update(true_score=true,absent_max_score=mx,true_margin=true-threshold,absent_margin=mx-threshold,
            true_minus_absent_max=true-mx,absent_max_ids='|'.join(rid for rid in q['absent_history'] if scores[rid]==mx),
            present_distractor_max=max(scores[rid] for rid in q['present_history'] if rid!=q['true_reference']),
            accepted_correct=pos==[q['true_reference']],absent_false_accept=bool(neg),unique_top=top==[q['true_reference']],
            scores=scores,accepted_present=pos,accepted_absent=neg)
        rows.append(row)
    assert max_scalar_difference<1e-12
    cal=[r for r in rows if r['split']=='calibration'];held=[r for r in rows if r['split']=='held_out']
    assert (len(cal),len(held))==(120,576)
    # Verify all saved held-out decisions without re-running the pipeline.
    with (a.root/'review/experiment08/primary_trials.csv').open() as f:
        archived={r['query_id']:r for r in csv.DictReader(f) if r['method']=='accounts'}
    for r in held:
        old=archived[r['query_id']]
        assert r['accepted_present']==json.loads(old['accepted_present']),r['query_id']
        assert r['accepted_absent']==json.loads(old['accepted_absent']),r['query_id']
        assert r['accepted_correct']==(old['correct_singleton']=='true')
    diag=load(a.root/'work/accounts_results/posthoc_diagnostics.json')['families']
    for family,d in diag.items():
        assert sum(r['unique_top'] for r in held if r['family']==family)==d['unique_top_score_true'],family
    full=choose_threshold(cal);frozen=config['calibration']['accounts']
    assert full['threshold']==threshold and full['correct_singletons']==frozen['correct_singletons']
    assert full['absent_false_acceptances']==frozen['false_acceptances']
    folds=[]
    for group in sorted(set(r['group_id'] for r in cal)):
        train=[r for r in cal if r['group_id']!=group];omitted=[r for r in cal if r['group_id']==group]
        fit=choose_threshold(train)
        folds.append(dict(omitted_group=group,omitted_length=omitted[0]['length'],threshold=fit['threshold'],
            threshold_minus_frozen=fit['threshold']-threshold,retained_calibration=fit,
            omitted_at_diagnostic_threshold=metrics(omitted,fit['threshold']),
            omitted_at_frozen_threshold=metrics(omitted,threshold)))
    summaries={}
    strata=[]
    for split,subset in [('calibration',cal),('held_out',held)]:
        summaries[split]=summarize(subset,threshold)
        for dimensions in [('length',),('family',),('length','family'),('group_id',)]:
            buckets=defaultdict(list)
            for r in subset:buckets[tuple(r[k] for k in dimensions)].append(r)
            for key,rr in sorted(buckets.items()):
                sm=summarize(rr,threshold);entry={'split':split,'stratum':'+'.join(dimensions),**dict(zip(dimensions,key)),**sm}
                strata.append(entry)
    # Describe the fixed linear arithmetic, not a causal ablation or a refit.
    contributions=[];buckets=defaultdict(list)
    for q in raw:
        ev=q['candidates'][q['true_reference']]
        if ev['available']:buckets[(q['split'],q['length'],q['family'])].append(ev['features'])
    for (split,length,family),features in sorted(buckets.items()):
        x=np.asarray(features);z=(x-np.asarray(config['mean']))/np.asarray(config['scale'])
        c=z*np.asarray(config['coef']);mean=c.mean(axis=0)
        for i,name in enumerate(config['feature_names']):
            contributions.append(dict(split=split,length=length,family=family,n_available=len(features),feature=name,
                mean_raw_feature=float(x[:,i].mean()),mean_logit_contribution=float(mean[i]),
                frozen_intercept=config['intercept'],mean_reconstructed_logit=float(mean.sum()+config['intercept'])))
    write_csv(a.out/'candidate_scores.csv',scores_csv)
    write_csv(a.out/'query_margins.csv',[{k:v for k,v in r.items() if k not in ('scores','accepted_present','accepted_absent')} for r in rows])
    write_csv(a.out/'feature_contributions.csv',contributions)
    write_json(a.out/'stratified_margins.json',strata)
    write_json(a.out/'calibration_sensitivity.json',dict(full_calibration_reproduced=full,folds=folds,
        warning='Diagnostics on calibration groups only. Frozen readout and deployed threshold unchanged. Each omission also removes its unique calibration length; group and length cannot be separated. No diagnostic threshold is selected using held-out outcomes.'))
    write_json(a.out/'summary.json',dict(frozen_threshold=threshold,by_split=summaries,
        verification=dict(held_out_present_and_absent_decisions_matched=576,calibration_threshold_exact=True,
            calibration_counts_matched=True,ranking_counts_by_family_matched=True,candidate_pairs=len(scores_csv),
            scalar_arithmetic_max_abs_difference=max_scalar_difference,source_hashes_match=True,export_hash_matches=True,
            metadata_and_histories_match_published_manifest=True),
        operations='Frozen linear arithmetic on saved evidence; calibration-only diagnostic threshold sweeps. No extraction, alignment, fitting, audio generation, or MERT inference.'))
    print(json.dumps(dict(summary=summaries,folds=folds),indent=2))


if __name__=='__main__': main()
