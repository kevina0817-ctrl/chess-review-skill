#!/usr/bin/env node
// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Exercise the embedded reviews from a standalone copy with no sibling files.
const fs=require('fs'),path=require('path'),assert=require('assert'),{pathToFileURL}=require('url');
const playwright=require(process.env.CHESS_REVIEW_PLAYWRIGHT||require.resolve('playwright',{paths:[process.cwd(),process.env.CHESS_REVIEW_NODE_MODULES||'']}));
async function main(){
 const input=process.argv[2],out=process.argv[3];
 if(!input||!out)throw new Error('Usage: node check_library.cjs index.html screenshot-directory');
 fs.mkdirSync(out,{recursive:true});
 const portable=path.join(out,'portable');fs.mkdirSync(portable,{recursive:true});
 const standalone=path.join(portable,'index.html');fs.copyFileSync(input,standalone);
 const browser=await playwright.chromium.launch({headless:true,...(process.env.CHESS_REVIEW_BROWSER?{executablePath:process.env.CHESS_REVIEW_BROWSER}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[],remote=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>{if(/^https?:/.test(request.url()))remote.push(request.url())});
  await page.goto(pathToFileURL(path.resolve(standalone)).href);
  const games=await page.evaluate(()=>library.games.map(({html,...game})=>game));
  assert(games.length>0);assert.equal(await page.locator('.game').count(),games.length);
  async function ready(id){await page.waitForFunction(id=>{try{return document.getElementById('review-frame').contentWindow.eval('DATA.meta.stem')===id}catch{return false}},id);return page.frameLocator('#review-frame')}
  async function select(game){await page.locator('.game').filter({has:page.locator('.opponent',{hasText:game.opponent})}).filter({hasText:game.result}).first().click();return ready(game.id)}
  for(const game of games){
   // IDs, not display names, distinguish several games against the same opponent.
   await page.locator('.game').evaluateAll((buttons,id)=>buttons.find(button=>button.dataset.game===id).click(),game.id);
   const review=await ready(game.id);
   assert.equal(await review.locator('.square').count(),64);
   assert.equal(await review.locator('.square').first().getAttribute('data-square'),game.side==='black'?'h1':'a8');
   assert(await review.locator('#board img').evaluateAll(images=>images.every(image=>image.complete&&image.naturalWidth>0)));
   const lessons=await review.locator('body').evaluate(()=>DATA.lessons.map(lesson=>({uci:lesson.bestUci})));
   for(let i=0;i<lessons.length;i++){
    await review.locator('#lesson-list button').nth(i).click();await review.locator('#better').click();await review.locator('#last').click();await review.locator('#try').click();
    const uci=lessons[i].uci;
    await review.locator(`[data-square="${uci.slice(0,2)}"]`).click();await review.locator(`[data-square="${uci.slice(2,4)}"]`).click();
    if(uci.length===5)await review.locator('#promotion').getByRole('button',{name:'升变为'+{q:'后',r:'车',b:'象',n:'马'}[uci[4]],exact:true}).click();
    assert((await review.locator('#feedback').innerText()).includes('找到了'));
   }
   await review.locator('#tab-replay').click();await review.locator('#last').click();
   assert.equal(await review.locator('#movelist button').count(),game.plies);
   assert((await review.locator('#state-label').innerText()).includes(game.result));
   await review.locator('#notes').fill('note-'+game.id);
   const download=page.waitForEvent('download');await review.locator('#download-pgn').click();assert.equal((await download).suggestedFilename(),game.id+'.pgn');
  }
  // Switching and reloading retain each game's own notebook.
  for(const game of games){
   await page.locator('.game').evaluateAll((buttons,id)=>buttons.find(button=>button.dataset.game===id).click(),game.id);
   let review=await ready(game.id);assert.equal(await review.locator('#notes').inputValue(),'note-'+game.id);
   await page.reload();review=await ready(game.id);assert.equal(await review.locator('#notes').inputValue(),'note-'+game.id);
   await review.locator('#notes').fill('');
  }
  await page.locator('#side').selectOption('white');assert.equal(await page.locator('.game').count(),games.filter(game=>game.side==='white').length);
  await page.locator('#side').selectOption('black');assert.equal(await page.locator('.game').count(),games.filter(game=>game.side==='black').length);
  await page.locator('#side').selectOption('all');
  await page.locator('#search').fill('no-such-opponent-xyz');assert(await page.locator('#empty').isVisible());await page.locator('#clear').click();
  await page.locator('#search').fill(games[0].opponent);assert.equal(await page.locator('.game').count(),games.filter(game=>game.opponent.toLowerCase().includes(games[0].opponent.toLowerCase())).length);
  await page.locator('#search').fill('');
  await page.locator('.game').first().click();await ready(games[0].id);
  if(games.length>1){await page.locator('#next-game').click();await ready(games[1].id);await page.locator('#prev-game').click();await ready(games[0].id)}
  const htmlDownload=page.waitForEvent('download');await page.locator('#download-review').click();assert.equal((await htmlDownload).suggestedFilename(),games[0].id+'.html');
  for(const width of [1440,390,320]){
   await page.setViewportSize({width,height:1100});await page.evaluate(()=>window.scrollTo(0,0));
   await page.waitForFunction(()=>{const f=document.getElementById('review-frame');return Math.abs(f.getBoundingClientRect().height-f.contentDocument.body.scrollHeight)<12});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Outer overflow at '+width);
   assert(await page.frameLocator('#review-frame').locator('body').evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Review overflow at '+width);
   await page.screenshot({path:path.join(out,'library-'+width+'.png'),fullPage:false});
   if(width===390){await page.locator('#reader').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,'library-mobile-reader.png')})}
  }
  assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
  console.log(JSON.stringify({status:'passed',games:games.length,lessons:games.reduce((sum,game)=>sum+game.lessons,0),offline:true,notes:'isolated per game',screenshots:out}));
 }finally{await browser.close()}
}
main().catch(error=>{console.error(error);process.exit(1)});
