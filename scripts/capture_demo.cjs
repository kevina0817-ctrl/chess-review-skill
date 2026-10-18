// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Capture only clearly labeled fictional demo data.
const fs=require('fs'),path=require('path'),assert=require('assert'),{pathToFileURL}=require('url');
const {chromium}=require(process.env.CHESS_REVIEW_PLAYWRIGHT||'playwright');
(async()=>{
 const [input,output]=process.argv.slice(2);if(!input)throw Error('Usage: node scripts/capture_demo.cjs demo/common-leaks.html [output-directory]');
 const out=path.resolve(output||path.join(__dirname,'../docs/screenshots'));fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.CHESS_REVIEW_BROWSER?{executablePath:process.env.CHESS_REVIEW_BROWSER}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.context().setOffline(true);
  await page.goto(pathToFileURL(path.resolve(input)).href);await page.evaluate(()=>document.fonts.ready);
  assert(await page.locator('#demo-notice').isVisible(),'Capture only the labeled synthetic demonstration');
  await page.screenshot({path:path.join(out,'v3.2-common-leaks-overview.png')});
  await page.locator('#comparison').screenshot({path:path.join(out,'common-leaks-comparison.png')});
  await page.locator('#positive-nav').click();await page.evaluate(()=>scrollTo(0,0));
  await page.screenshot({path:path.join(out,'v3.2-growth.png'),fullPage:true});
  assert.deepEqual(errors,[]);console.log(JSON.stringify({captured:3,source:path.resolve(input),output:out,synthetic:true}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
