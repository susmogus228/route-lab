'use strict';
/* The Lab displays Python responses; it never estimates traffic or travel time. */
(() => {
  let presets=[], current=null, title='', zone=[], mode='threshold', version=0;
  let sensitivity=null, closure=null, selected=null, replacement=null, cursor=[0,0];
  let geometry=null, previousClosure=null, selectedVersion=0, drawing=false;
  const canvas=$('lab-canvas');
  const pointKey=p=>p.join(',');
  const mapOnly=value=>structuredClone({grid:value.grid,start:value.start,goal:value.goal});
  const isEndpoint=p=>same(p,current.start)||same(p,current.goal);
  const note=(message,error=false)=>{
    $('lab-status').textContent=message;$('lab-status').classList.toggle('error',error);
    $('lab-status').setAttribute('role',error?'alert':'status');
  };
  function clearResults(){
    version++;selectedVersion++;sensitivity=null;closure=null;selected=null;replacement=null;
    $('lab-layout').removeAttribute('aria-busy');
    $('lab-cost').disabled=true;$('lab-export').disabled=true;$('lab-repair').disabled=true;
    for(const id of ['lab-threshold-metrics','lab-closure-metrics','lab-levels','lab-closure-table','lab-cost-chart'])$(id).replaceChildren();
    for(const id of ['lab-threshold-insight','lab-closure-insight','lab-before-after','lab-closure-selection'])$(id).textContent='';
  }
  function setMode(value,run=true){
    mode=value;clearResults();
    $('lab-threshold-panel').hidden=mode!=='threshold';$('lab-closures-panel').hidden=mode!=='closures';
    $('lab-threshold-mode').setAttribute('aria-pressed',String(mode==='threshold'));
    $('lab-closures-mode').setAttribute('aria-pressed',String(mode==='closures'));
    $('lab-endpoint').textContent=`POST /api/${mode==='threshold'?'threshold':'closures'}`;
    draw();if(run)analyze();
  }
  function load(value,name,custom=false){
    if(!custom)previousClosure=null;
    else if(closure)previousClosure={result:closure,map:mapOnly(current)};
    current=mapOnly(value);title=name;cursor=[...current.start];
    if(custom){if(!$('lab-scenario').querySelector('[value=editor]')){const option=el('option','Editor map');option.value='editor';option.disabled=true;$('lab-scenario').append(option);}$('lab-scenario').querySelector('[value=editor]').textContent=name;$('lab-scenario').value='editor';}
    zone=structuredClone(value.traffic_cells||[]);
    $('lab-repair').hidden=value.id!=='bridge-bottleneck';
    $('lab-title').textContent=title;$('lab-size').textContent=`${current.grid.length} × ${current.grid[0].length}`;
    $('lab-description').textContent=[value.description,value.takeaway].filter(Boolean).join(' ')||'Test your editor map against congestion and independent single-cell closures.';
    $('lab-cost').value=1;$('lab-cost-value').textContent='1';
    setMode(zone.length?'threshold':'closures');
  }
  async function analyze(){
    if(!current)return;
    const token=version, snapshot=mapOnly(current), operation=mode;
    draw();
    if(mode==='threshold'&&!zone.length){note('Choose a traversable cell, excluding start and goal, to test costs 1–9.');return;}
    note(mode==='threshold'?'Calculating all nine entry costs…':'Testing independent single-cell closures…');
    $('lab-layout')?.setAttribute('aria-busy','true');
    try{
      const response=await request(mode==='threshold'?'/api/threshold':'/api/closures',mode==='threshold'?{...snapshot,cells:structuredClone(zone)}:snapshot);
      if(token!==version||operation!==mode)return;
      $('lab-export').disabled=false;
      if(mode==='threshold'){
        sensitivity=response.data;$('lab-cost').disabled=false;
        table($('lab-levels'),['Zone cost','Optimal','Keep reference','Steps'],sensitivity.levels.map(r=>[r.entry_cost,r.cost,r.reference_cost,r.steps]));
        renderThreshold();note('Nine costs calculated. Move the slider or select a different cell.');
      }else{
        closure=response.data;renderClosures();
        const first=closure.cells.find(c=>c.critical)||[...closure.cells].sort((a,b)=>(b.delta||0)-(a.delta||0))[0];
        note(`${closure.tested_count} independent closures tested. Select a cell to inspect its effect.`);
        if(first)await selectClosure(first.cell);
      }
    }catch(error){if(token===version)note(error.message,true);}
    finally{if(token===version)$('lab-layout')?.removeAttribute('aria-busy');}
  }
  function renderThreshold(){
    if(!sensitivity)return;
    const value=Number($('lab-cost').value), row=sensitivity.levels.find(r=>r.entry_cost===value);
    $('lab-cost-value').textContent=String(value);
    metrics($('lab-threshold-metrics'),[['Optimal cost',row.cost===null?'No route':fmt(row.cost,0)],['Steps',row.steps===null?'—':fmt(row.steps,0)],['Keep reference',row.reference_cost===null?'—':fmt(row.reference_cost,0)],['Switch at',sensitivity.first_switch_cost===null?'None in 1–9':fmt(sensitivity.first_switch_cost,0)]]);
    let text;
    if(!row.reachable)text='These endpoints are disconnected. Changing positive entry costs cannot open a wall.';
    else if(row.reference_optimal)text=`At zone cost ${value}, the cost-1 reference route remains optimal. ${sensitivity.first_switch_cost===null?'It stays optimal across all nine tested costs.':`It first loses optimality at cost ${sensitivity.first_switch_cost}.`}`;
    else text=`At zone cost ${value}, the optimal route costs ${row.cost}. Keeping the reference route costs ${row.reference_cost}: ${row.reference_cost-row.cost} more cost ${row.reference_cost-row.cost===1?'unit':'units'}.`;
    $('lab-threshold-insight').textContent=text;drawChart();draw();
  }
  function drawChart(){
    const wrap=$('lab-cost-chart');wrap.replaceChildren();
    const rows=sensitivity.levels.filter(r=>r.reachable);if(!rows.length)return;
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
    svg.setAttribute('viewBox','0 0 340 168');svg.setAttribute('role','img');
    svg.setAttribute('aria-label',`Optimal and reference route costs at entry costs 1 through 9. First strict loss of optimality: ${sensitivity.first_switch_cost??'none'}. Exact values follow in the table.`);
    const max=Math.max(1,...rows.map(r=>r.reference_cost),...rows.map(r=>r.cost));
    const x=v=>30+(v-1)*36, y=v=>136-v/max*112;
    const line=(attributes)=>{const n=document.createElementNS(ns,'line');for(const[k,v]of Object.entries(attributes))n.setAttribute(k,v);svg.append(n);};
    line({x1:30,x2:318,y1:136,y2:136,stroke:'#61656b'});
    for(const key of ['reference_cost','cost']){
      const poly=document.createElementNS(ns,'polyline');poly.setAttribute('points',rows.map(r=>`${x(r.entry_cost)},${y(r[key])}`).join(' '));poly.setAttribute('fill','none');poly.setAttribute('stroke',key==='cost'?'#258dff':'#b8bec8');poly.setAttribute('stroke-width','2');if(key==='reference_cost')poly.setAttribute('stroke-dasharray','5 4');svg.append(poly);
    }
    const text=(xv,yv,value)=>{const n=document.createElementNS(ns,'text');n.setAttribute('x',xv);n.setAttribute('y',yv);n.setAttribute('fill','#b8bec8');n.setAttribute('font-size','11');n.setAttribute('text-anchor','middle');n.textContent=value;svg.append(n);};
    for(let v=1;v<=9;v++)text(x(v),154,String(v));text(14,26,String(max));text(14,140,'0');
    const active=rows.find(r=>r.entry_cost===Number($('lab-cost').value));
    if(active){const dot=document.createElementNS(ns,'circle');dot.setAttribute('cx',x(active.entry_cost));dot.setAttribute('cy',y(active.cost));dot.setAttribute('r','4');dot.setAttribute('fill','#fff');svg.append(dot);}
    wrap.append(svg);
  }
  function renderClosures(){
    $('lab-repair').disabled=false;
    metrics($('lab-closure-metrics'),[['Baseline cost',closure.baseline.cost===null?'No route':fmt(closure.baseline.cost,0)],['Cells tested',fmt(closure.tested_count,0)],['Disconnecting',fmt(closure.critical_count,0)],['Max added cost',closure.worst_delta===null?'—':`+${closure.worst_delta}`]]);
    $('lab-closure-insight').textContent=!closure.baseline.reachable?'The original map is already disconnected. These tests do not count existing disconnection as a new failure.':!closure.tested_count?'No eligible cells remain: start and goal are excluded from closures.':closure.critical_count?`${closure.critical_count} individual closures disconnect this start and goal. The × markers identify those cells.`:'A route survives each tested single-cell closure. Combined closures and uncertain travel costs are outside this test.';
    if(previousClosure&&same(previousClosure.map.start,current.start)&&same(previousClosure.map.goal,current.goal)){
      $('lab-before-after').textContent=`Previous map: ${previousClosure.result.critical_count} disconnecting cells out of ${previousClosure.result.tested_count}. Current: ${closure.critical_count} out of ${closure.tested_count}. Maps may have different numbers of open cells.`;
    }
    const rows=closure.cells.map(r=>[`[${r.cell.join(', ')}]`,r.critical?'Disconnects':r.cost===null?'No route':`Cost ${r.cost}`,r.delta===null?'—':`+${r.delta}`]);
    table($('lab-closure-table'),['Closed cell','Outcome','Added cost'],rows);
    const elements=$('lab-closure-table').querySelectorAll('tbody tr');
    elements.forEach((tr,i)=>{const td=tr.firstChild,button=el('button',td.textContent);button.type='button';button.setAttribute('aria-label',`Inspect closure at ${closure.cells[i].cell.join(', ')}`);button.addEventListener('click',()=>selectClosure(closure.cells[i].cell));td.replaceChildren(button);});
    draw();
  }
  async function selectClosure(cell){
    if(!closure)return;
    const item=closure.cells.find(r=>same(r.cell,cell));if(!item)return;
    selected=item;replacement=null;cursor=[...cell];const token=version,selection=++selectedVersion;
    $('lab-closure-selection').textContent=`Closing [${cell.join(', ')}]: ${item.critical?'no route remains':!item.reachable?'still no route':`cost ${item.cost}, ${item.delta===0?'no added cost':`+${item.delta} from baseline`}`}.`;
    draw();
    if(!item.reachable)return;
    const changed=mapOnly(current);changed.grid[cell[0]][cell[1]]=0;
    try{const response=await request('/api/solve',{...changed,algorithm:'astar',trace_limit:0});if(token!==version||selection!==selectedVersion)return;replacement=response.data;draw();}
    catch(error){if(token===version&&selection===selectedVersion)note(error.message,true);}
  }
  function chooseCell(){
    if(!current)return;
    if(current.grid[cursor[0]][cursor[1]]===0||isEndpoint(cursor)){note('Select an open cell other than start or goal.');draw();return;}
    if(mode==='closures'){if(closure)selectClosure(cursor);else note('Wait for the closure analysis to finish.');}
    else{zone=[[...cursor]];clearResults();analyze();}
  }
  function draw(){
    if(!current||drawing)return;drawing=true;
    requestAnimationFrame(()=>{drawing=false;paint();});
  }
  function paint(){
    const width=canvas.parentElement.clientWidth;if(!width||!current)return;
    const rows=current.grid.length,cols=current.grid[0].length;
    const height=Math.max(168,Math.min(400,(width-16)*rows/cols+16));
    const cell=Math.min((width-16)/cols,(height-16)/rows),left=(width-cell*cols)/2,top=(height-cell*rows)/2;
    geometry={width,height,cell,left,top,rows,cols};
    const dpr=devicePixelRatio||1;canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);canvas.style.height=height+'px';
    Object.assign(canvas.dataset,{gridLeft:left,gridTop:top,cellSize:cell,rows,columns:cols,viewWidth:width,viewHeight:height});
    const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#141414';ctx.fillRect(0,0,width,height);
    const level=sensitivity?.levels.find(r=>r.entry_cost===Number($('lab-cost').value));
    const route=mode==='threshold'?level?.path:selected?(replacement?.path||[]):closure?.baseline.path;
    const path=new Set((route||[]).map(pointKey)),zones=new Set(zone.map(pointKey));
    const outcomes=new Map((closure?.cells||[]).map(r=>[pointKey(r.cell),r]));
    for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){
      const p=[r,c],key=pointKey(p),outcome=outcomes.get(key),inZone=mode==='threshold'&&zones.has(key);
      const value=inZone?Number($('lab-cost').value):current.grid[r][c];
      const x=left+c*cell,y=top+r*cell,closed=mode==='closures'&&selected&&same(p,selected.cell);
      ctx.fillStyle=value===0||closed?'#080808':path.has(key)?'#0969da':mode==='closures'&&outcome?.critical?'#60451f':mode==='closures'&&outcome?.delta>0?'#393124':value>1?'#32302a':'#222222';
      ctx.fillRect(x,y,cell,cell);ctx.strokeStyle='#414141';ctx.lineWidth=.6;ctx.strokeRect(x,y,cell,cell);
      if(inZone){ctx.strokeStyle='#e9b86b';ctx.lineWidth=2;ctx.strokeRect(x+1,y+1,Math.max(.5,cell-2),Math.max(.5,cell-2));}
      const start=same(p,current.start),goal=same(p,current.goal);
      if(start||goal){ctx.fillStyle='#f3f3f5';ctx.fillRect(x+1,y+1,Math.max(.5,cell-2),Math.max(.5,cell-2));}
      if(cell>=14){
        const label=start&&goal?'S/G':start?'S':goal?'G':mode==='closures'&&outcome?.critical?'×':closed?'×':value===0?'':String(value);
        ctx.fillStyle=start||goal?'#0f0f0f':mode==='closures'&&outcome?.critical?'#ffe1a3':'#f3f3f5';ctx.textAlign='center';ctx.textBaseline='middle';ctx.font=`${Math.max(9,Math.min(16,cell*.45))}px system-ui`;ctx.fillText(label,x+cell/2,y+cell/2);
      }
    }
    ctx.strokeStyle='#f3f3f5';ctx.lineWidth=2;ctx.strokeRect(left+cursor[1]*cell+1,top+cursor[0]*cell+1,Math.max(.5,cell-2),Math.max(.5,cell-2));
    $('lab-cell-info').textContent=`Cell [${cursor.join(', ')}] · ${current.grid[cursor[0]][cursor[1]]===0?'wall':`base cost ${current.grid[cursor[0]][cursor[1]]}`} · arrows move, Enter selects.`;
    $('lab-legend').textContent=mode==='threshold'?'Outlined = cost zone · Blue = optimal route · S / G = endpoints':'× = disconnects · Warm cells = added cost · Blue = selected surviving route';
    canvas.setAttribute('aria-label',`${title}. ${rows} by ${cols}. Cursor ${cursor.join(', ')}. ${mode==='threshold'?'Select a cost zone':'Inspect a single closure'}. Use arrows and Enter. Exact results appear below in the table.`);
  }
  canvas.addEventListener('pointerdown',event=>{
    if(!geometry)return;const b=canvas.getBoundingClientRect(),v=geometry;
    const x=(event.clientX-b.left)*v.width/b.width-v.left,y=(event.clientY-b.top)*v.height/b.height-v.top;
    if(x<0||y<0||x>=v.cols*v.cell||y>=v.rows*v.cell)return;
    cursor=[Math.floor(y/v.cell),Math.floor(x/v.cell)];canvas.focus({preventScroll:true});chooseCell();
  });
  canvas.addEventListener('keydown',event=>{
    if(!current)return;const directions={ArrowUp:[-1,0],ArrowRight:[0,1],ArrowDown:[1,0],ArrowLeft:[0,-1]};
    if(directions[event.key]){event.preventDefault();const d=directions[event.key];cursor=[Math.max(0,Math.min(current.grid.length-1,cursor[0]+d[0])),Math.max(0,Math.min(current.grid[0].length-1,cursor[1]+d[1]))];draw();}
    else if(event.key==='Enter'||event.key===' '){event.preventDefault();chooseCell();}
  });
  $('lab-cost').addEventListener('input',renderThreshold);
  $('lab-threshold-mode').addEventListener('click',()=>setMode('threshold'));
  $('lab-closures-mode').addEventListener('click',()=>setMode('closures'));
  $('lab-scenario').addEventListener('change',()=>{const s=presets[Number($('lab-scenario').value)];load(s,s.name);});
  $('lab-use-editor').addEventListener('click',()=>{const value=window.routeLabMap();if(value)load(value,'Editor map',true);else note('Load an editor map first.',true);});
  $('lab-edit').addEventListener('click',()=>{if(current)window.routeLabLoadMap(current,title);});
  $('lab-bridge').addEventListener('click',()=>{const i=presets.findIndex(s=>s.id==='bridge-bottleneck');if(i>=0){$('lab-scenario').value=i;load(presets[i],presets[i].name);}});
  $('lab-repair').addEventListener('click',()=>{const fixed=mapOnly(current);fixed.grid[2][5]=1;load(fixed,'Bridge + second crossing',true);});
  $('lab-export').addEventListener('click',()=>download('route-lab-analysis.json',pretty({experiment:mode,map:current,cells:mode==='threshold'?zone:undefined,selected_entry_cost:Number($('lab-cost').value),selected_closure:selected?.cell,result:mode==='threshold'?sensitivity:closure})));
  addEventListener('resize',draw);addEventListener('hashchange',draw);new ResizeObserver(draw).observe(canvas.parentElement);
  function openExperiment(id){
    const index=presets.findIndex(value=>value.id===id);if(index<0)return;
    $('lab-scenario').value=index;load(presets[index],presets[index].name);
    if(id==='bridge-bottleneck'&&mode!=='closures')setMode('closures');
    location.hash='lab';routeTab();$('lab-title').focus({preventScroll:true});draw();
  }
  async function initializeLab(){
    $('experiment-congestion').disabled=true;$('experiment-closures').disabled=true;$('experiment-retry').hidden=true;
    $('experiment-status').hidden=false;$('experiment-status').textContent='Loading experiment maps…';$('experiment-status').setAttribute('role','status');
    try{
      presets=(await request('/api/presets')).data.scenarios;
      if(!presets.some(s=>s.id==='rush-hour')||!presets.some(s=>s.id==='bridge-bottleneck'))throw new Error('Required experiment maps are unavailable.');
      $('lab-scenario').replaceChildren();presets.forEach((s,i)=>{const option=el('option',s.name);option.value=i;$('lab-scenario').append(option);});
      const index=presets.findIndex(s=>s.id==='rush-hour');$('lab-scenario').value=index;load(presets[index],presets[index].name);
      $('experiment-congestion').disabled=false;$('experiment-closures').disabled=false;$('experiment-status').hidden=true;
    }catch(error){note(error.message,true);$('experiment-status').textContent='Experiment maps could not load. Retry to open the analyses.';$('experiment-status').setAttribute('role','alert');$('experiment-retry').hidden=false;}
  }
  $('experiment-congestion').addEventListener('click',()=>openExperiment('rush-hour'));
  $('experiment-closures').addEventListener('click',()=>openExperiment('bridge-bottleneck'));
  $('experiment-retry').addEventListener('click',initializeLab);
  initializeLab();
})();
