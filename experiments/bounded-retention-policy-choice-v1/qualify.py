"""Fifteen predeclared tiny nonmusical streamed fixture readouts."""
import json
from pathlib import Path
from run import ROOT,POLICIES,execute,save
PITCH=[60,64,67,61,69,63,70,65,72,66,73,68]
def rec(start,pitches=PITCH,scale=1,shift=0):
 return {'events':[[start+i*.25*scale,start+(i+1)*.25*scale,p+shift] for i,p in enumerate(pitches)],'support':[start,start+3*scale]}
def main():
 summary=[]
 for case in ['transformed','removed','ambiguous']:
  occurrences=[rec(0),rec(4,[25+i%3 for i in range(12)]),rec(8,PITCH if case=='ambiguous' else [35+i%4 for i in range(12)])]
  obs={'occurrences':occurrences,'query':rec(16,scale=1.25,shift=2)}
  save(ROOT/'qualification'/case/'observations.json',obs)
  for policy in POLICIES:
   dest=ROOT/'qualification'/case/policy
   execute(obs,dest,policy,case=='removed')
   r=json.loads((dest/'response.json').read_text());raw=r['raw']
   expected=case=='transformed' and policy!='present'
   checks={'acceptance':raw['accepted']==expected,'recent_eviction':min(r['recent_units'])>=16,'capacity':len(r['retained_records'])<=(512 if policy=='unpressured' else 8),'availability':r['simulation_observations_available_at']==20}
   if expected:checks.update(shift=raw['selected']['shift']==2,scale=abs(raw['selected']['scale']-1.25)<1e-8,source=0<=raw['selected']['center']<3)
   if case=='removed':checks['removed']=not any(x['id']==1 for x in r['retained_records'])
   if case=='ambiguous' and policy!='present':checks['all_alternatives']=raw['candidate_count']==2
   summary.append({'case':case,'policy':policy,'checks':checks,'passed':all(checks.values())})
   save(ROOT/'qualification.json',{'planned':15,'completed':len(summary),'passed':all(x['passed'] for x in summary),'rows':summary})
   if not all(checks.values()):raise RuntimeError('Qualification failed: '+str(summary[-1]))
 print(json.dumps({'completed':15,'passed':True}))
if __name__=='__main__':main()
