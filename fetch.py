# Runs on a GitHub runner: finds each painting's canonical image via Wikidata (P18), falls back to Commons search,
# downloads a <=6000px rendition, records the source file and licence.
import json,re,requests,os,time
S=requests.Session(); S.headers['User-Agent']='GHOST-art-fetch/1.0 (personal archive)'
os.makedirs('orig',exist_ok=True); log=[]
def clean(t): return re.sub(r'\(.*?\)','',t).replace('detail','').strip()
def wd_image(title,artist):
    q=f'{clean(title)} {"" if "confirm" in artist else artist.split(",")[0]}'
    r=S.get('https://www.wikidata.org/w/api.php',params=dict(action='wbsearchentities',search=clean(title),language='en',limit=8,format='json')).json()
    for e in r.get('search',[]):
        ent=S.get(f'https://www.wikidata.org/wiki/Special:EntityData/{e["id"]}.json').json()['entities'][e['id']]
        cl=ent.get('claims',{})
        if 'P18' not in cl: continue
        desc=(e.get('description') or '').lower()
        if 'painting' in desc or 'fresco' in desc or 'tapestry' in desc or 'work' in desc:
            if 'confirm' in artist or artist.split()[-1].lower() in desc or artist.split(',')[0].split()[-1].lower() in desc:
                return cl['P18'][0]['mainsnak']['datavalue']['value'],e['id']
    return None,None
def commons_search(title,artist):
    q=f'{clean(title)} {"" if "confirm" in artist else artist}'
    r=S.get('https://commons.wikimedia.org/w/api.php',params=dict(action='query',list='search',srsearch=q,srnamespace=6,srlimit=5,format='json')).json()
    hits=[h['title'][5:] for h in r['query']['search'] if h['title'].lower().endswith(('.jpg','.jpeg','.png','.tif','.tiff'))]
    return hits[0] if hits else None
for it in json.load(open('paintings.json')):
    f,qid=wd_image(it['title'],it['artist']); how='wikidata'
    if not f: f=commons_search(it['title'],it['artist']); how='commons-search'
    if not f: log.append(dict(id=it['id'],status='not found')); continue
    info=S.get('https://commons.wikimedia.org/w/api.php',params=dict(action='query',titles='File:'+f,prop='imageinfo',iiprop='url|size|extmetadata',iiurlwidth=6000,format='json')).json()
    ii=list(info['query']['pages'].values())[0]['imageinfo'][0]
    url=ii.get('thumburl') if ii['width']>6000 else ii['url']
    ext=os.path.splitext(url)[1].lower()
    if ext in ('.tif','.tiff'): url=ii.get('thumburl',url); ext='.jpg'
    data=S.get(url).content
    open(f'orig/{it["id"]:03d}{ext}','wb').write(data)
    lic=ii.get('extmetadata',{}).get('LicenseShortName',{}).get('value','')
    log.append(dict(id=it['id'],status='ok',how=how,file=f,qid=qid,size=f'{ii["width"]}x{ii["height"]}',license=lic,bytes=len(data)))
    print(it['id'],how,f,ii['width'],ii['height'],flush=True); time.sleep(0.5)
json.dump(log,open('orig/log.json','w'),indent=1,ensure_ascii=False)
