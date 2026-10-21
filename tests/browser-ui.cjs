/* Optional browser regression: npm install --no-save --no-package-lock playwright@1.62.1 */
async function checkUi(page) {
  const checks=[],viewports=[];
  const ok=(condition,name)=>{if(!condition)throw new Error(name);checks.push(name);};
  const base='http://127.0.0.1:8767/?regression='+Date.now();
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  async function ready(){await page.locator('#route-result .metrics').waitFor();}
  async function run(button,endpoint){
    const [response]=await Promise.all([page.waitForResponse(r=>r.url().endsWith(endpoint)&&r.request().method()==='POST'),page.locator(button).click()]);
    if(!response.ok())throw new Error(await response.text());
    await page.waitForFunction(selector=>!document.querySelector(selector).disabled,button);
    return response.json();
  }
  async function clickCell(row,col){
    const geometry=await page.locator('#route-canvas').evaluate(canvas=>{
      const b=canvas.getBoundingClientRect(),d=canvas.dataset;
      return{left:+d.gridLeft,top:+d.gridTop,cell:+d.cellSize,width:+d.viewWidth,height:+d.viewHeight,cssWidth:b.width,cssHeight:b.height};
    });
    await page.locator('#route-canvas').click({position:{x:(geometry.left+(col+.5)*geometry.cell)*geometry.cssWidth/geometry.width,y:(geometry.top+(row+.5)*geometry.cell)*geometry.cssHeight/geometry.height}});
    ok((await page.locator('#cell-info').innerText()).includes(`Cell [${row}, ${col}]`),`Pointer maps to cell ${row},${col}`);
  }
  for(const [width,height] of [[319,672],[375,812],[768,1024],[1280,800]]){
    await page.setViewportSize({width,height});await page.goto(base);await ready();
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    const m=await page.evaluate(()=>{
      const c=document.querySelector('#route-canvas'),b=c.getBoundingClientRect(),d=c.dataset;
      return{width:innerWidth,height:innerHeight,primary:document.querySelector('#solve').getBoundingClientRect().width,secondary:document.querySelector('#compare').getBoundingClientRect().width,canvasTop:b.top,canvasBottom:b.bottom,overflow:document.documentElement.scrollWidth>innerWidth,cellWidth:+d.cellSize*b.width/+d.viewWidth,cellHeight:+d.cellSize*b.height/+d.viewHeight,summary:document.querySelector('#route-summary').textContent};
    });
    ok(m.primary>=112&&m.secondary>=112,`Primary buttons fit at ${width}`);
    ok(m.canvasTop<=550&&m.canvasBottom<=height-4,`Entire default map fits first screen at ${width}`);
    ok(!m.overflow&&Math.abs(m.cellWidth/m.cellHeight-1)<.015,`No overflow and square rendered cells at ${width}`);
    ok(m.summary.includes('cost 26')&&await page.locator('#status').isVisible(),`Cost and status visible at ${width}`);
    for(const [r,c] of [[0,0],[0,17],[11,0],[11,17]])await clickCell(r,c);
    for(const tab of await page.locator('[data-nav]').all()){
      await tab.click();ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&scrollY===0),`Tab fits and starts at top at ${width}`);
    }
    viewports.push(m);
  }
  await page.setViewportSize({width:319,height:672});await page.goto(base);await ready();
  await page.locator('#paint').selectOption('9');await clickCell(0,0);
  let map=JSON.parse(await page.locator('#map-json').inputValue());
  ok(map.grid[0][0]===9&&(await page.locator('#route-summary').innerText()).includes('Inputs changed'),'Editing updates JSON and invalidates result');
  const before=JSON.stringify(map);await page.locator('#route-canvas').click({position:{x:2,y:2}});
  ok(JSON.stringify(JSON.parse(await page.locator('#map-json').inputValue()))===before,'Canvas padding click does not edit a cell');
  await page.locator('#paint').selectOption('3');await page.locator('#route-canvas').press('ArrowRight');await page.locator('#route-canvas').press('Space');
  map=JSON.parse(await page.locator('#map-json').inputValue());ok(map.grid[0][1]===3,'Keyboard editing after resize');
  await page.getByRole('button',{name:'Reset map',exact:true}).click();
  let data=await run('#solve','/api/solve');ok(data.cost===26,'Reset and recalculate original route');
  await page.locator('#scenario').selectOption('1');data=await run('#compare','/api/compare');
  ok(data.costs_agree&&data.results.every(r=>r.cost===6&&r.steps===6),'Weighted detour comparison cost6, steps6');
  ok(await page.locator('#comparison table tbody tr').count()===2,'Readable comparison has both algorithms');
  await page.locator('#trace-step').press('ArrowRight');ok(await page.locator('#trace-count').innerText()==='1','Expansion trace slider');
  await page.locator('#scenario').selectOption('2');data=await run('#solve','/api/solve');ok(!data.reachable&&data.cost===null,'Unreachable result is explained');
  await page.getByText('Map rules and JSON import',{exact:true}).click();
  await page.locator('#map-json').fill('{bad json');await page.locator('#import-map').click();
  ok(await page.locator('#status.error').isVisible(),'Invalid map import has a visible error');
  await page.locator('#map-json').fill(JSON.stringify({grid:[[1]],start:[0,0],goal:[0,0],algorithm:'astar'}));
  await run('#import-map','/api/solve');data=await run('#compare','/api/compare');
  ok(data.results.every(r=>r.cost===0&&r.path.length===1),'Singleton map and imported algorithm compare correctly');
  await page.locator('#map-json').fill(JSON.stringify({grid:[[1,1,1,1,1,1,1,1]],start:[0,0],goal:[0,7]}));
  await run('#import-map','/api/solve');await page.locator('#paint').selectOption('inspect');await clickCell(0,7);
  ok((await page.locator('#cell-info').innerText()).includes('Cell [0, 7]'),'Thin map pointer geometry');
  await page.getByRole('link',{name:'API',exact:true}).click();
  await run('#send-api','/api/compare');ok(await page.locator('#http-status').innerText()==='HTTP 200','API explorer real successful request');
  await page.locator('#api-body').fill('{}');await page.locator('#send-api').click();
  await page.waitForFunction(()=>!document.querySelector('#send-api').disabled);
  ok(await page.locator('#http-status').innerText()==='HTTP 400'&&await page.locator('#status.error').isVisible(),'API validation response and visible error');
  ok(errors.length===0,'No JavaScript page errors');
  return{status:'passed',count:checks.length,checks,viewports};
}
module.exports=checkUi;
if(require.main===module){
  (async()=>{
    const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
    const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_EXECUTABLE?{executablePath:process.env.PLAYWRIGHT_EXECUTABLE}:{})});
    try{console.log(JSON.stringify(await checkUi(await browser.newPage()),null,2));}finally{await browser.close();}
  })().catch(error=>{console.error(error);process.exitCode=1;});
}
