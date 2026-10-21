/* Real frontend regression for stale map imports. The service is not mutated. */
module.exports=async function(page,{base='http://127.0.0.1:8767'}={}) {
  const cases=[];const check=(ok,label)=>{if(!ok)throw new Error(label);cases.push(label);};
  const imported={grid:[[1,1,1],[1,1,1]],start:[0,0],goal:[1,2]};
  const alternate=JSON.stringify({...imported,goal:[0,2]});
  async function start() {
    await page.goto(base+'/?test=import-'+Date.now()+'#workspace');
    await page.locator('#status').filter({hasText:'Route ready'}).waitFor();
    await page.locator('details').filter({has:page.locator('#map-json')}).locator('summary').click();
    await page.locator('#map-json').fill(JSON.stringify(imported));
    let release,entered;const gate=new Promise(r=>release=r),arrival=new Promise(r=>entered=r);
    const hold=async route=>{entered();await gate;await route.continue();};
    await page.route('**/api/solve',hold);await page.locator('#import-map').click();await arrival;
    return {release,hold};
  }
  let held=await start();await page.locator('#scenario').selectOption('1');
  const expected=await page.locator('#map-json').inputValue(),title=await page.locator('#map-title').textContent();
  held.release();await page.waitForResponse(r=>r.url().endsWith('/api/solve'));await page.waitForFunction(()=>!document.querySelector('#import-map').disabled);
  check(await page.locator('#map-json').inputValue()===expected&&await page.locator('#map-title').textContent()===title,'late import cannot overwrite a newer scenario');
  await page.unroute('**/api/solve',held.hold);
  held=await start();await page.locator('#map-json').fill(alternate);held.release();
  await page.waitForFunction(()=>!document.querySelector('#import-map').disabled);
  check(await page.locator('#map-json').inputValue()===alternate,'late import preserves a newer JSON draft');
  check(await page.locator('#map-title').textContent()!=='Imported map','editing only the draft does not commit the pending import');
  await page.unroute('**/api/solve',held.hold);
  held=await start();await page.locator('#map-json').fill(alternate);await page.locator('#map-json').fill(JSON.stringify(imported));held.release();
  await page.waitForFunction(()=>!document.querySelector('#import-map').disabled);
  check(await page.locator('#map-title').textContent()!=='Imported map','editing JSON away and back still cancels the older validation');
  await page.unroute('**/api/solve',held.hold);
  await page.goto(base+'/?test=import-error-'+Date.now()+'#workspace');await page.locator('#status').filter({hasText:'Route ready'}).waitFor();
  await page.locator('details').filter({has:page.locator('#map-json')}).locator('summary').click();await page.locator('#map-json').fill(JSON.stringify(imported));
  let failRelease,failEntered;const failedGate=new Promise(r=>failRelease=r),failedEntered=new Promise(r=>failEntered=r);
  const fail=async route=>{failEntered();await failedGate;await route.fulfill({status:400,json:{error:'Old import is invalid'}});};
  await page.route('**/api/solve',fail);await page.locator('#import-map').click();await failedEntered;await page.locator('#scenario').selectOption('2');const currentStatus=await page.locator('#status').textContent();failRelease();
  await page.waitForFunction(()=>!document.querySelector('#import-map').disabled);
  check(await page.locator('#status').textContent()===currentStatus,'stale import failure cannot replace the newer status');
  await page.unroute('**/api/solve',fail);
  await page.locator('#map-json').fill(JSON.stringify(imported));await page.locator('#import-map').click();await page.locator('#status').filter({hasText:'Map validated'}).waitFor();
  check(await page.locator('#map-title').textContent()==='Imported map','current successful import still commits');
  check(JSON.stringify(JSON.parse(await page.locator('#map-json').inputValue()))===JSON.stringify(imported),'validated import preserves its exact map');
  return {checks:cases.length,cases};
};
