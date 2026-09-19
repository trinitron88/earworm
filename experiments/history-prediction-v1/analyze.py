"""Saved forecasts only: group-weighted scores, bootstrap and frozen decision rule."""
import argparse,csv,json,math
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
NAMES=['present','recency','transition','retrieval_absolute','retrieval_transposed','relational']

def write_csv(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def main(split):
    out=HERE/'results'/split;out.mkdir(parents=True,exist_ok=True)
    truth={x['episode']:x for x in map(json.loads,(HERE/'data'/split/'truth.jsonl').read_text().splitlines())}
    cache=[json.loads(x) for x in (HERE/'data'/split/'arrived_cache.jsonl').read_text().splitlines()]
    trials=[];forecast={c['episode']:c['forecast']['forecasts'] for c in cache}
    for c in cache:
        t=truth[c['episode']];y=np.zeros(50)
        for v,m in zip(t['outcome_intervals'],t['outcome_probabilities']):y[int(round(v))+24]+=m
        for name,f in c['forecast']['forecasts'].items():
            p=np.array(f['probabilities']);mode=int(np.argmax(p));correct=f['point_pitch_semitones'] is not None and abs(f['point_pitch_semitones']-t['pitch_semitones'])<=.35
            trials.append({'episode':c['episode'],'group_id':t['group_id'],'family':t['family'],'condition':t['condition'],'variant':t['variant'],'model':name,
                'accuracy':float(correct),'log_loss':float(-sum(y*np.log(p))),'brier':float(sum((p-y)**2)),
                'confidence':float(max(p)),'expected_argmax_accuracy':float(y[mode]),'entropy_nats':float(-sum(p*np.log(p))),
                'ambiguous_support_mass':float(sum(p[y>0])) if t['condition']=='ambiguous' else None,
                'ambiguous_max_probability_error':float(max(abs(p[y>0]-.5))) if t['condition']=='ambiguous' else None})
    groups=sorted({r['group_id'] for r in trials});group_rows=[]
    for g in groups:
        for family in ['basic','transfer']:
            for condition in ['intact','reset','removal','swap','shuffle','ambiguous']:
                for name in NAMES:
                    rr=[r for r in trials if (r['group_id'],r['family'],r['condition'],r['model'])==(g,family,condition,name)];assert len(rr)==2
                    group_rows.append({'group_id':g,'family':family,'condition':condition,'model':name,**{m:float(np.mean([r[m] for r in rr])) for m in ['accuracy','log_loss','brier','confidence','entropy_nats']},'paired_success':float(all(r['accuracy'] for r in rr))})
    rng=np.random.default_rng(2026091907);indices=rng.integers(0,len(groups),size=(5000,len(groups)))
    def values(name,family,condition,metric):return np.array([next(r[metric] for r in group_rows if (r['group_id'],r['family'],r['condition'],r['model'])==(g,family,condition,name)) for g in groups])
    def ci(v):return np.quantile(v[indices].mean(axis=1),[.025,.975]).tolist()
    comparisons=[]
    for family in ['basic','transfer']:
        for name in NAMES[:-1]:
            for metric in ['accuracy','paired_success','log_loss','brier']:
                v=values('relational',family,'intact',metric)-values(name,family,'intact',metric)
                comparisons.append({'family':family,'baseline':name,'metric':'relational_minus_baseline_'+metric,'mean_difference':float(v.mean()),'ci95_low':ci(v)[0],'ci95_high':ci(v)[1]})
    aggregates=[]
    for family in ['basic','transfer']:
        for condition in ['intact','reset','removal','swap','shuffle','ambiguous']:
            for name in NAMES:
                aggregates.append({'family':family,'condition':condition,'model':name,**{m:float(values(name,family,condition,m).mean()) for m in ['accuracy','paired_success','log_loss','brier','confidence','entropy_nats']}})
    controls={};qualifies={}
    for name in NAMES:
        family_controls={}
        for family in ['basic','transfer']:
            tv={};swap_error=0.
            for condition in ['reset','removal']:
                tv[condition]=max(.5*sum(abs(np.array(forecast[f'{g}/{family}/{condition}/0'][name]['probabilities'])-np.array(forecast[f'{g}/{family}/{condition}/1'][name]['probabilities']))) for g in groups)
            for g in groups:
                for v in [0,1]:swap_error=max(swap_error,float(max(abs(np.array(forecast[f'{g}/{family}/swap/{v}'][name]['probabilities'])-np.array(forecast[f'{g}/{family}/intact/{1-v}'][name]['probabilities'])))))
            amb=[r for r in trials if r['model']==name and r['family']==family and r['condition']=='ambiguous']
            control_ok=all(values(name,family,c,'accuracy').mean()<=.55 and values(name,family,c,'paired_success').mean()<=.10 and tv[c]<=1e-9 for c in ['reset','removal'])
            swap_ok=swap_error<=1e-9 and values(name,family,'swap','paired_success').mean()>=.8
            shuffle_ok=values(name,family,'shuffle','accuracy').mean()>=values(name,family,'intact','accuracy').mean()-.10
            ambiguity_ok=all(r['ambiguous_support_mass']>=.90 and r['ambiguous_max_probability_error']<=.10 and r['confidence']<=.60 for r in amb)
            family_controls[family]={'reset_removal_pass':bool(control_ok),'reset_removal_total_variation':tv,'swap_pass':bool(swap_ok),'swap_max_probability_difference':swap_error,'shuffle_preserved_information_pass':bool(shuffle_ok),'ambiguity_pass':bool(ambiguity_ok),'ambiguous_min_support_mass':min(r['ambiguous_support_mass'] for r in amb),'ambiguous_max_probability_error':max(r['ambiguous_max_probability_error'] for r in amb)}
        controls[name]=family_controls
        basic_diff=values(name,'basic','intact','accuracy')-values('present','basic','intact','accuracy')
        basic=values(name,'basic','intact','paired_success').mean()>=.80 and ci(basic_diff)[0]>0 and all(family_controls['basic'][k] for k in ['reset_removal_pass','swap_pass','shuffle_preserved_information_pass','ambiguity_pass'])
        transfer=values(name,'transfer','intact','paired_success').mean()>=.70 and family_controls['transfer']['ambiguity_pass']
        qualifies[name]={'basic_pass':bool(basic),'transfer_pass':bool(transfer),'basic_accuracy_advantage_vs_present_ci95':ci(basic_diff)}
    simpler=NAMES[:-1]
    strongest=min(simpler,key=lambda name:(-values(name,'transfer','intact','accuracy').mean(),values(name,'transfer','intact','log_loss').mean(),simpler.index(name)))
    delta=values('relational','transfer','intact','accuracy')-values(strongest,'transfer','intact','accuracy');dc=ci(delta)
    proper_difference=float((values('relational','transfer','intact','log_loss')-values(strongest,'transfer','intact','log_loss')).mean())
    brier_difference=float((values('relational','transfer','intact','brier')-values(strongest,'transfer','intact','brier')).mean())
    equivalent=dc[0]>=-.05 and dc[1]<=.05 and abs(proper_difference)<=.05 and abs(brier_difference)<=.02
    a=qualifies['relational']['basic_pass'] and qualifies['relational']['transfer_pass'] and delta.mean()>=.10 and dc[0]>0 and proper_difference<=0 and brier_difference<=0
    better=dc[1]<0 and delta.mean()<=-.10 and proper_difference>=0 and brier_difference>=0
    b=qualifies[strongest]['basic_pass'] and (equivalent or better)
    validity_path=HERE/'validation'/f'{split}.json'
    validity=json.loads(validity_path.read_text()) if validity_path.exists() else {'status':'not_yet_verified'}
    if validity['status']!='pass':branch='C' if validity.get('localized_failure') else 'inconclusive'
    elif a:branch='A'
    elif b:branch='B'
    else:branch='inconclusive'
    action={'A':'Retain the tested relational predictor as preferred prototype; no follow-on execution authorized.',
            'B':f"Retain {strongest} as the prediction reference for {'basic and transposed anticipation' if qualifies[strongest]['transfer_pass'] else 'basic anticipation only'}; no claim beyond retrieval/transition prediction.",
            'C':'Withhold affected capability claim; preserve the localized prerequisite failure for one proposed repair requiring new authorization.',
            'inconclusive':'Preserve results; make no unsupported architectural selection and stop.'}[branch]
    decision={'authoritative_heldout_decision':split=='heldout','branch':branch,'action':action,'validity':validity['status'],'strongest_simpler_baseline':strongest,'relational_minus_strongest_transfer_accuracy':float(delta.mean()),'paired_group_bootstrap_ci95':dc,'equivalence_margin':.05,'equivalence_established':bool(equivalent),'relational_minus_strongest_log_loss':proper_difference,'relational_minus_strongest_brier':brier_difference,'capabilities':qualifies,'groups':len(groups),'bootstrap_resamples':5000,'bootstrap_seed':2026091907,'posthoc_tuning':False}
    calibration=[]
    for name in NAMES:
        for family in ['basic','transfer']:
            rr=[r for r in trials if r['model']==name and r['family']==family and r['condition']=='ambiguous']
            calibration.append({'model':name,'family':family,'mean_confidence':float(np.mean([r['confidence'] for r in rr])),'mean_expected_argmax_accuracy':float(np.mean([r['expected_argmax_accuracy'] for r in rr])),'mean_log_loss':float(np.mean([r['log_loss'] for r in rr])),'mean_brier':float(np.mean([r['brier'] for r in rr])),'max_probability_error':max(r['ambiguous_max_probability_error'] for r in rr)})
    for name,rows in [('trials.csv',trials),('groups.csv',group_rows),('summary.csv',aggregates),('paired_comparisons.csv',comparisons),('ambiguity_calibration.csv',calibration)]:write_csv(out/name,rows)
    (out/'controls.json').write_text(json.dumps(controls,indent=2)+'\n');(out/'decision.json').write_text(json.dumps(decision,indent=2)+'\n')
    print(json.dumps(decision,indent=2))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('split',choices=['development','calibration','heldout']);main(a.parse_args().split)
