module.exports=async function(page,{base='http://127.0.0.1:8767'}={}) {
  const cases=[];const check=(ok,label)=>{if(!ok)throw new Error(label);cases.push(label);};
  await page.goto(base+'/?test=entries-'+Date.now()+'#workspace');
  await page.locator('#experiment-congestion').waitFor();await page.waitForFunction(()=>!document.querySelector('#experiment-congestion').disabled);
  const editor=await page.evaluate(()=>window.routeLabMap());
  await page.locator('#experiment-congestion').click();await page.locator('#lab-status').filter({hasText:'Nine costs calculated'}).waitFor();
  check(await page.locator('[data-panel=lab]').isVisible(),'first-screen congestion action opens the Lab');
  check(await page.locator('#lab-scenario option:checked').textContent()==='Rush hour','congestion action selects the intended experiment');
  check(await page.locator('#lab-title').evaluate(n=>document.activeElement===n),'experiment action moves keyboard focus to the destination heading');
  await page.locator('[data-nav=workspace]').click();await page.locator('#experiment-closures').click();
  await page.locator('#lab-status').filter({hasText:'independent closures tested'}).waitFor();
  check((await page.locator('#lab-title').textContent()).toLowerCase().includes('bridge'),'closure action selects the bridge experiment');
  check(await page.locator('#lab-closures-mode').getAttribute('aria-pressed')==='true','bridge entry uses closure analysis');
  check(JSON.stringify(await page.evaluate(()=>window.routeLabMap()))===JSON.stringify(editor),'experiment entry leaves the editor map intact');
  for(const width of [304,1280]) {
    await page.locator('[data-nav=workspace]').click();await page.setViewportSize({width,height:900});const actual=await page.evaluate(()=>innerWidth);
    if(Math.abs(actual-width)>1)await page.setViewportSize({width:Math.round(width*width/actual),height:900});
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'experiment links fit at CSS width '+width);
  }
  // Each preset request fails, including independent editor and Lab initialization.
  await page.route('**/api/presets',route=>route.fulfill({status:503,json:{error:'QA unavailable'}}));
  await page.goto(base+'/?test=entries-fail-'+Date.now()+'#workspace');await page.locator('#experiment-retry').waitFor();
  check(await page.locator('#experiment-congestion').isDisabled(),'unavailable presets disable experiment entry');
  await page.unroute('**/api/presets');await page.locator('#experiment-retry').click();
  await page.waitForFunction(()=>!document.querySelector('#experiment-congestion').disabled);
  check(await page.locator('#experiment-retry').isHidden(),'preset loading has a working retry');
  return {checks:cases.length,cases};
};
