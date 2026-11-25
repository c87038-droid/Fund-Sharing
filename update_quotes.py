import csv, io, json, pathlib, urllib.request, urllib.parse, datetime, re, unicodedata, math
from collections import defaultdict
ROOT=pathlib.Path(__file__).parent/'data'
SIT='https://www.sitca.org.tw/MemberK0000/F/03/'
TD='https://opendata.tdcc.com.tw/getOD.ashx?id='
SOURCES=[('境內','nav',11109,SIT+'nav.csv'),('境內','div',160547,SIT+'160547%E6%8A%95%E4%BF%A1%E6%8A%95%E9%A1%A7%E5%85%AC%E6%9C%83%E5%A2%83%E5%85%A7%E5%9F%BA%E9%87%91%E9%85%8D%E6%81%AF%E8%B3%87%E6%96%99.csv'),('境外','div',11642,TD+'3-5')]+[('境外','nav',n,TD+k) for n,k in [(37818,'3-20'),(37820,'3-22'),(37821,'3-21')]]
def norm(s): return re.sub(r'\s+','',unicodedata.normalize('NFKC',str(s or '')).casefold())
def currency(s):
 s=norm(s); return {'美元':'usd','美金':'usd','南非幣':'zar','南非蘭特':'zar','新臺幣':'twd','新台幣':'twd','台幣':'twd','臺幣':'twd','歐元':'eur','日圓':'jpy','日元':'jpy','澳幣':'aud','澳元':'aud','英鎊':'gbp','人民幣':'cny','港幣':'hkd','港元':'hkd','瑞士法郎':'chf','加幣':'cad','加拿大幣':'cad','紐幣':'nzd'}.get(s,s)
def date(s):
 p=re.findall(r'\d+',str(s));
 if len(p)==1 and len(p[0]) in (7,8): p=[p[0][:-4],p[0][-4:-2],p[0][-2:]]
 if len(p)!=3:return None
 try:
  y,m,d=map(int,p); y+=1911 if y<1911 else 0; return datetime.date(y,m,d).isoformat()
 except ValueError:return None
def number(s):
 try:
  n=float(str(s).replace(',','')); return n if math.isfinite(n) and n>=0 else None
 except (ValueError,TypeError):return None
def rows(raw):
 for enc in ('utf-8-sig','cp950','utf-16'):
  try: t=raw.decode(enc);break
  except UnicodeError:continue
 else:raise ValueError('encoding')
 return [{(k or '').strip(): (v or '').strip() for k,v in r.items() if k and isinstance(v,str)} for r in csv.DictReader(io.StringIO(t))]
def get(r,*ks):
 fields={norm(k):v for k,v in r.items()}
 return next((fields[norm(k)] for k in ks if fields.get(norm(k)) not in (None,'')), '')
AMOUNT_FIELDS=('每單位分派金額','每單位分派金額(原幣別)','每單位配息金額','每單位配息金額(原幣別)','每單位配息','每受益權單位配息金額','每單位收益分配金額','每單位收益分配金額(原幣別)','每單位可分配金額')
PRE_FIELDS=('除息日前一日之淨值','除息日前一日淨值','除息前一日淨值')
def fetch(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'FundCatalog/1.0','Accept':'application/json,text/csv,*/*'}),timeout=45) as resp:return resp.read()
def api_div_rows():
 # Discover the actual endpoint from TDCC's published OpenAPI description.
 base='https://openapi.tdcc.com.tw/'
 doc=json.loads(fetch(base+'tdcc-opendata-api-docs'))
 for path,ops in doc.get('paths',{}).items():
  op=ops.get('get',{})
  if not op or not (path.rstrip('/').endswith('/3-5') or '境外基金配息資訊' in str(op.get('summary',''))):continue
  servers=op.get('servers') or ops.get('servers') or doc.get('servers') or [{'url':base}]
  for server in servers:
   url=urllib.parse.urljoin(base,server['url'].rstrip('/')+'/')+path.lstrip('/')
   u=urllib.parse.urlparse(url)
   if u.scheme!='https' or not (u.hostname or '').endswith('.tdcc.com.tw') or '{' in url:continue
   try:
    obj=json.loads(fetch(url))
    if isinstance(obj,dict):obj=next((obj[k] for k in ('data','result','records','items') if isinstance(obj.get(k),list)),None)
    if isinstance(obj,list) and obj and all(isinstance(x,dict) for x in obj):
     print('11642 OpenAPI endpoint',url);return obj
   except Exception as e:print('11642 OpenAPI ERROR',str(e))
 raise ValueError('No usable TDCC OpenAPI rows')
def frequency(r):
 v=norm(get(r,'配息頻率'))
 return {'月配':12,'月配息':12,'每月':12,'每月配息':12,'monthly':12,'季配':4,'季配息':4,'每季':4,'每季配息':4,'quarterly':4,'半年配':2,'半年配息':2,'每半年':2,'年配':1,'年配息':1,'每年':1}.get(v)
def ingest(rr,m,kind,sid,idx,data,today):
 count=matched=missing=dates=0
 if not rr:raise ValueError('empty data')
 print(sid,'headers:',list(rr[0]))
 for r in rr:
  k=match(r,m,idx)
  if not k:continue
  matched+=1
  d=date(get(r,'淨值日期','日期') if kind=='nav' else get(r,'除息日','除息日期'))
  n=number(get(r,'基金淨值','最新淨值小計(總額)') if kind=='nav' else get(r,*AMOUNT_FIELDS))
  if n is None:missing+=1
  if not d or d>today:continue
  if kind=='nav':
   if n is None or n<=0:continue
   f=data.setdefault(k,{'navs':{},'history':{}});f['navs'][d]={'amount':n,'source':sid};count+=1
  else:
   f=data.setdefault(k,{'navs':{},'history':{}})
   h=f['history'].setdefault(d,{'date':d,'amount':None,'source':sid,'frequency':None})
   dates+=1
   if n is not None:h.update(amount=n,source=sid);count+=1
   freq=frequency(r)
   if freq:h['frequency']=freq
   pre=number(get(r,*PRE_FIELDS))
   if pre is not None and pre>0:h['pre_ex_nav']=pre
 return count,matched,missing,dates

def key(f):return '|'.join([f['market'],norm(f.get('isin') or f.get('code')),currency(f.get('currency')),norm(f.get('name'))])
def index(catalog):
 idx=defaultdict(set)
 for f in catalog:
  for typ,v in [('isin',f.get('isin')),('code',f.get('code'))]:
   if v and f.get('currency'):idx[(f['market'],typ,norm(v),currency(f['currency']))].add(key(f))
 return idx
def match(r,m,idx):
 cu=currency(get(r,'計價幣別','基金幣別','配息幣別','幣別','基金計價幣別')); hits=[]
 for typ,v in [('isin',get(r,'基金ISIN_CODE','基金ISIN Code','ISIN','ISIN Code','ISIN_CODE','基金ISIN')),('code',get(r,'基金統編','基金代碼','統編'))]:
  if v:
   h=idx.get((m,typ,norm(v),cu),set());
   if h:hits.append(h)
 if not hits:return None
 h=set.intersection(*hits);return next(iter(h)) if len(h)==1 else None
def main():
 catalog=json.loads((ROOT/'catalog.json').read_text())['funds']; idx=index(catalog); path=ROOT/'quotes.json'; old=json.loads(path.read_text()) if path.exists() else {}; data=old.get('funds',{}); status=[]; today=datetime.date.today().isoformat(); cutoff=(datetime.date.today()-datetime.timedelta(days=366)).isoformat()
 for m,kind,sid,url in SOURCES:
  count=matched=missing_amount=dates=0
  try:
   rr=rows(fetch(url));count,matched,missing_amount,dates=ingest(rr,m,kind,sid,idx,data,today)
  except Exception as e:print(sid,'CSV ERROR',str(e))
  if sid==11642 and count==0:
   try:
    ar=api_div_rows();ac,am,ax,ad=ingest(ar,m,kind,sid,idx,data,today)
    count+=ac;matched+=am;missing_amount+=ax;dates+=ad
   except Exception as e:print(sid,'OpenAPI fallback unavailable',str(e))
  status.append({'id':sid,'count':count,'ok':count>0,'identity_matches':matched,'missing_amount':missing_amount,'date_matches':dates})
  print(sid,'matched',count,'identity_matches',matched,'missing_amount',missing_amount,'date_matches',dates)
 for k,f in list(data.items()):
  f['navs']={d:v for d,v in f.get('navs',{}).items() if d>=cutoff};f['history']={d:v for d,v in f.get('history',{}).items() if d>=cutoff}
  if not f['navs'] and not f['history']:del data[k];continue
  nd=max(f['navs'],default=''); hist=sorted(f['history'].values(),key=lambda h:h['date'],reverse=True);h=hist[0] if hist else {}; ex=h.get('date'); prev=(datetime.date.fromisoformat(ex)-datetime.timedelta(days=1)).isoformat() if ex else ''; pre=h.get('pre_ex_nav') or f['navs'].get(prev,{}).get('amount')
  f.update(nav=f['navs'].get(nd,{}).get('amount'),nav_date=nd or None,nav_source=f['navs'].get(nd,{}).get('source'),distribution=h.get('amount'),ex_date=ex,pre_ex_nav=pre,payments_per_year=h.get('frequency'),records=hist)
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps({'updated':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':status,'funds':data},ensure_ascii=False,separators=(',',':')),encoding='utf-8');tmp.replace(path)
 if not any(s['ok'] for s in status): raise SystemExit('No verified rows; check source headers')
if __name__=='__main__':main()
