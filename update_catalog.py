import csv, io, json, pathlib, urllib.request, datetime
ROOT=pathlib.Path(__file__).parent
SOURCES=[('境外','https://opendata.tdcc.com.tw/getOD.ashx?id=3-2','https://data.gov.tw/dataset/11639'),('境內','https://www.sitca.org.tw/MemberK0000/F/03/43476%E6%8A%95%E4%BF%A1%E6%8A%95%E9%A1%A7%E5%85%AC%E6%9C%83%E5%A2%83%E5%85%A7%E5%9F%BA%E9%87%91%E5%9F%BA%E6%9C%AC%E8%B3%87%E6%96%99.csv','https://data.gov.tw/dataset/43476')]
def parse(raw,market,source):
    for enc in ('utf-8-sig','cp950','utf-16'):
        try: content=raw.decode(enc); break
        except UnicodeError: continue
    else: raise ValueError('Unknown encoding')
    result=[]
    for row in csv.DictReader(io.StringIO(content)):
        r={k.strip(): (v or '').strip() for k,v in row.items() if k}
        def get(*keys): return next((r[k] for k in keys if r.get(k)), '')
        name=get('基金名稱')
        if not name: continue
        result.append(dict(name=name,company=get('公司名稱','境外基金機構','基金總代理名稱'),currency=get('計價幣別','基金計價幣別'),isin=get('基金ISIN_CODE','基金ISIN Code'),code=get('基金代碼','統編'),category=get('基金種類','基金類型別'),date=get('資料日期','年月'),market=market,source=source))
    if len(result)<100: raise ValueError(f'{market}: unexpected count {len(result)}')
    return result
if __name__=='__main__':
    all_rows=[]
    for market,url,source in SOURCES:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'FundCatalog/1.0'}),timeout=90) as r: raw=r.read()
        all_rows.extend(parse(raw,market,source))
    output=ROOT/'data/catalog.json'; tmp=output.with_suffix('.tmp'); tmp.write_text(json.dumps({'updated':datetime.datetime.now(datetime.timezone.utc).isoformat(),'funds':all_rows},ensure_ascii=False),encoding='utf-8'); tmp.replace(output)
    print(len(all_rows))
