#!/usr/bin/env node
// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Browser-level checks for the generated standalone review; no external requests needed.
const fs=require('fs');
const path=require('path');
const {pathToFileURL}=require('url');
const assert=require('assert');
let playwright;
try{playwright=require(process.env.CHESS_REVIEW_PLAYWRIGHT||require.resolve('playwright',{paths:[process.cwd(),process.env.CHESS_REVIEW_NODE_MODULES||'']}));}
catch{throw new Error('Provide Playwright through CHESS_REVIEW_PLAYWRIGHT or CHESS_REVIEW_NODE_MODULES.');}
async function main(){
 const input=process.argv[2],out=process.argv[3];
 if(!input||!out)throw new Error('Usage: node check_review.cjs review.html screenshot-directory');
 fs.mkdirSync(out,{recursive:true});
 const options={headless:true};
 if(process.env.CHESS_REVIEW_BROWSER)options.executablePath=process.env.CHESS_REVIEW_BROWSER;
 const browser=await playwright.chromium.launch(options);
 try{
  const page=await browser.newPage({viewport:{width:1280,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.resolve(input)).href);
  await page.locator('#board .square').last().waitFor();
  const data=await page.evaluate(()=>DATA);
  assert.equal(await page.locator('.square').count(),64);
  assert(await page.locator('[data-square="a1"]').evaluate(e=>e.classList.contains('dark')));
  assert(!(await page.locator('[data-square="h1"]').evaluate(e=>e.classList.contains('dark'))));
  assert.equal(await page.locator('#board .square').first().getAttribute('data-square'),data.meta.user_color==='black'?'h1':'a8');
  assert(await page.locator('#board img').evaluateAll(imgs=>imgs.every(x=>x.complete&&x.naturalWidth>0)));
  await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
  for(let i=0;i<data.lessons.length;i++){
   const lesson=data.lessons[i];
   await page.locator('#lesson-list button').nth(i).click();
   if(lesson.actualStates.length>1)await page.locator('#last').click();
   await page.locator('#better').click();await page.locator('#last').click();
   if(lesson.assert_mate)assert((await page.locator('#state-label').innerText()).includes('将死'));
   await page.locator('#try').click();
   const from=lesson.bestUci.slice(0,2),to=lesson.bestUci.slice(2,4);
   await page.locator(`[data-square="${from}"]`).click();
   assert(await page.locator(`[data-square="${to}"]`).evaluate(e=>e.classList.contains('legal')));
   await page.locator(`[data-square="${to}"]`).click();
   if(lesson.bestUci.length===5){const name={q:'后',r:'车',b:'象',n:'马'}[lesson.bestUci[4]];await page.locator('#promotion').getByRole('button',{name:'升变为'+name,exact:true}).click();}
   assert((await page.locator('#feedback').innerText()).includes('找到了'));
   await page.locator('#retry').click();await page.locator('#hint').click();
   assert((await page.locator('#feedback').innerText()).includes(lesson.hint));
  }
  await page.locator('#tab-replay').click();
  if(data.states.length>1)await page.locator('#last').click();
  assert((await page.locator('#state-label').innerText()).includes(data.meta.endLabel));
  assert.equal(await page.locator('#movelist button').count(),data.states.length-1);
  if(data.states.length>1){
   await page.locator('#first').click();await page.locator('#play').click();
   await page.waitForTimeout(1400);
   if((await page.locator('#play').innerText())==='暂停')await page.locator('#play').click();
   assert.equal(await page.locator('#timeline').inputValue(),'1');
  }
  const before=await page.locator('#board .square').first().getAttribute('data-square');
  await page.locator('#flip').click();assert.notEqual(await page.locator('#board .square').first().getAttribute('data-square'),before);
  await page.locator('#notes').fill('browser-check-note');await page.reload();
  assert.equal(await page.locator('#notes').inputValue(),'browser-check-note');await page.locator('#notes').fill('');
  const downloading=page.waitForEvent('download');await page.locator('#download-pgn').click();
  const download=await downloading;assert.equal(download.suggestedFilename(),data.meta.stem+'.pgn');
  for(const width of [390,320]){
   await page.setViewportSize({width,height:844});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),`horizontal overflow at ${width}`);
   await page.screenshot({path:path.join(out,`mobile-${width}.png`),fullPage:true});
  }
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({status:'passed',positions:data.states.length,lessons:data.lessons.length,user_color:data.meta.user_color,screenshots:out}));
 }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exit(1)});
