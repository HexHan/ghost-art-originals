# Finds the largest Wikimedia Commons photo for each query and downloads it full size (no cap).
import json,requests,os,time
S=requests.Session(); S.headers['User-Agent']='GHOSTArtFetch/1.0 (https://github.com/HexHan/ghost-art-originals; personal archive) python-requests'
os.makedirs('big',exist_ok=True); log=[]
for job in json.load(open('big_jobs.json')):
    r=S.get('https://commons.wikimedia.org/w/api.php',params=dict(action='query',generator='search',gsrsearch=job['q'],gsrnamespace=6,gsrlimit=30,prop='imageinfo',iiprop='url|size|mime',format='json')).json()
    cands=[]
    for p in r.get('query',{}).get('pages',{}).values():
        ii=(p.get('imageinfo') or [{}])[0]
        if ii.get('mime') in ('image/jpeg','image/png','image/tiff'):
            cands.append((ii['width']*ii['height'],p['title'],ii))
    cands.sort(reverse=True)
    log.append(dict(id=job['id'],cands=[(c[1],c[2]['width'],c[2]['height']) for c in cands[:8]]))
    if job.get('must'): cands=[c for c in cands if all(w.lower() in c[1].lower() for w in job['must'])]
    for area,title,ii in cands[:job.get('n',3)]:
        url=ii['url']
        if ii['mime']=='image/tiff' or ii['width']>12000:
            q=S.get('https://commons.wikimedia.org/w/api.php',params=dict(action='query',titles=title,prop='imageinfo',iiprop='url',iiurlwidth=min(ii['width'],12000),format='json')).json()
            url=list(q['query']['pages'].values())[0]['imageinfo'][0]['thumburl']
        if job.get('w') and ii['width']>job['w']:
            q=S.get('https://commons.wikimedia.org/w/api.php',params=dict(action='query',titles=title,prop='imageinfo',iiprop='url',iiurlwidth=job['w'],format='json')).json()
            url=list(q['query']['pages'].values())[0]['imageinfo'][0]['thumburl']
        for tr in range(6):
            rr=S.get(url,timeout=300); data=rr.content
            if rr.ok and not data[:200].lstrip().lower().startswith((b'<!doctype',b'<html')): break
            time.sleep(10*(tr+1))
        else: continue
        time.sleep(3)
        k=len([f for f in os.listdir('big') if f.startswith(f"{job['id']:03d}_")])
        open(f"big/{job['id']:03d}_{k}.jpg",'wb').write(data)
json.dump(log,open('big/log.json','w'),indent=1,ensure_ascii=False)
