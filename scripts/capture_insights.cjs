// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Capture only the public historical demo, never a user's private game.
const fs=require('fs'),path=require('path'),assert=require('assert'),{pathToFileURL}=require('url');
const {chromium}=require(process.env.CHESS_REVIEW_PLAYWRIGHT||'playwright');
(async()=>{
 const [source,output]=process.argv.slice(2);if(!source||!output)throw Error('Usage: node scripts/capture_insights.cjs demo-directory screenshot-directory');
 const demo=path.resolve(source),out=path.resolve(output);fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.CHESS_REVIEW_BROWSER?{executablePath:process.env.CHESS_REVIEW_BROWSER}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1650}}),errors=[],requests=[];page.on('pageerror',e=>errors.push(e.message));await page.route(/^https?:/,r=>{requests.push(r.request().url());return r.abort()});
  await page.goto(pathToFileURL(path.join(demo,'2026-09-24_Duke_Karl_and_Count_Isouard.html')).href);await page.locator('#board .square').last().waitFor();await page.evaluate(()=>document.fonts.ready);
  const d=await page.evaluate(()=>DATA);assert.equal(d.meta.white,'Paul Morphy');assert.equal(d.meta.black,'Duke Karl and Count Isouard');assert.equal(await page.locator('[id^="score-"],#phase-scores').count(),0);
  if(await page.evaluate(()=>document.documentElement.lang==='en'))assert(await page.evaluate(()=>!/[\u3400-\u9fff]/.test(document.documentElement.outerHTML)));
  await page.locator('#better').click();await page.locator('#next').click();await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(out,'review-overview.png')});
  await page.locator('.insights').screenshot({path:path.join(out,'v3-insights.png')});
  await page.setViewportSize({width:1440,height:1100});
  const i=await page.evaluate(()=>DATA.analytics.positions.findIndex(p=>p.forecast.some(f=>f.mate)));assert(i>=0);await page.locator('#eval-chart circle').nth(i).focus();await page.keyboard.press('Enter');await page.locator('#forecast-open').click();await page.locator('#next').click();await page.locator('#board').evaluate(el=>scrollTo(0,el.getBoundingClientRect().top+scrollY-100));await page.screenshot({path:path.join(out,'v3-threats.png')});
  await page.locator('#opening-learn summary').click();await page.locator('#opening-jump').click();await page.locator('#opening-learn').screenshot({path:path.join(out,'v3-opening.png')});
  await page.goto(pathToFileURL(path.join(demo,'index.html')).href);await page.frameLocator('#review-frame').locator('#stats-user [data-stat="moves"]').waitFor();await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(out,'library.png')});
  assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);console.log(JSON.stringify({captured:5,source:demo,output:out}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
