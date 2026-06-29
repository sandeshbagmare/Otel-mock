"""HTML/CSS/JS for the mock provider pages and the unified dashboard.

Pages are built with simple ``__PLACEHOLDER__`` substitution (not str.format)
so the embedded CSS/JS braces don't need escaping. Live updates use plain
fetch polling against the JSON API — no websockets, no build step.
"""

import json

_CSS = """
:root { --bg:#0d1117; --panel:#161b22; --panel2:#1c2430; --line:#2a3340;
        --text:#e6edf3; --muted:#8b98a8; --accent:__ACCENT__; --brand:__COLOR__; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--text);
       font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }
a { color:var(--accent); text-decoration:none; }
code,.mono { font-family:"SF Mono",Consolas,"Roboto Mono",monospace; }
header.bar { background:linear-gradient(110deg,var(--brand),#0d1117 78%);
             border-bottom:1px solid var(--line); padding:18px 24px; display:flex;
             align-items:center; gap:16px; flex-wrap:wrap; }
.brandchip { width:46px; height:46px; border-radius:12px; background:var(--accent);
             display:flex; align-items:center; justify-content:center; color:#0d1117;
             font-weight:800; font-size:20px; box-shadow:0 0 0 4px rgba(255,255,255,.06); }
.htext h1 { margin:0; font-size:20px; letter-spacing:.2px; }
.htext .tag { color:var(--muted); font-size:13px; }
.badge { font-size:10px; font-weight:700; letter-spacing:1px; padding:3px 8px;
         border-radius:6px; background:rgba(255,255,255,.08); color:var(--muted); }
.badge.mock { background:var(--accent); color:#0d1117; }
.spacer { flex:1; }
.live { display:flex; align-items:center; gap:7px; color:var(--muted); font-size:12px; }
.dot { width:9px; height:9px; border-radius:50%; background:#3fb950;
       box-shadow:0 0 8px #3fb950; animation:pulse 1.6s infinite; }
.dot.off { background:#6e7681; box-shadow:none; animation:none; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.35} }
.wrap { padding:20px 24px; max-width:1280px; margin:0 auto; }
.stats { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:18px; }
.stat { background:var(--panel); border:1px solid var(--line); border-radius:12px;
        padding:12px 16px; min-width:104px; }
.stat .n { font-size:24px; font-weight:700; }
.stat .l { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.6px; }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:12px;
         padding:16px; margin-bottom:18px; }
.panel h3 { margin:0 0 10px; font-size:13px; color:var(--muted); text-transform:uppercase;
            letter-spacing:.6px; }
.ep { display:flex; align-items:center; gap:10px; margin:6px 0; flex-wrap:wrap; }
.ep .m { background:#0d1117; border:1px solid var(--line); border-radius:7px;
         padding:6px 10px; font-size:12.5px; color:#cdd9e5; }
.ep .verb { color:var(--accent); font-weight:700; font-size:11px; }
.copy { cursor:pointer; border:1px solid var(--line); background:var(--panel2);
        color:var(--muted); border-radius:6px; padding:4px 8px; font-size:11px; }
.copy:hover { color:var(--text); }
.toolbar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:10px; }
.chip { cursor:pointer; border:1px solid var(--line); background:var(--panel);
        color:var(--muted); border-radius:20px; padding:6px 14px; font-size:12.5px; }
.chip.on { background:var(--accent); color:#0d1117; border-color:var(--accent); font-weight:700; }
input.search { flex:1; min-width:160px; background:#0d1117; border:1px solid var(--line);
        border-radius:8px; color:var(--text); padding:8px 12px; font-size:13px; }
table { width:100%; border-collapse:collapse; }
th { text-align:left; color:var(--muted); font-size:11px; text-transform:uppercase;
     letter-spacing:.6px; padding:8px 10px; border-bottom:1px solid var(--line); position:sticky; top:0;
     background:var(--panel); }
td { padding:9px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
tr.row { cursor:pointer; } tr.row:hover { background:var(--panel2); }
.sig { font-size:10px; font-weight:700; padding:2px 8px; border-radius:6px; letter-spacing:.5px; }
.sig.trace { background:#1f6feb33; color:#79c0ff; } .sig.metric{ background:#23863633; color:#7ee787; }
.sig.log { background:#9e6a0333; color:#f0b86e; } .sig.unknown{ background:#6e768133; color:#adbac7; }
.svc { color:#cdd9e5; } .t { color:var(--muted); font-size:12px; white-space:nowrap; }
.sum { color:#e6edf3; } .ingest { color:var(--muted); font-size:11px; }
.raw { background:#0a0d12; border:1px solid var(--line); border-radius:8px; padding:12px;
       margin:6px 0 2px; white-space:pre; overflow:auto; max-height:340px; font-size:12px; color:#cdd9e5; }
.empty { color:var(--muted); text-align:center; padding:40px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(250px,1fr)); gap:14px; margin-bottom:20px; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:14px; overflow:hidden;
        transition:transform .12s, border-color .12s; }
.card:hover { transform:translateY(-2px); border-color:#3d4754; }
.card .strip { height:6px; } .card .body { padding:14px 16px; }
.card .cn { font-weight:700; font-size:15px; display:flex; align-items:center; gap:8px; }
.card .ct { color:var(--muted); font-size:11.5px; margin:2px 0 12px; }
.card .nums { display:flex; gap:14px; }
.card .nums div span { display:block; }
.card .nums .v { font-size:18px; font-weight:700; } .card .nums .k { font-size:10px; color:var(--muted); text-transform:uppercase; }
.card .open { margin-top:12px; font-size:12px; }
.pbadge { font-size:10px; font-weight:700; padding:2px 8px; border-radius:6px; color:#0d1117; }
.foot { color:var(--muted); font-size:12px; text-align:center; padding:24px 0 10px; }
"""


def _page(title, body_html, css_vars, script_js):
    css = _CSS.replace("__ACCENT__", css_vars["accent"]).replace("__COLOR__", css_vars["color"])
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>" + title + "</title><style>" + css + "</style></head><body>"
        + body_html
        + "<script>" + script_js + "</script></body></html>"
    )


# --------------------------------------------------------------------------- #
# Provider page
# --------------------------------------------------------------------------- #
_PROVIDER_BODY = """
<header class='bar'>
  <div class='brandchip'>__INITIAL__</div>
  <div class='htext'><h1>__NAME__ <span class='badge mock'>MOCK</span></h1>
    <div class='tag'>__TAGLINE__</div></div>
  <div class='spacer'></div>
  <div class='live'><span class='dot' id='dot'></span><span id='status'>listening</span></div>
</header>
<div class='wrap'>
  <div class='stats' id='stats'></div>
  <div class='panel'>
    <h3>Point your OpenTelemetry exporter here</h3>
    <div id='endpoints'></div>
  </div>
  <div class='toolbar'>
    <div class='chip on' data-f='all'>All</div>
    <div class='chip' data-f='trace'>Traces</div>
    <div class='chip' data-f='metric'>Metrics</div>
    <div class='chip' data-f='log'>Logs</div>
    <input class='search' id='search' placeholder='filter by service, name, attribute…'>
    <div class='chip' id='pause'>⏸ Pause</div>
    <div class='chip' id='clear'>Clear view</div>
  </div>
  <div class='panel' style='padding:0'>
    <table><thead><tr><th style='width:96px'>Time</th><th style='width:74px'>Signal</th>
      <th style='width:160px'>Service</th><th>Summary</th><th style='width:130px'>Received as</th></tr></thead>
      <tbody id='rows'></tbody></table>
    <div class='empty' id='empty'>Waiting for telemetry… send some data to one of the endpoints above.</div>
  </div>
</div>
<div class='foot'>mockotel · local mock of <b>__NAME__</b> · this is NOT the real vendor</div>
"""

_PROVIDER_JS = """
const CFG = __CFG__;
let cursor = 0, filter = 'all', paused = false, search = '';
const rowsEl = document.getElementById('rows');
const emptyEl = document.getElementById('empty');
const data = [];

function ep(verb, path) {
  return `<div class='ep'><span class='verb'>${verb}</span>`+
    `<span class='m'>${location.origin}${path}</span>`+
    `<span class='copy' data-c='${location.origin}${path}'>copy</span></div>`;
}
function renderEndpoints() {
  let h = ep('POST','/v1/traces') + ep('POST','/v1/metrics') + ep('POST','/v1/logs');
  if (CFG.native_paths && CFG.native_paths.length)
    h += CFG.native_paths.map(p => ep('POST', p)).join('');
  h += `<div style='color:var(--muted);font-size:12px;margin-top:8px'>`+
       `Set <code>OTEL_EXPORTER_OTLP_ENDPOINT=${location.origin}</code> and `+
       `<code>OTEL_EXPORTER_OTLP_PROTOCOL=http/json</code> · `+
       `or run the Docker collector for gRPC/protobuf.</div>`;
  document.getElementById('endpoints').innerHTML = h;
}
function fmtTime(ts){ const d=new Date(ts*1000);
  return d.toLocaleTimeString([], {hour12:false}) + '.' + String(d.getMilliseconds()).padStart(3,'0'); }
function statBox(n,l){ return `<div class='stat'><div class='n'>${n}</div><div class='l'>${l}</div></div>`; }
function renderStats(s){
  const b = s.by_signal||{};
  document.getElementById('stats').innerHTML =
    statBox(s.requests||0,'Requests') + statBox(b.trace||0,'Traces') +
    statBox(b.metric||0,'Metrics') + statBox(b.log||0,'Logs') +
    statBox(Object.keys(s.services||{}).length,'Services') +
    statBox((s.uptime_s||0).toFixed(0)+'s','Uptime');
}
function passes(r){
  if (filter!=='all' && r.signal!==filter) return false;
  if (search){ const blob=JSON.stringify(r).toLowerCase(); if(!blob.includes(search)) return false; }
  return true;
}
function rowHtml(r){
  const sig = r.signal||'unknown';
  return `<tr class='row' data-seq='${r.seq}'><td class='t'>${fmtTime(r.ts)}</td>`+
    `<td><span class='sig ${sig}'>${sig.toUpperCase()}</span></td>`+
    `<td class='svc'>${esc(r.service||'')}</td>`+
    `<td class='sum'>${esc(r.summary||r.name||'')}</td>`+
    `<td class='ingest'>${esc(r.ingest||'')}</td></tr>`;
}
function esc(s){ return String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
function render(){
  const vis = data.filter(passes).slice(-600);
  emptyEl.style.display = vis.length ? 'none':'block';
  rowsEl.innerHTML = vis.map(rowHtml).reverse().join('');
}
async function poll(){
  if (!paused){
    try{
      const res = await fetch(`/api/records?since=${cursor}&limit=300`);
      const j = await res.json();
      if (j.records && j.records.length){
        for (const r of j.records){ data.push(r); cursor=Math.max(cursor,r.seq); }
        if (data.length>4000) data.splice(0, data.length-4000);
        render();
      }
      if (j.stats) renderStats(j.stats);
      document.getElementById('dot').classList.remove('off');
      document.getElementById('status').textContent='listening';
    }catch(e){
      document.getElementById('dot').classList.add('off');
      document.getElementById('status').textContent='disconnected';
    }
  }
}
document.addEventListener('click', e=>{
  const chip=e.target.closest('.chip[data-f]');
  if(chip){ document.querySelectorAll('.chip[data-f]').forEach(c=>c.classList.remove('on'));
            chip.classList.add('on'); filter=chip.dataset.f; render(); return; }
  if(e.target.id==='pause'){ paused=!paused; e.target.textContent=paused?'▶ Resume':'⏸ Pause';
            e.target.classList.toggle('on',paused); return; }
  if(e.target.id==='clear'){ data.length=0; render(); return; }
  const cp=e.target.closest('.copy');
  if(cp){ navigator.clipboard?.writeText(cp.dataset.c); cp.textContent='copied'; setTimeout(()=>cp.textContent='copy',900); return; }
  const row=e.target.closest('tr.row');
  if(row){ const seq=+row.dataset.seq; const rec=data.find(r=>r.seq===seq);
    const nxt=row.nextElementSibling;
    if(nxt && nxt.classList.contains('rawrow')){ nxt.remove(); return; }
    const tr=document.createElement('tr'); tr.className='rawrow';
    tr.innerHTML=`<td colspan='5'><div class='raw'>${esc(JSON.stringify(rec,null,2))}</div></td>`;
    row.after(tr); }
});
document.getElementById('search').addEventListener('input', e=>{ search=e.target.value.toLowerCase(); render(); });
renderEndpoints(); poll(); setInterval(poll, 1000);
"""


def provider_page(provider):
    body = (_PROVIDER_BODY
            .replace("__INITIAL__", (provider["name"][:1] or "M").upper())
            .replace("__NAME__", provider["name"])
            .replace("__TAGLINE__", provider.get("tagline", "")))
    js = _PROVIDER_JS.replace("__CFG__", json.dumps(provider))
    return _page("Mock " + provider["name"] + " · mockotel", body,
                 {"accent": provider["accent"], "color": provider["color"]}, js)


# --------------------------------------------------------------------------- #
# Unified dashboard
# --------------------------------------------------------------------------- #
_DASH_BODY = """
<header class='bar'>
  <div class='brandchip'>O</div>
  <div class='htext'><h1>Mock OTEL · Unified Telemetry Dashboard</h1>
    <div class='tag'>One live view across every mock provider on this machine</div></div>
  <div class='spacer'></div>
  <div class='live'><span class='dot' id='dot'></span><span id='status'>aggregating</span></div>
</header>
<div class='wrap'>
  <div class='stats' id='stats'></div>
  <h3 style='color:var(--muted);text-transform:uppercase;letter-spacing:.6px;font-size:13px'>Providers</h3>
  <div class='grid' id='cards'></div>
  <div class='toolbar'>
    <div class='chip on' data-f='all'>All</div>
    <div class='chip' data-f='trace'>Traces</div>
    <div class='chip' data-f='metric'>Metrics</div>
    <div class='chip' data-f='log'>Logs</div>
    <input class='search' id='search' placeholder='filter the firehose…'>
    <div class='chip' id='pause'>⏸ Pause</div>
  </div>
  <div class='panel' style='padding:0'>
    <table><thead><tr><th style='width:96px'>Time</th><th style='width:128px'>Provider</th>
      <th style='width:66px'>Signal</th><th style='width:150px'>Service</th><th>Summary</th></tr></thead>
      <tbody id='rows'></tbody></table>
    <div class='empty' id='empty'>No telemetry yet. Send data to any provider — it shows up here.</div>
  </div>
</div>
<div class='foot'>mockotel · unified dashboard · all data is local &amp; in-memory</div>
"""

_DASH_JS = """
let filter='all', paused=false, search='';
const data=[]; let lastKey='';
function esc(s){ return String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
function fmtTime(ts){ const d=new Date(ts*1000);
  return d.toLocaleTimeString([], {hour12:false})+'.'+String(d.getMilliseconds()).padStart(3,'0'); }
function statBox(n,l){ return `<div class='stat'><div class='n'>${n}</div><div class='l'>${l}</div></div>`; }
function passes(r){
  if(filter!=='all' && r.signal!==filter) return false;
  if(search){ if(!JSON.stringify(r).toLowerCase().includes(search)) return false; }
  return true;
}
function render(){
  const vis=data.filter(passes).slice(-600);
  document.getElementById('empty').style.display=vis.length?'none':'block';
  document.getElementById('rows').innerHTML=vis.map(r=>{
    const sig=r.signal||'unknown';
    return `<tr><td class='t'>${fmtTime(r.ts)}</td>`+
      `<td><span class='pbadge' style='background:${r.accent||'#888'}'>${esc(r.provider_name||r.provider)}</span></td>`+
      `<td><span class='sig ${sig}'>${sig.toUpperCase()}</span></td>`+
      `<td class='svc'>${esc(r.service||'')}</td>`+
      `<td class='sum'>${esc(r.summary||r.name||'')}</td></tr>`;
  }).reverse().join('');
}
function renderCards(providers){
  document.getElementById('cards').innerHTML = providers.map(p=>{
    const s=p.stats||{}, b=s.by_signal||{};
    const dotcls = p.up ? '' : 'off';
    return `<div class='card'><div class='strip' style='background:${p.accent}'></div>`+
      `<div class='body'><div class='cn'><span class='dot ${dotcls}' style='position:relative'></span>${esc(p.name)}</div>`+
      `<div class='ct'>${esc(p.tagline||'')}</div>`+
      `<div class='nums'>`+
        `<div><span class='v'>${b.trace||0}</span><span class='k'>traces</span></div>`+
        `<div><span class='v'>${b.metric||0}</span><span class='k'>metrics</span></div>`+
        `<div><span class='v'>${b.log||0}</span><span class='k'>logs</span></div>`+
        `<div><span class='v'>${s.requests||0}</span><span class='k'>reqs</span></div>`+
      `</div>`+
      `<div class='open'><a href='${p.url}' target='_blank'>Open ${esc(p.name)} →</a></div>`+
      `</div></div>`;
  }).join('');
}
async function pollStats(){
  try{
    const j=await (await fetch('/api/stats')).json();
    renderCards(j.providers||[]);
    const t=j.totals||{}, b=t.by_signal||{};
    document.getElementById('stats').innerHTML =
      statBox(j.providers?j.providers.filter(p=>p.up).length:0,'Providers up')+
      statBox(t.requests||0,'Requests')+statBox(b.trace||0,'Traces')+
      statBox(b.metric||0,'Metrics')+statBox(b.log||0,'Logs')+
      statBox(t.total||0,'Total items');
    document.getElementById('dot').classList.remove('off');
  }catch(e){ document.getElementById('dot').classList.add('off'); }
}
async function pollRecords(){
  if(paused) return;
  try{
    const j=await (await fetch('/api/records?limit=400')).json();
    const recs=j.records||[];
    const key=recs.length?recs[recs.length-1].provider+recs[recs.length-1].seq+'@'+recs.length:'';
    data.length=0; for(const r of recs) data.push(r);
    render();
    document.getElementById('status').textContent='aggregating';
  }catch(e){ document.getElementById('status').textContent='disconnected'; }
}
document.addEventListener('click',e=>{
  const chip=e.target.closest('.chip[data-f]');
  if(chip){ document.querySelectorAll('.chip[data-f]').forEach(c=>c.classList.remove('on'));
            chip.classList.add('on'); filter=chip.dataset.f; render(); return; }
  if(e.target.id==='pause'){ paused=!paused; e.target.textContent=paused?'▶ Resume':'⏸ Pause';
            e.target.classList.toggle('on',paused); }
});
document.getElementById('search').addEventListener('input',e=>{ search=e.target.value.toLowerCase(); render(); });
pollStats(); pollRecords(); setInterval(pollStats,1500); setInterval(pollRecords,1200);
"""


def dashboard_page():
    return _page("Mock OTEL · Unified Dashboard", _DASH_BODY,
                 {"accent": "#00ADB5", "color": "#13263a"}, _DASH_JS)
