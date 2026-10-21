'use strict';
const KIND='route';
const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const pretty=value=>JSON.stringify(value,null,2);
const fmt=(value,d=2)=>typeof value==='number'&&Number.isFinite(value)?value.toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d}):'—';
function status(message,error=false){$('status').textContent=message;$('status').classList.toggle('error',error);$('status').setAttribute('role',error?'alert':'status');}
async function request(path,body,timeout=15000){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeout);
  try{const response=await fetch(path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal});
    const json=await response.json();if(!response.ok){const e=new Error(json.error||`HTTP ${response.status}`);e.http=response.status;e.data=json;throw e;}return{data:json,status:response.status};
  }catch(error){if(error.name==='AbortError')throw new Error('Request timed out. The current result was not replaced; retry when the local service is ready.');throw error;}finally{clearTimeout(timer);}
}
async function busy(button,task,message='Calculating…'){
  const label=button.textContent;button.disabled=true;button.textContent='Working…';button.setAttribute('aria-busy','true');status(message);
  try{await task();}catch(error){status(error.message||'The local service is unavailable. Retry the request.',true);}finally{button.disabled=false;button.textContent=label;button.removeAttribute('aria-busy');}
}
function download(name,content,type='application/json'){
  const url=URL.createObjectURL(new Blob([content],{type}));const link=el('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function table(container,headers,rows){
  container.replaceChildren();container.tabIndex=0;const t=el('table');const caption=el('caption',headers.join(' · '));caption.className='small muted';t.append(caption);const head=el('thead'),tr=el('tr');for(const h of headers){const th=el('th',h);th.scope='col';tr.append(th);}head.append(tr);t.append(head);const body=el('tbody');for(const row of rows){const line=el('tr');for(const v of row)line.append(el('td',v==null?'—':String(v)));body.append(line);}t.append(body);container.append(t);
}
function metrics(container,items){container.replaceChildren();const row=el('div',undefined,'metrics');for(const [label,value]of items){const item=el('div',undefined,'metric');item.append(el('strong',value),el('span',label));row.append(item);}container.append(row);}
function routeTab(){let name=location.hash.slice(1)||'workspace';if(!document.querySelector(`[data-panel="${CSS.escape(name)}"]`))name='workspace';$('status').hidden=name==='lab';for(const p of document.querySelectorAll('[data-panel]'))p.hidden=p.dataset.panel!==name;const slot=document.querySelector(`[data-panel="${CSS.escape(name)}"] .status-slot`);if(slot)slot.append($("status"));for(const a of document.querySelectorAll('[data-nav]')){if(a.dataset.nav===name)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');}}
addEventListener('hashchange',()=>{routeTab();scrollTo({top:0,behavior:'instant'});scheduleDraw();});routeTab();
let apiSpec,apiEntries=[];
async function setupApi(){
  apiSpec=(await request('/openapi.json')).data;apiEntries=[];
  for(const [path,methods]of Object.entries(apiSpec.paths))for(const [method,definition]of Object.entries(methods))apiEntries.push({path,method:method.toUpperCase(),definition});
  apiEntries.sort((a,b)=>(a.method==='POST'?0:1)-(b.method==='POST'?0:1));$('endpoint').replaceChildren();for(const [i,item]of apiEntries.entries()){const opt=el('option',`${item.method} ${item.path}`);opt.value=i;$('endpoint').append(opt);}
  setApiExample();
}
function setApiExample(){const endpoint=apiEntries[Number($('endpoint').value)];if(!endpoint)return;const post=endpoint.method==='POST';$('api-body').hidden=!post;$('api-get-note').hidden=post;$('api-body').value=pretty(endpoint.definition.requestBody?.content?.['application/json']?.example||{});$('api-help').textContent=endpoint.definition.summary;$('http-status').textContent='Not sent';$('api-response').textContent='Send a request to inspect the response.';}
$('endpoint').addEventListener('change',setApiExample);
$('send-api').addEventListener('click',()=>busy($('send-api'),async()=>{
  const item=apiEntries[Number($('endpoint').value)];let payload;if(item.method==='POST'){try{payload=JSON.parse($('api-body').value);}catch{throw new Error('Request JSON is invalid. Fix it before sending.');}}
  try{const result=await request(item.path,payload);$('http-status').textContent=`HTTP ${result.status}`;$('api-response').textContent=pretty(result.data);status('API response received from the local service.');}
  catch(error){$('http-status').textContent=error.http?`HTTP ${error.http}`:'Request failed';$('api-response').textContent=pretty(error.data||{error:error.message});throw error;}
},'Sending API request…'));
$('copy-curl').addEventListener('click',async()=>{try{const item=apiEntries[Number($('endpoint').value)];const quote=s=>"'"+s.replaceAll("'","'\\''")+"'";let command=`curl ${quote(location.origin+item.path)}`;if(item.method==='POST')command+=` -H 'Content-Type: application/json' --data ${quote($('api-body').value)}`;await navigator.clipboard.writeText(command);status('curl command copied (POSIX shell quoting).');}catch{status('Clipboard is unavailable. The endpoint and JSON body remain visible for copying.',true);}});
async function setupEvidence(meta){$('provenance').textContent=pretty(meta);const response=await request('/api/evidence');$('evidence-files').replaceChildren();for(const file of response.data.files){const li=el('li'),a=el('a',file.name);a.href=file.url;a.download=file.name;li.append(a,el('span',`${fmt(file.bytes/1024,1)} KiB`,'muted mono'));$('evidence-files').append(li);}if(!response.data.files.length)$('evidence-files').append(el('li','No recorded files yet. Run the project CLI first.'));}
async function initialize(){try{$('init-error').hidden=true;await initProject();await setupApi();}catch(error){$('init-error').hidden=false;status(error.message,true);}}
$('retry-init').addEventListener('click',initialize);

let scenarios=[],map=null,original=null,result=null,cursor=[0,0],mapRevision=0,mapDraftRevision=0,mapImportRevision=0,mapView=null,drawFrame=0;
const same=(a,b)=>a[0]===b[0]&&a[1]===b[1];
const algorithmName=value=>value==='astar'?'A*':'Dijkstra';
const scenarioName=s=>({'campus':'Campus passages','weighted-detour':'Cheaper detour','unreachable':'Closed passage','open':'Open courtyard'}[s.id]||s.name);

function invalidateMap(){
  mapRevision++;result=null;
  $('trace-step').disabled=true;$('trace-step').value=0;$('trace-count').textContent='0';
  $('route-result').replaceChildren(el('p','Inputs changed. Run a search for a current result.','muted'));
  $('route-summary').textContent='Inputs changed · run a search again.';
  $('comparison').hidden=true;$('comparison').replaceChildren();
  $('path-table').replaceChildren();$('trace-note').textContent='';
  status('Inputs changed. Run the search to update the route.');drawMap();
}

function loadMap(value,name){
  map=structuredClone({grid:value.grid,start:value.start,goal:value.goal});original=structuredClone(map);
  cursor=[...map.start];$('map-title').textContent=name||'Imported map';
  $('scenario-note').textContent=[value.description,value.takeaway].filter(Boolean).join(' ');$('scenario-note').hidden=!$('scenario-note').textContent;
  $('map-size').textContent=`${map.grid.length} × ${map.grid[0].length}`;
  $('map-json').value=pretty(map);invalidateMap();
}

function scheduleDraw(){
  if(drawFrame)return;
  drawFrame=requestAnimationFrame(()=>{drawFrame=0;drawMap();});
}

function drawMap(){
  if(!map)return;
  const canvas=$('route-canvas'),width=canvas.parentElement.clientWidth;
  if(width<1)return;
  const rows=map.grid.length,cols=map.grid[0].length;
  const absoluteTop=canvas.getBoundingClientRect().top+scrollY;
  const heightLimit=Math.min(440,Math.max(168,innerHeight-absoluteTop-32));
  const height=Math.max(168,Math.min(heightLimit,(width-16)*rows/cols+16));
  const cell=Math.min((width-16)/cols,(height-16)/rows);
  const left=(width-cell*cols)/2,top=(height-cell*rows)/2;
  mapView={width,height,cell,left,top,rows,cols};
  const dpr=devicePixelRatio||1;
  canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);
  canvas.style.height=height+'px';
  Object.assign(canvas.dataset,{gridLeft:left,gridTop:top,cellSize:cell,rows,columns:cols,viewWidth:width,viewHeight:height});
  const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.fillStyle='#141414';ctx.fillRect(0,0,width,height);
  const traced=new Set((result?.trace||[]).slice(0,Number($('trace-step').value)).map(e=>e.node.join(',')));
  const path=new Set((result?.path||[]).map(p=>p.join(',')));
  for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){
    const v=map.grid[r][c],key=`${r},${c}`,x=left+c*cell,y=top+r*cell;
    ctx.fillStyle=v===0?'#080808':traced.has(key)?'#193047':v>1?'#32302a':'#222222';
    if(path.has(key))ctx.fillStyle='#0969da';
    ctx.fillRect(x,y,cell,cell);ctx.strokeStyle='#414141';ctx.lineWidth=.6;ctx.strokeRect(x,y,cell,cell);
    const isStart=same([r,c],map.start),isGoal=same([r,c],map.goal);
    if(isStart||isGoal){
      ctx.fillStyle='#f3f3f5';ctx.fillRect(x+1,y+1,Math.max(.5,cell-2),Math.max(.5,cell-2));
      if(cell>=12){ctx.fillStyle='#0f0f0f';ctx.font=`700 ${Math.max(8,Math.min(16,cell*.55))}px system-ui`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(isStart&&isGoal?'S/G':isStart?'S':'G',x+cell/2,y+cell/2);}
    }else if(cell>=14&&v>0){
      ctx.fillStyle=path.has(key)?'white':'#c9cdd3';ctx.font=`${Math.min(13,cell*.5)}px system-ui`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(v,x+cell/2,y+cell/2);
    }
  }
  ctx.strokeStyle='#e9b86b';ctx.lineWidth=cell>=8?2:1;
  ctx.strokeRect(left+cursor[1]*cell+1,top+cursor[0]*cell+1,Math.max(.5,cell-2),Math.max(.5,cell-2));
  $('cell-info').textContent=`Cell [${cursor.join(', ')}] · ${map.grid[cursor[0]][cursor[1]]===0?'wall':`entry cost ${map.grid[cursor[0]][cursor[1]]}`} · arrows move, Space edits.`;
  canvas.setAttribute('aria-label',`${rows} by ${cols} weighted grid. Cursor [${cursor}]. Start [${map.start}], goal [${map.goal}]. Arrow keys move; Space or Enter applies edit mode.`);
}

function applyEdit(){
  if(!map)return;
  const tool=$('paint').value;
  if(tool==='inspect'){drawMap();return;}
  if(tool==='start'||tool==='goal'){
    if(map.grid[cursor[0]][cursor[1]]===0){status('Place endpoints on a traversable cell.',true);return;}
    map[tool]=[...cursor];
  }else{
    if(tool==='0'&&(same(cursor,map.start)||same(cursor,map.goal))){status('Move the endpoint before making its cell a wall.',true);return;}
    map.grid[cursor[0]][cursor[1]]=Number(tool);
  }
  $('map-json').value=pretty(map);invalidateMap();
}

$('route-canvas').addEventListener('pointerdown',e=>{
  if(!map||!mapView)return;
  const box=e.currentTarget.getBoundingClientRect(),v=mapView;
  const x=(e.clientX-box.left)*v.width/box.width-v.left;
  const y=(e.clientY-box.top)*v.height/box.height-v.top;
  if(x<0||y<0||x>=v.cols*v.cell||y>=v.rows*v.cell){status('Select a cell inside the grid.');return;}
  cursor=[Math.floor(y/v.cell),Math.floor(x/v.cell)];
  e.currentTarget.focus({preventScroll:true});applyEdit();
});
$('route-canvas').addEventListener('keydown',e=>{
  if(!map)return;
  const directions={ArrowUp:[-1,0],ArrowDown:[1,0],ArrowLeft:[0,-1],ArrowRight:[0,1]};
  if(directions[e.key]){e.preventDefault();const d=directions[e.key];cursor=[Math.max(0,Math.min(map.grid.length-1,cursor[0]+d[0])),Math.max(0,Math.min(map.grid[0].length-1,cursor[1]+d[1]))];drawMap();}
  else if(e.key===' '||e.key==='Enter'){e.preventDefault();applyEdit();}
});
$('trace-step').addEventListener('input',()=>{$('trace-count').textContent=$('trace-step').value;drawMap();});
$('scenario').addEventListener('change',()=>{const s=scenarios[Number($('scenario').value)];loadMap(s,scenarioName(s));});
$('algorithm').addEventListener('change',invalidateMap);
$('reset-map').addEventListener('click',()=>loadMap(original,$('map-title').textContent));
$('export-map').addEventListener('click',()=>{if(map)download('route-map.json',pretty(map));});

function showRoute(data,all){
  result=data;$('route-result').replaceChildren();
  metrics($('route-result'),[['Cost',data.reachable?fmt(data.cost,0):'No route'],['Steps',data.steps===null?'—':fmt(data.steps,0)],['Expanded',fmt(data.expanded,0)],['Runtime',fmt(data.runtime_ms,3)+' ms']]);
  $('route-result').append(el('p',`${algorithmName(data.algorithm)} · peak heap ${data.heap_peak} · trace recording on`,'muted small'));
  $('route-summary').textContent=data.reachable?`${algorithmName(data.algorithm)} · cost ${fmt(data.cost,0)} · ${fmt(data.steps,0)} steps`:'No route connects these endpoints.';
  $('comparison').replaceChildren();$('comparison').hidden=!all;
  if(all){
    $('comparison').append(el('p',data.reachable?'Both algorithms agree on the minimum cost.':'Both algorithms found no route.','small'));
    const wrap=el('div',undefined,'table-wrap');
    table(wrap,['Method','Cost','Expanded','ms'],all.results.map(r=>[algorithmName(r.algorithm),r.cost===null?'—':fmt(r.cost,0),r.expanded,fmt(r.runtime_ms,3)]));
    $('comparison').append(wrap);
  }
  $('trace-step').max=data.trace.length;$('trace-step').value=0;$('trace-step').disabled=data.trace.length===0;$('trace-count').textContent='0';
  $('trace-note').textContent=`${data.trace.length} recorded expansions${data.trace_truncated?' · recording truncated; search completed':''}. Move the slider to inspect them.`;
  table($('path-table'),['Step','Row','Column','Entry cost'],data.path.map((p,i)=>[i,p[0],p[1],i===0?0:map.grid[p[0]][p[1]]]));
  status(data.reachable?'Route ready. Edit a cell or compare algorithms.':'No route found. Open a passage or move the endpoints.');drawMap();
}

async function runRoute(compare=false){
  const revision=mapRevision,snapshot=structuredClone(map);
  const payload={...snapshot,trace_limit:512,...(!compare?{algorithm:$('algorithm').value}:{})};
  const response=await request(compare?'/api/compare':'/api/solve',payload);
  if(revision!==mapRevision){status('Inputs changed during the request. Run the search again.');return;}
  const data=compare?response.data.results.find(x=>x.algorithm===$('algorithm').value):response.data;
  showRoute(data,compare?response.data:null);
}
$('solve').addEventListener('click',()=>busy($('solve'),()=>runRoute(false),'Finding route…'));
$('compare').addEventListener('click',()=>busy($('compare'),()=>runRoute(true),'Comparing algorithms…'));
$('map-json').addEventListener('input',()=>{mapDraftRevision++;status('JSON draft changed. Validate it to apply the map; the editor map is unchanged.');});
$('import-map').addEventListener('click',()=>busy($('import-map'),async()=>{
  const mapAtStart=mapRevision,draftAtStart=mapDraftRevision,importNumber=++mapImportRevision,draft=$('map-json').value;
  const current=()=>mapAtStart===mapRevision&&draftAtStart===mapDraftRevision&&importNumber===mapImportRevision&&$('map-json').value===draft;
  let value;try{value=JSON.parse(draft);}catch{throw new Error('Map JSON is invalid.');}
  try{await request('/api/solve',{...value,trace_limit:0});}
  catch(error){if(current())throw error;return;}
  if(!current())return;
  loadMap(value,'Imported map');
  status('Map validated. Run a search to inspect its route.');
},'Validating map…'));
new ResizeObserver(scheduleDraw).observe($('route-canvas').parentElement);
addEventListener('resize',scheduleDraw);

async function initProject(){
  scenarios=(await request('/api/presets')).data.scenarios;$('scenario').replaceChildren();
  scenarios.forEach((s,i)=>{const option=el('option',({'campus':'Campus','weighted-detour':'Detour','unreachable':'Closed','open':'Open'}[s.id]||s.name));option.value=i;$('scenario').append(option);});
  loadMap(scenarios[0],scenarioName(scenarios[0]));
  const benchmark=(await request('/api/benchmark')).data;$('benchmark-json').textContent=pretty(benchmark);
  if(benchmark.rows)table($('benchmark-table'),['Family','Grid','Seed','Algorithm','Cost','Expanded','Median ms'],benchmark.rows.map(r=>[r.family,r.size,r.seed,algorithmName(r.algorithm),r.cost??'Unreachable',r.expanded,fmt(r.median_ms,3)]));
  else $('benchmark-table').textContent=benchmark.message||'No recorded benchmark.';
  await setupEvidence({configuration:benchmark.configuration,environment:benchmark.environment,source_sha256:benchmark.source_sha256,protocol_sha256:benchmark.protocol_sha256,limitations:benchmark.limitations});
  await runRoute(false);
}
window.routeLabMap=()=>map?structuredClone(map):null;
window.routeLabLoadMap=(value,name)=>{loadMap(value,name);location.hash='workspace';};
initialize();
