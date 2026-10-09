"""Builds dashboard/index.html from the latest weather data.

Put this file in weather-etl/etl/dashboard.py and run it after the load step.
Reads MySQL first (same .env settings as load.py), falls back to
data/processed/weather_clean.csv. Columns are detected automatically.
"""
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "processed" / "weather_clean.csv"
OUT = ROOT / "dashboard" / "index.html"
load_dotenv(ROOT / ".env")


def _from_mysql():
    from sqlalchemy import create_engine, inspect
    url = (f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
           f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
    eng = create_engine(url)
    tables = inspect(eng).get_table_names()
    table = os.getenv("DB_TABLE") or next(
        (t for t in tables if "weather" in t.lower()), tables[0])
    df = pd.read_sql(f"SELECT * FROM `{table}`", eng)
    return df, f"MySQL table {table}"


def load_data():
    try:
        return _from_mysql()
    except Exception as e:
        print(f"[dashboard] MySQL not used ({type(e).__name__}); reading CSV instead")
        return pd.read_csv(CSV), "CSV file"


def _pick(cols, hints):
    for h in hints:
        for c in cols:
            if h in str(c).lower():
                return c
    return None


def build_dashboard():
    df, source = load_data()
    df = df.tail(5000).copy()
    cols = list(df.columns)

    tcol = _pick(cols, ["timestamp", "datetime", "date", "time", "dt"])
    if tcol is not None:
        parsed = pd.to_datetime(df[tcol], errors="coerce")
        if parsed.notna().mean() > 0.5:
            df[tcol] = parsed
            df = df.sort_values(tcol)
        else:
            tcol = None

    nums = [c for c in df.select_dtypes("number").columns
            if str(c).lower() != "id" and not str(c).lower().endswith("_id")
            and str(c).lower() not in ("lat", "lon", "latitude", "longitude")]
    ccol = _pick(cols, ["city", "location", "place", "name"])
    if ccol is None:
        ccol = next(c for c in cols if c not in nums and c != tcol)

    keep = [ccol] + ([tcol] if tcol else []) + nums
    out = df[keep].copy()
    if tcol:
        out[tcol] = out[tcol].dt.strftime("%Y-%m-%d %H:%M")
    rows = json.loads(out.to_json(orient="records"))

    data = {"rows": rows, "metrics": nums, "city": ccol, "time": tcol,
            "source": source,
            "updated": datetime.now().strftime("%d %b %Y, %H:%M")}
    html = TEMPLATE.replace("__DATA__", json.dumps(data))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Dashboard updated: {OUT} ({len(rows)} rows from {source})")


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Weather ETL dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;800&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{--bg:#edf1f2;--ink:#13242f;--mute:#5d707c;--line:#d3dde2;--panel:#fff;--accent:#0f6e8c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Public Sans",system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:28px 18px 48px}
header{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:12px;border-bottom:2px solid var(--ink);padding-bottom:14px}
h1{margin:0;font-size:clamp(26px,4vw,40px);font-weight:800;letter-spacing:-.02em}
.stamp{text-align:right;color:var(--mute);font-size:13px}
.stamp b{display:block;color:var(--ink);font-size:15px}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:18px 0}
select,.chip{font:inherit;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:6px;padding:6px 12px;cursor:pointer}
.chip{display:flex;align-items:center;gap:7px}.chip i{width:10px;height:10px;border-radius:50%}
.chip.off{opacity:.4}
select:focus-visible,.chip:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.facts{display:flex;flex-wrap:wrap;gap:34px;margin:6px 0 20px}
.facts div{font-size:13px;color:var(--mute)}.facts strong{display:block;font-size:26px;color:var(--ink);line-height:1.2}
.grid{display:grid;grid-template-columns:2fr 1fr;gap:16px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:16px}
.panel h2{margin:0 0 10px;font-size:15px;font-weight:600}
.box{position:relative;height:300px}
.wide{grid-column:1/-1;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:7px 12px 7px 0;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--mute);font-weight:600}
@media(max-width:760px){.grid{grid-template-columns:1fr}}
</style></head><body><main>
<header><h1>Weather across the cities</h1>
<div class="stamp"><b id="upd"></b><span id="src"></span></div></header>
<div class="controls"><label>Measure <select id="metric"></select></label><span id="chips" style="display:contents"></span></div>
<div class="facts" id="facts"></div>
<div class="grid">
<section class="panel"><h2 id="t1"></h2><div class="box"><canvas id="line"></canvas></div></section>
<section class="panel"><h2 id="t2"></h2><div class="box"><canvas id="bar"></canvas></div></section>
<section class="panel wide"><h2>Newest rows</h2><table id="tbl"></table></section>
</div></main>
<script>
const D=__DATA__, R=D.rows, C=D.city, T=D.time, M=D.metrics;
const cities=[...new Set(R.map(r=>r[C]))];
const pal=["#0f6e8c","#d9831f","#4b8f3a","#a8446a","#6a5acd","#c0392b","#2a9d8f","#7f8c8d"];
const col=c=>pal[cities.indexOf(c)%pal.length];
const nice=s=>s.replace(/_/g," ");
const fmt=v=>v==null?"n/a":(Number.isInteger(v)?v:v.toFixed(1));
let metric=M[0], on=new Set(cities), lc, bc;
document.getElementById("upd").textContent="Updated "+D.updated;
document.getElementById("src").textContent="Source: "+D.source+", "+R.length+" rows";
const sel=document.getElementById("metric");
M.forEach(m=>sel.add(new Option(nice(m),m)));
sel.onchange=()=>{metric=sel.value;draw()};
const chips=document.getElementById("chips");
cities.forEach(c=>{const b=document.createElement("button");b.className="chip";
 b.innerHTML='<i style="background:'+col(c)+'"></i>'+c;
 b.onclick=()=>{on.has(c)?on.delete(c):on.add(c);b.classList.toggle("off",!on.has(c));draw()};chips.append(b)});
function draw(){
 const live=cities.filter(c=>on.has(c));
 const labels=T?[...new Set(R.map(r=>r[T]))].sort():R.map((_,i)=>i+1);
 const ds=live.map(c=>{const mp={};R.filter(r=>r[C]===c).forEach((r,i)=>mp[T?r[T]:R.indexOf(r)+1]=r[metric]);
  return{label:c,data:labels.map(l=>mp[l]??null),borderColor:col(c),backgroundColor:col(c),tension:.3,spanGaps:true,pointRadius:2}});
 const last=live.map(c=>{const x=R.filter(r=>r[C]===c);return x[x.length-1]});
 document.getElementById("t1").textContent=nice(metric)+" over time";
 document.getElementById("t2").textContent="Latest "+nice(metric)+" by city";
 lc&&lc.destroy();bc&&bc.destroy();
 lc=new Chart("line",{type:"line",data:{labels,datasets:ds},options:{maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{maxTicksLimit:8}}}}});
 bc=new Chart("bar",{type:"bar",data:{labels:live,datasets:[{data:last.map(r=>r[metric]),backgroundColor:live.map(col)}]},options:{indexAxis:"y",maintainAspectRatio:false,plugins:{legend:{display:false}}}});
 const v=last.filter(r=>r[metric]!=null).sort((a,b)=>b[metric]-a[metric]);
 document.getElementById("facts").innerHTML=v.length?
  '<div>Highest '+nice(metric)+'<strong>'+v[0][C]+' ('+fmt(v[0][metric])+')</strong></div>'+
  '<div>Lowest<strong>'+v[v.length-1][C]+' ('+fmt(v[v.length-1][metric])+')</strong></div>'+
  '<div>Cities shown<strong>'+live.length+'</strong></div>':"";
 const h=[C,...(T?[T]:[]),...M], rows=R.filter(r=>on.has(r[C])).slice(-12).reverse();
 document.getElementById("tbl").innerHTML="<tr>"+h.map(x=>"<th>"+nice(x)+"</th>").join("")+"</tr>"+
  rows.map(r=>"<tr>"+h.map(x=>"<td>"+(typeof r[x]==="number"?fmt(r[x]):r[x]??"")+"</td>").join("")+"</tr>").join("");
}
draw();
</script></body></html>"""

if __name__ == "__main__":
    build_dashboard()