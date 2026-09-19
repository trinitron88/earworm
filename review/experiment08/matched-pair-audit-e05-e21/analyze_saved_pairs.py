"""Post-hoc arithmetic on four saved queries. No pipeline imports, search, or fitting."""
import argparse,csv,hashlib,json,math
from pathlib import Path
import numpy as np

PREVIOUS='review/experiment08/calibration-audit/completion-20260919'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def csvwrite(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def support(e,c):
    if not e['available']:return -1e6
    return float(np.dot((np.asarray(e['features'])-c['mean'])/c['scale'],c['coef'])+c['intercept'])
def arrays(d):return {k:np.asarray(v['values'],dtype=v['dtype']) for k,v in d.items()}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--input',type=Path,default=Path(__file__).resolve().parent);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists() and any(a.out.iterdir()):raise ValueError('Use a new empty output directory')
    a.out.mkdir(parents=True,exist_ok=True)
    ids=load(a.input/'input_identifiers.json');data=load(a.input/'saved_inputs.json');c=load(a.root/'work/accounts_results/frozen_config.json')
    assert sha(a.input/'saved_inputs.json')==ids['selected_export']['sha256']
    for name,h in ids['frozen_source_sha256'].items():assert sha(a.root/'work'/name)==h
    for rel in ['work/accounts_results/frozen_config.json','work/accounts_results/protocol.json']:
        assert sha(a.root/rel)==next(i['sha256'] for i in ids['original_inputs'] if i['path']==rel)
    compact=a.root/ids['prior_compact_export']['path'];assert sha(compact)==ids['prior_compact_export']['sha256']
    old={q['query_id']:q for q in map(json.loads,compact.read_text().splitlines())}
    with (a.root/PREVIOUS/'results/query_margins.csv').open() as f:prior={r['query_id']:r for r in csv.DictReader(f)}
    desc={k:arrays(v) for k,v in data['descriptions'].items()}
    score_rows=[];feature_rows=[];correspondences=[];paths=[];energy=[];events=[];details=[]
    max_residual_error=0.;max_loss_error=0.;max_gap_error=0.;max_scalar_error=0.
    for bid,d in sorted(desc.items()):
        for i,(on,off,pitch) in enumerate(zip(d['event_onset_s'],d['event_offset_s'],d['event_pitch_semitones'])):
            raw=dict(block_id=bid,event_index_zero_based=i,onset_s=float(on),offset_s=float(off),pitch_semitones=float(pitch),
                pitch_span_cents=float(d['event_pitch_span_cents'][i]),phase_fraction=float(d['event_phase_fraction'][i]),bend_peak_cents=float(d['event_bend_peak_cents'][i]))
            if 'frame_rms' in d:
                mask=(d['frame_time_s']>=on)&(d['frame_time_s']<=off)
                raw.update(rms_frame_count=int(mask.sum()),rms_mean=float(d['frame_rms'][mask].mean()) if mask.any() else None,rms_max=float(d['frame_rms'][mask].max()) if mask.any() else None)
            else:raw.update(rms_frame_count=None,rms_mean=None,rms_max=None)
            events.append(raw)
    for item in data['queries']:
        q=item['query'];qid=q['query_id'];assert q==old[qid];qd=desc[qid];true=q['true_reference'];threshold=c['threshold']
        scores={rid:support(e,c) for rid,e in q['candidates'].items()}
        am=max(scores[rid] for rid in q['absent_history']);distractors=[r for r in q['present_history'] if r!=true];dm=max(scores[r] for r in distractors)
        selection=dict(absent_exact_maxima=[r for r in q['absent_history'] if scores[r]==am],absent_within_1e_9_of_max=[r for r in q['absent_history'] if abs(scores[r]-am)<1e-9],
            present_distractor_exact_maxima=[r for r in distractors if scores[r]==dm],present_distractor_within_1e_9_of_max=[r for r in distractors if abs(scores[r]-dm)<1e-9])
        assert selection==item['selection']
        pos=[r for r in q['present_history'] if scores[r]>=threshold];neg=[r for r in q['absent_history'] if scores[r]>=threshold]
        sr=dict(query_id=qid,split=q['split'],true_reference=true,true_score=scores[true],true_margin=scores[true]-threshold,
            absent_max_ids='|'.join(selection['absent_exact_maxima']),absent_max_score=am,absent_margin=am-threshold,true_minus_absent_max=scores[true]-am,
            present_distractor_max_ids='|'.join(selection['present_distractor_exact_maxima']),present_distractor_max_score=dm,
            absent_and_present_impostor_same=selection['absent_exact_maxima']==selection['present_distractor_exact_maxima'],
            true_impostor_gap_within_prior_1e_9_ranking_tolerance=abs(scores[true]-am)<1e-9,
            accepted_present='|'.join(pos),accepted_absent='|'.join(neg),correct_singleton=pos==[true])
        for key in ['true_score','true_margin','absent_max_score','absent_margin','true_minus_absent_max']:
            assert sr[key]==float(prior[qid][key]),(qid,key)
        score_rows.append(sr)
        comparators=sorted(set(selection['absent_within_1e_9_of_max']+selection['present_distractor_within_1e_9_of_max']))
        comparison_summaries=[]
        for rid in comparators:
            te=q['candidates'][true];ie=q['candidates'][rid];assert te['available'] and ie['available']
            delta=(np.asarray(te['features'])-np.asarray(ie['features']))/np.asarray(c['scale'])*np.asarray(c['coef'])
            direct_gap=scores[true]-scores[rid];summed=math.fsum(map(float,delta));error=abs(summed-direct_gap);max_gap_error=max(max_gap_error,error)
            assert error<1e-12
            changed=[]
            for k,name in enumerate(c['feature_names']):
                difference=te['features'][k]-ie['features'][k]
                if difference!=0:changed.append(name)
                feature_rows.append(dict(query_id=qid,impostor_id=rid,feature=name,true_value=te['features'][k],impostor_value=ie['features'][k],raw_difference=difference,
                    frozen_scale=c['scale'][k],frozen_coefficient=c['coef'][k],coefficient_per_raw_unit=c['coef'][k]/c['scale'][k],additive_gap_contribution=float(delta[k])))
            comparison_summaries.append(dict(impostor_id=rid,direct_score_gap=direct_gap,sum_feature_gap_contributions=summed,absolute_roundoff_discrepancy=error,nonzero_feature_differences=changed))
        for rid,e in item['saved_candidate_evidence'].items():
            assert all(e[k]==v for k,v in q['candidates'][rid].items())
            rd=desc[rid]
            scalar=math.fsum((v-m)/s*w for v,m,s,w in zip(e['features'],c['mean'],c['scale'],c['coef']))+c['intercept']
            max_scalar_error=max(max_scalar_error,abs(scalar-scores[rid]))
            for pi,path in enumerate(e['paths']):
                aa,bb=np.array(path['matched_pairs'],dtype=int).T
                rp=rd['event_pitch_semitones'].astype(float)[aa];qp=qd['event_pitch_semitones'].astype(float)[bb]
                rt=rd['event_onset_s'].astype(float)[aa];qt=qd['event_onset_s'].astype(float)[bb]
                pitch=qp-rp-path['global_pitch_shift'];timing=qt-path['timing_scale']*rt-path['timing_offset_s']
                err=max(float(np.max(np.abs(pitch-path['pitch_residual_semitones']))),float(np.max(np.abs(timing-path['timing_residual_s']))));max_residual_error=max(max_residual_error,err);assert err<1e-12
                pl=np.maximum(np.abs(pitch)-.05,0)/2;tl=np.maximum(np.abs(timing)-.005,0)*2
                cost=float((pl.sum()+tl.sum()+.7*(len(path['missing_reference'])+len(path['inserted_query'])))/max(e['reference_events'],e['query_events']))
                loss_error=max(abs(float(pl.mean())-path['mean_pitch_loss']),abs(float(tl.mean())-path['mean_timing_loss']),abs(cost-path['cost']))
                max_loss_error=max(max_loss_error,loss_error);assert loss_error<1e-12
                paths.append(dict(query_id=qid,candidate_id=rid,path_index=pi,used_for_support=pi==0,role='true' if rid==true else 'impostor',
                    saved_correspondences=json.dumps(path['matched_pairs']),missing_reference_indices=json.dumps(path['missing_reference']),inserted_query_indices=json.dumps(path['inserted_query']),
                    pitch_shift=path['global_pitch_shift'],timing_scale=path['timing_scale'],timing_offset_s=path['timing_offset_s'],cost=path['cost'],mean_pitch_loss=path['mean_pitch_loss'],mean_timing_loss=path['mean_timing_loss'],exact_pitch_fraction=path['exact_pitch_fraction']))
                for j,(ai,bi) in enumerate(path['matched_pairs']):
                    correspondences.append(dict(query_id=qid,candidate_id=rid,path_index=pi,used_for_support=pi==0,reference_event=ai,query_event=bi,
                        reference_pitch_semitones=float(rp[j]),query_pitch_semitones=float(qp[j]),pitch_residual_semitones=path['pitch_residual_semitones'][j],
                        pitch_loss=float(pl[j]),reference_onset_s=float(rt[j]),query_onset_s=float(qt[j]),saved_onset_change_s=path['onset_change_s'][j],
                        timing_residual_s=path['timing_residual_s'][j],timing_loss=float(tl[j])))
                # Apply only the frozen observation rule to SAVED RMS frames at saved fitted positions.
                floor=max(1e-5,float(qd['frame_rms'].max())*.01)
                for mi in path['missing_reference']:
                    on=float(rd['event_onset_s'][mi])*path['timing_scale']+path['timing_offset_s'];off=float(rd['event_offset_s'][mi])*path['timing_scale']+path['timing_offset_s']
                    mask=(qd['frame_time_s']>=on+.020)&(qd['frame_time_s']<=off-.020)
                    maximum=float(qd['frame_rms'][mask].max()) if mask.any() else None
                    quiet=maximum is not None and maximum<=floor
                    energy.append(dict(query_id=qid,candidate_id=rid,path_index=pi,used_for_support=pi==0,missing_reference_event=mi,
                        hypothesized_onset_s=on,hypothesized_offset_s=off,measured_window_start_s=on+.020,measured_window_end_s=off-.020,
                        saved_frame_count=int(mask.sum()),measured_max_rms=maximum,quiet_threshold_rms=floor,
                        observation='quiet_at_predicted_location' if quiet else 'unresolved_observation',physical_cause='not_identified',direct_energy_feature_in_support=False))
                if pi==0:
                    rebuilt=[cost,float(np.log1p(len(aa))),len(aa)/e['reference_events'],len(aa)/e['query_events'],float(pl.mean()),float(np.mean(np.abs(pitch)<=.2)),float(tl.mean()),
                        len(path['missing_reference'])/e['reference_events'],len(path['inserted_query'])/e['query_events'],1-e['query_events']/len(qd['event_onset_s']),
                        float(np.log1p(e['reference_events'])),float(np.log1p(e['query_events']))]
                    assert np.max(np.abs(np.asarray(rebuilt)-e['features']))<1e-12
        details.append(dict(**sr,selection=selection,feature_gap_comparisons=comparison_summaries))
    assert max_scalar_error<1e-12
    csvwrite(a.out/'scores_and_margins.csv',score_rows);csvwrite(a.out/'feature_gap_contributions.csv',feature_rows)
    csvwrite(a.out/'saved_correspondences.csv',correspondences);csvwrite(a.out/'saved_path_summary.csv',paths)
    csvwrite(a.out/'measured_events.csv',events);csvwrite(a.out/'missing_position_energy.csv',energy)
    write(a.out/'summary.json',dict(queries=details,frozen_threshold=c['threshold'],
        interpretation='Four selected post-hoc cases. Exact equality defines maximum ties; a separate 1e-9 list matches the prior ranking tolerance. Operational acceptance remains exact >= threshold.',
        energy_rule='Apply the original expected-position RMS rule to saved query frames; locations are alignment hypotheses, energy is measured, physical cause remains unidentified. No energy feature directly enters the frozen support vector.'))
    write(a.out/'verification.json',dict(prior_query_scores_and_margins_exactly_reconciled=4,query_metadata_and_histories_exact=True,
        selected_evidence_features_equal_compact_export=True,all_maxima_and_near_ties_reconciled=True,
        saved_residuals_max_abs_reconstruction_error=max_residual_error,saved_losses_max_abs_reconstruction_error=max_loss_error,
        feature_gap_sum_max_abs_roundoff_difference=max_gap_error,scalar_support_max_abs_difference=max_scalar_error,
        floating_point_check_tolerance=1e-12,operational_threshold_unchanged=True,original_pipeline_executed=False))
    print(json.dumps(dict(scores=score_rows,comparison_summaries={d['query_id']:d['feature_gap_comparisons'] for d in details},energy_best=[r for r in energy if r['used_for_support']]),indent=2))

if __name__=='__main__':main()
