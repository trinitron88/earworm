import json,urllib.request,hashlib,datetime,re,time
from pathlib import Path
p=Path('/private/tmp/earworm-borrowed-recurrence-20260922/experiments/borrowed-recurrence-feasibility-v1');(p/'sources').mkdir(exist_ok=True);(p/'provenance').mkdir(exist_ok=True)
rows=[(773,2,58),(774,3,70),(775,4,67),(776,5,55),(778,7,73),(779,8,61),(781,10,62),(782,11,71),(784,13,59),(785,14,72),(786,15,68),(787,0,142)]
dev={773,775,778,781};plan=[{'bwv':b,'split':'development' if b in dev else 'evaluation','mutopia_id':i,'stem':f'bach-invention-{n:02}' if n else 'bwv787','voice_policy':'first nonempty MIDI note track; isolated voice; first 12 nonoverlapping note events; reject chords instead of silently selecting'} for b,n,i in rows]
(p/'sources/acquisition_plan.json').write_text(json.dumps({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'piece_split_fixed_before_download':True,'pieces':plan,'evaluation_policy':'preserve bytes; do not parse evaluation notes or render evaluation audio before preregistration'},indent=2)+'\n')
manifest=[];total=0;start=time.perf_counter()
def fetch(url,cap):
 with urllib.request.urlopen(url,timeout=30) as r:
  data=r.read(cap+1);assert len(data)<=cap
 return data
legal='https://www.mutopiaproject.org/legal.html';(p/'provenance/mutopia-legal.html').write_bytes(fetch(legal,2000000))
for row in plan:
 page=f"https://www.mutopiaproject.org/cgibin/piece-info.cgi?id={row['mutopia_id']}";html=fetch(page,2000000);text=re.sub('<[^>]+>',' ',html.decode());assert 'Public Domain' in text
 (p/f"provenance/mutopia-{row['mutopia_id']}.html").write_bytes(html)
 for ext in ['mid','ly']:
  url=f"https://www.mutopiaproject.org/ftp/BachJS/BWV{row['bwv']}/{row['stem']}/{row['stem']}.{ext}"
  data=fetch(url,1000000);total+=len(data);assert total<=25*1024**2
  name=f"sources/BWV{row['bwv']}.{ext}";(p/name).write_bytes(data)
  manifest.append({**row,'path':name,'url':url,'source':'Mutopia Project','work_title':f"{'Invention' if row['bwv']<787 else 'Sinfonia'} BWV {row['bwv']}",'rights_assertion':'Copyright: Public Domain','rights_page':page,'rights_terms_url':legal,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(p/'sources/manifest.json').write_text(json.dumps({'files':manifest,'total_source_bytes':total,'acquisition_seconds':time.perf_counter()-start,'source_license_pages_saved':True},indent=2)+'\n');print(total,len(manifest))
