"""Evaluator-only fixed clean-event material preparation. Never import in a predictor.

No audio, candidate, model, network, or adaptive performance selection. Existing
source bytes and all historical saved event arrays are provenance inspected.
Bach structural selection is chronological. Novel motifs and foils are each
constructed once; a failed validity check ends preparation without replacement.
"""
from pathlib import Path
from collections import defaultdict
import hashlib
import importlib.util
import json
import math
import random
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
BORROWED = REPO / 'experiments/borrowed-recurrence-feasibility-v1'
BACH_SPLITS = {'development': [773, 775], 'calibration': [778, 781],
               'evaluation': [774, 776, 779, 782, 784, 785, 786, 787]}
CELLS = ['unchanged', 'transpose', 'stretch', 'foil']
SEED_BASE = 202609260800
SHIFTS = [-5, -2, 2, 5]
SCALES = [0.8, 1.25]
SLOT_SECONDS = 4.0
SOURCE_SECONDS = 3.0
INTERFERERS = 128
TIMING_TOLERANCE = 1e-9


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def canonical(events):
    if len(events) != 12:
        raise ValueError('exactly twelve events required')
    start, end, pitch = events[0][0], events[-1][1], events[0][2]
    span = end - start
    if span <= 0:
        raise ValueError('nonpositive span')
    return tuple((round((a-start)/span, 10), round((b-start)/span, 10), int(p-pitch))
                 for a, b, p in events)


def equivalent(a, b):
    """Independent full endpoint/pitch relation, not G or a candidate call."""
    if len(a) != 12 or len(b) != 12:
        return False
    sa, sb = a[-1][1]-a[0][0], b[-1][1]-b[0][0]
    if min(sa, sb) <= 0:
        return False
    shift = b[0][2]-a[0][2]
    return all(abs((x[j]-a[0][0])/sa-(y[j]-b[0][0])/sb) <= TIMING_TOLERANCE
               for x,y in zip(a,b) for j in (0,1)) and all(y[2]-x[2] == shift for x,y in zip(a,b))


def normalize(events):
    start, end = events[0][0], events[-1][1]
    factor = SOURCE_SECONDS/(end-start)
    return [[(a-start)*factor, (b-start)*factor, int(p)] for a,b,p in events]


def check_events(events):
    if len(events) != 12 or any(b <= a or p < 24 or p > 104 for a,b,p in events):
        raise ValueError('invalid event count, duration or pitch')
    if any(a[1] > b[0]+TIMING_TOLERANCE for a,b in zip(events,events[1:])):
        raise ValueError('overlapping events')


def historical_inventory():
    supports = defaultdict(set)
    source_files = []
    phrases = {}
    event_keys = {'source_events', 'query_events', 'relative_events', 'all_rendered_events',
                  'events', 'original_quarter_events'}
    def walk(v, path):
        if isinstance(v, dict):
            if 'bwv' in v and 'note_indices' in v:
                supports[int(v['bwv'])].update(v['note_indices'])
            for key, value in v.items():
                if key in event_keys and isinstance(value,list) and len(value) >= 12:
                    if all(isinstance(x,list) and len(x)>=3 and all(isinstance(y,(float,int)) for y in x[:3]) for x in value):
                        for offset in range(len(value)-11):
                            window = [x[:3] for x in value[offset:offset+12]]
                            try:
                                check_events(window)
                                sig = canonical(window)
                                phrases.setdefault(sig, {'events': window, 'path': path, 'field':key, 'window_start':offset})
                            except (ValueError,TypeError,OverflowError):
                                pass
                walk(value,path)
        elif isinstance(v,list):
            for x in v:
                if isinstance(x,(dict,list)):walk(x,path)
    for path in sorted(REPO.rglob('*.json')):
        if ROOT in path.parents or '.git' in path.parts:
            continue
        try:
            value=json.loads(path.read_text())
        except (ValueError, UnicodeError):
            continue
        walk(value,str(path.relative_to(REPO)))
        source_files.append({'path':str(path.relative_to(REPO)), 'sha256':digest(path)})
    return supports, list(phrases.values()), source_files


def matches_history(events, history):
    sig=tuple(int(events[i+1][2]-events[i][2]) for i in range(11))
    for p in history:
        old=p['events']
        if sig == tuple(int(old[i+1][2]-old[i][2]) for i in range(11)) and equivalent(events,old):
            return {k:v for k,v in p.items() if k!='events'}
    return None


def novel(seed, index):
    rng=random.Random(seed)
    degree=rng.randrange(-2,4)
    degrees=[degree]
    for _ in range(11):
        degree=max(-5,min(10,degree+rng.choice([-4,-3,-2,-1,1,2,3,4])))
        degrees.append(degree)
    scale=[0,2,4,5,7,9,11]
    t=0.0;events=[]
    for d in degrees:
        duration=rng.choice([0.5,0.75,1.0,1.5])
        events.append([t,t+duration,60+index%4+12*(d//7)+scale[d%7]])
        t+=duration
    return normalize(events)


def make_materials():
    started=time.monotonic()
    if (ROOT/'inputs/manifest.json').exists():
        raise RuntimeError('material artifact already exists; do not regenerate exposed inputs')
    supports,history,historical_files=historical_inventory()
    spec=importlib.util.spec_from_file_location('frozen_midi_reader',BORROWED/'midi_reader.py')
    parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
    acquired=json.loads((BORROWED/'sources/manifest.json').read_text())
    mids={f['bwv']:f for f in acquired['files'] if f['path'].endswith('.mid')}
    families=[];selection=[];sources=[]
    for split,works in BACH_SPLITS.items():
        for bwv in works:
            info=mids[bwv];path=BORROWED/info['path']
            if digest(path)!=info['sha256']:raise ValueError('source hash mismatch')
            parsed=parser.read_midi(path)
            track_index,track=next((i,t) for i,t in enumerate(parsed['tracks']) if t['notes'])
            if track['sustain_pedal'] or track['overlapping_note_ons']:
                raise ValueError('pedal or ambiguous repeated-note overlap')
            notes=track['notes'];rejections=[];chosen=None
            for a in range(36,len(notes)-11):
                events=[x[:3] for x in notes[a:a+12]]
                reasons=[]
                if set(range(a,a+12)) & supports[bwv]:reasons.append('historical_event_support_overlap')
                try:check_events(events)
                except ValueError as exc:reasons.append(str(exc))
                if any(x[1] > events[0][0]+TIMING_TOLERANCE for x in notes[:a]):reasons.append('earlier_note_crosses_excerpt_start')
                if a+12<len(notes) and notes[a+12][0]<events[-1][1]-TIMING_TOLERANCE:reasons.append('next_note_crosses_excerpt_end')
                match=None if reasons else matches_history(events,history)
                if match:reasons.append('historical_full_pitch_time_relation')
                if reasons:
                    rejections.append({'start_index':a,'end_index':a+11,'reasons':reasons,'historical_match':match})
                    continue
                chosen=(a,events);break
            if chosen is None:raise ValueError('finite eligible Bach material exhausted; no replacement work')
            a,raw=chosen;events=normalize(raw);family=f'bach-bwv{bwv}-notes{a}-{a+11}'
            provenance={**info,'repository_path':str(path.relative_to(REPO)), 'midi_track_index':track_index,
                        'midi_track_name':track['name'],'note_indices':list(range(a,a+12)),
                        'original_quarter_events':notes[a:a+12], 'historical_note_indices':sorted(supports[bwv]),
                        'quarter_span':[raw[0][0],raw[-1][1]],'new_split':split}
            sources.append(provenance)
            selection.append({'family_id':family,'rejected_windows':rejections,'selected_start_index':a})
            families.append({'family_id':family,'split':split,'stratum':'bach','events':events,'source_provenance':provenance})
        for i in range(len(works)):
            global_index=sum(len(x) for key,x in BACH_SPLITS.items() if list(BACH_SPLITS).index(key)<list(BACH_SPLITS).index(split))+i
            seed=SEED_BASE+global_index
            events=novel(seed,i);check_events(events)
            match=matches_history(events,history)
            if match:raise ValueError(f'once-generated novel historical collision: {seed}, {match}')
            families.append({'family_id':f'novel-{split}-{i+1:02d}','split':split,'stratum':'novel','events':events,
                             'source_provenance':{'type':'new deterministic original motif','seed':seed,'generation_attempts':1}})
    for index,f in enumerate(families):
        source=f['events'];pitches=[x[2] for x in source];rotated=pitches[7:]+pitches[:7]
        foil=[[a,b,p] for (a,b,_),p in zip(source,rotated)]
        if equivalent(source,foil) or sum(a!=b for a,b in zip(pitches,rotated))<4:
            raise ValueError(f'fixed one-pass foil is trivial: {f["family_id"]}')
        f['foil_events']=foil;f['transpose_shift']=SHIFTS[index%len(SHIFTS)];f['stretch_scale']=SCALES[index%len(SCALES)]
    for i,a in enumerate(families):
        for b in families[i+1:]:
            for ka in ('events','foil_events'):
                for kb in ('events','foil_events'):
                    if equivalent(a[ka],b[kb]):raise ValueError('full phrase relation collision between frozen families; no replacements')
    split_doc={'schema':'bounded-retention-split-v1','families':families,
               'split_counts':{s:sum(f['split']==s for f in families) for s in BACH_SPLITS},
               'bach_works':BACH_SPLITS,'freshness':'Fresh nonoverlapping excerpts, not historically unseen works; historical evaluation works remain evaluation.'}
    save(ROOT/'split.json',split_doc)
    entries=[]
    for family_number,f in enumerate(families):
        pool=[(g,k) for g in families if g['split']==f['split'] and g['family_id']!=f['family_id'] for k in ('events','foil_events')]
        occurrences=[{'events':f['events'],'support':[0.0,SOURCE_SECONDS]}]
        provenance=[]
        for i in range(INTERFERERS):
            g,key=pool[i%len(pool)];start=(i+1)*SLOT_SECONDS
            events=[[a+start,b+start,p] for a,b,p in g[key]]
            occurrences.append({'events':events,'support':[start,start+SOURCE_SECONDS]})
            provenance.append({'record_index':i+1,'family_id':g['family_id'],'variant':key,'slot_start':start})
        for cell_number,cell in enumerate(CELLS):
            shift=f['transpose_shift'] if cell=='transpose' else 0
            scale=f['stretch_scale'] if cell=='stretch' else 1.0
            start=(INTERFERERS+1)*SLOT_SECONDS
            basis=f['foil_events'] if cell=='foil' else f['events']
            query_events=[[start+a*scale,start+b*scale,p+shift] for a,b,p in basis]
            check_events(query_events)
            session_id=f's{family_number:02d}-{cell_number}'
            observation={'schema':'bounded-retention-observations-v1','session_id':session_id,
                         'occurrences':occurrences,'query':{'events':query_events,'support':[start,start+SOURCE_SECONDS*scale]}}
            labels={'schema':'bounded-retention-labels-v1','session_id':session_id,'family_id':f['family_id'],
                    'split':f['split'],'stratum':f['stratum'],'cell':cell,'positive':cell!='foil',
                    'source_support':[0.0,SOURCE_SECONDS],'query_support':[start,start+SOURCE_SECONDS*scale],
                    'expected_shift':shift if cell!='foil' else None,'expected_scale':scale if cell!='foil' else None,
                    'source_record_index':0,'interference_occurrences':INTERFERERS,'interference_provenance':provenance,
                    'query_final_event_offset':start+SOURCE_SECONDS*scale,
                    'decision_available_at':math.ceil(start+SOURCE_SECONDS*scale),
                    'identity_definition':'Independent construction correspondence; not perceptual identity',
                    'source_dependent_record_indices':[0]}
            folder=ROOT/'inputs'/f['split']/session_id
            save(folder/'observations.json',observation);save(folder/'labels.json',labels)
            entries.append({'session_id':session_id,'family_id':f['family_id'],'split':f['split'],'stratum':f['stratum'],'cell':cell,
                            'path':str(folder.relative_to(ROOT)),
                            'observations':str((folder/'observations.json').relative_to(ROOT)),
                            'labels':str((folder/'labels.json').relative_to(ROOT)),
                            'observations_sha256':digest(folder/'observations.json'),'labels_sha256':digest(folder/'labels.json')})
    save(ROOT/'inputs/manifest.json',{'schema':'bounded-retention-input-manifest-v1','sessions':entries,
         'unique_material_streams':len(entries),'candidate_readouts_run':0,'source_removal_reuses_positive_observations':True})
    save(ROOT/'input-manifest.json',{'schema':'bounded-retention-input-manifest-v1',
         'sessions':[{k:e[k] for k in ('session_id','path','split','family_id','stratum','cell','observations_sha256','labels_sha256')} for e in entries],
         'unique_material_streams':len(entries),'candidate_readouts_run':0})
    provenance={'schema':'bounded-retention-material-provenance-v1','historical_json_inventory':historical_files,
                'historical_unique_12event_phrases_checked':len(history),'historical_bach_supports':{str(k):sorted(v) for k,v in supports.items()},
                'source_manifest_sha256':digest(BORROWED/'sources/manifest.json'),'midi_parser_sha256':digest(BORROWED/'midi_reader.py'),
                'sources':sources,'selection':selection,'material_preparation_seconds':time.monotonic()-started,
                'selection_rule':'Chronological first eligible 12-event window with start>=36, no prior source-event overlap, no overlapping notes or boundary-crossing notes, no historical full normalized pitch/timing equivalent; no matcher outcomes consulted.',
                'novel_rule':'One Python Random fixed seed per family, bounded diatonic walk, fixed duration choices; abort collision, never regenerate.',
                'foil_rule':'Rotate pitch sequence left by7, keep timing and pitch inventory; reject trivial result without replacement.',
                'interference_rule':'Exactly128 occurrences cycling other same-split families in split manifest order, source then foil variant; no target-family interferers, no adaptive length.',
                'arrival_rule':'Immutable complete occurrence and query become available at the end of the one-second broker unit containing the final note: ceil(final event offset). Actual event support remains separate. Slots4s; source/query duration3s before transform. This is clean evaluator-supplied segmented evidence.',
                'novel_seed_base':SEED_BASE,'slot_seconds':SLOT_SECONDS,'source_seconds':SOURCE_SECONDS,
                'interferers':INTERFERERS,'query_start_seconds':(INTERFERERS+1)*SLOT_SECONDS,
                'material_streams_constructed':len(entries),'candidate_readouts_run':0,
                'audio_operations':0,'network_operations':0,'historical_files_modified':False,
                'split_sha256':digest(ROOT/'split.json'),'input_manifest_sha256':digest(ROOT/'input-manifest.json'),
                'detailed_input_manifest_sha256':digest(ROOT/'inputs/manifest.json')}
    save(ROOT/'material-provenance.json',provenance)
    print(json.dumps({'families':len(families),'streams':len(entries),'seconds':time.monotonic()-started,'historical_phrases':len(history)}))


if __name__=='__main__':
    make_materials()
