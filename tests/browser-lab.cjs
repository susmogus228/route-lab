/* Optional browser suite; uses the same Playwright runtime as browser-ui.cjs. */
async function checkLab(page) {
  const checks=[],viewports=[],errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const ok=(condition,name)=>{if(!condition)throw new Error(name);checks.push(name);};
  const base='http://127.0.0.1:8767/?revision=resilience';
  async function ready(){await page.locator('#lab-threshold-metrics .metrics').waitFor();}
  async function select(name){
    await page.locator('#lab-scenario').selectOption({label:name});
    await page.waitForFunction(()=>!document.querySelector('#lab-export').disabled);
  }
  async function cell(selector,row,col){
    const v=await page.locator(selector).evaluate(c=>{const b=c.getBoundingClientRect(),d=c.dataset;return{left:+d.gridLeft,top:+d.gridTop,cell:+d.cellSize,width:+d.viewWidth,height:+d.viewHeight,cw:b.width,ch:b.height};});
    await page.locator(selector).click({position:{x:(v.left+(col+.5)*v.cell)*v.cw/v.width,y:(v.top+(row+.5)*v.cell)*v.ch/v.height}});
  }
  for(const[width,height]of[[319,672],[375,812],[768,1024],[1280,800]]){
    await page.setViewportSize({width,height});await page.goto(base+'&viewport='+width+'&run='+Date.now()+'#lab');await ready();
    await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
    const shape=await page.evaluate(()=>{const c=document.querySelector('#lab-canvas'),b=c.getBoundingClientRect(),d=c.dataset;return{width:innerWidth,height:innerHeight,top:b.top,bottom:b.bottom,overflow:document.documentElement.scrollWidth>innerWidth,cellX:+d.cellSize*b.width/+d.viewWidth,cellY:+d.cellSize*b.height/+d.viewHeight,primary:document.querySelector('#lab-threshold-mode').getBoundingClientRect().width,secondary:document.querySelector('#lab-closures-mode').getBoundingClientRect().width};});
    ok(!shape.overflow,`Lab has no horizontal overflow at ${width}`);
    ok(shape.primary>=112&&shape.secondary>=112,`Lab mode controls fit at ${width}`);
    ok(Math.abs(shape.cellX/shape.cellY-1)<.015,`Lab cells remain square at ${width}`);
    ok(shape.top<height&&shape.bottom<=height,`Default experiment map fits first screen at ${width}`);
    ok(!(await page.locator('#status').isVisible()),`Editor status does not leak into Lab at ${width}`);
    await page.locator('#lab-cost').fill('2');
    ok((await page.locator('#lab-threshold-insight').innerText()).includes('Keeping the reference route costs 7'),'Exact cost7 reference versus cost6 optimum at '+width);
    viewports.push(shape);
  }
  ok(await page.locator('#lab-scenario option').count()===10,'Ten explained maps are available');
  ok(await page.locator('#lab-levels tbody tr').count()===9,'Nine backend-calculated levels have exact table rows');
  ok(await page.locator('#lab-cost-chart svg polyline').count()===2,'Chart shows measured optimum and reference costs');
  await page.locator('#lab-cost').fill('1');
  ok((await page.locator('#lab-threshold-insight').innerText()).includes('remains optimal'),'Reference route remains optimal at cost1');
  await page.locator('#lab-cost').press('ArrowRight');
  ok(await page.locator('#lab-cost-value').innerText()==='2','Keyboard slider selects a calculated level');
  await cell('#lab-canvas',1,2);
  await page.waitForFunction(()=>!document.querySelector('#lab-cost').disabled);
  ok((await page.locator('#lab-cell-info').innerText()).includes('[1, 2]'),'Pointer selects a new traffic zone');
  await page.locator('#lab-canvas').press('ArrowRight');await page.locator('#lab-canvas').press('Enter');
  await page.waitForFunction(()=>!document.querySelector('#lab-cost').disabled);
  ok((await page.locator('#lab-cell-info').innerText()).includes('[1, 3]'),'Keyboard selects a new traffic zone');
  await page.route('**/api/closures',async route=>{await new Promise(r=>setTimeout(r,200));await route.continue();});
  await page.locator('#lab-scenario').selectOption({label:'Bridge bottleneck'});
  ok(await page.locator('#lab-repair').isDisabled(),'Bridge repair waits for its measured baseline');
  await page.waitForFunction(()=>!document.querySelector('#lab-export').disabled);
  await page.unroute('**/api/closures');
  ok((await page.locator('#lab-closure-insight').innerText()).includes('3 individual'),'Bridge has three disconnecting cells');
  await cell('#lab-canvas',3,5);
  ok((await page.locator('#lab-closure-selection').innerText()).includes('Closing [3, 5]: no route remains'),'Selecting bridge explains the failed route');
  await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/solve')&&r.request().method()==='POST'),cell('#lab-canvas',0,0)]);
  ok((await page.locator('#lab-closure-selection').innerText()).includes('cost 8'),'Selecting harmless closure shows its surviving route');
  await page.locator('#lab-repair').click();await page.waitForFunction(()=>document.querySelector('#lab-closure-insight').textContent.includes('survives each'));
  ok((await page.locator('#lab-before-after').innerText()).includes('3 disconnecting cells out of 69. Current: 0 out of 70'),'One opened crossing removes single-closure disconnection in the measured map');
  const downloadEvent=page.waitForEvent('download');await page.locator('#lab-export').click();const download=await downloadEvent;
  ok(download.suggestedFilename()==='route-lab-analysis.json'&&await download.failure()===null,'Analysis JSON download completes');
  await select('Disconnected district');
  ok((await page.locator('#lab-closure-insight').innerText()).includes('already disconnected'),'Already unreachable map has an explicit explanation');
  ok((await page.locator('#lab-closure-metrics .metric').nth(2).innerText()).startsWith('0'),'Existing disconnection is not counted as new critical cells');
  await page.locator('#lab-threshold-mode').click();
  ok((await page.locator('#lab-status').innerText()).includes('Choose a traversable cell'),'Missing traffic zone prompts a valid selection');
  ok(!(await page.locator('#lab-layout').getAttribute('aria-busy')),'Changing to a mode without a zone clears loading state');
  await cell('#lab-canvas',0,1);await page.waitForFunction(()=>!document.querySelector('#lab-cost').disabled);
  ok((await page.locator('#lab-threshold-insight').innerText()).includes('cannot open a wall'),'Changing costs does not invent connectivity');
  // Prove a delayed closure result cannot replace a newly selected map.
  await page.route('**/api/closures',async route=>{await new Promise(r=>setTimeout(r,200));await route.continue();});
  await page.locator('#lab-scenario').selectOption({label:'Bridge bottleneck'});
  await page.locator('#lab-scenario').selectOption({label:'Disconnected district'});
  await page.waitForFunction(()=>document.querySelector('#lab-closure-insight').textContent.includes('already disconnected'));
  ok(await page.locator('#lab-title').innerText()==='Disconnected district','A delayed response cannot replace the current scenario');
  await page.unroute('**/api/closures');
  await select('Bridge bottleneck');
  await page.locator('#lab-edit').click();
  ok(page.url().endsWith('#workspace')&&(await page.locator('#map-title').innerText())==='Bridge bottleneck','Lab map opens in the working editor');
  await page.locator('#paint').selectOption('1');await cell('#route-canvas',2,5);
  await page.getByRole('link',{name:'Lab',exact:true}).click();await page.locator('#lab-use-editor').click();
  await page.waitForFunction(()=>document.querySelector('#lab-closure-insight').textContent.includes('survives each'));
  ok(await page.locator('#lab-title').innerText()==='Editor map','Edited map returns to Lab for a real recalculation');
  ok((await page.locator('#lab-before-after').innerText()).includes('Current: 0 out of 70'),'Editor repair reconciles with the shortcut experiment');
  // Larger maps remain valid for solving, but analysis has a smaller explicit bound.
  await page.getByRole('link',{name:'Route',exact:true}).click();
  await page.getByText('Map rules and JSON import',{exact:true}).click();
  await page.locator('#map-json').fill(JSON.stringify({grid:Array.from({length:17},()=>Array(17).fill(1)),start:[0,0],goal:[16,16]}));
  await page.locator('#import-map').click();await page.waitForFunction(()=>!document.querySelector('#import-map').disabled);
  await page.getByRole('link',{name:'Lab',exact:true}).click();await page.locator('#lab-use-editor').click();
  await page.waitForFunction(()=>document.querySelector('#lab-status').classList.contains('error'));
  ok((await page.locator('#lab-status').innerText()).includes('256 total grid cells'),'Oversized analysis shows the real backend validation limit');
  ok(await page.locator('#lab-export').isDisabled(),'Rejected map cannot export stale results');
  await page.getByRole('link',{name:'API',exact:true}).click();
  await page.locator('#endpoint').selectOption({label:'POST /api/threshold'});await page.locator('#send-api').click();
  await page.waitForFunction(()=>!document.querySelector('#send-api').disabled);
  ok(await page.locator('#http-status').innerText()==='HTTP 200'&&JSON.parse(await page.locator('#api-response').innerText()).first_switch_cost===2,'API explorer calls the threshold service');
  await page.locator('#endpoint').selectOption({label:'POST /api/closures'});await page.locator('#send-api').click();
  await page.waitForFunction(()=>!document.querySelector('#send-api').disabled);
  ok(await page.locator('#http-status').innerText()==='HTTP 200','API explorer calls the closure service');
  ok(errors.length===0,'Lab has no JavaScript page errors');
  return {status:'passed',count:checks.length,checks,viewports};
}
module.exports=checkLab;
if(require.main===module){
  (async()=>{const{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_EXECUTABLE?{executablePath:process.env.PLAYWRIGHT_EXECUTABLE}:{})});try{console.log(JSON.stringify(await checkLab(await browser.newPage()),null,2));}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
}
