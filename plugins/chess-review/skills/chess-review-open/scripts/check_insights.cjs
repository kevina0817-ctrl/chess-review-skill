#!/usr/bin/env node
// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Check actual user interactions, move counts, evaluation orientation, and offline behavior.
const fs=require('fs'),path=require('path'),assert=require('assert');
const {pathToFileURL}=require('url');
const {chromium}=require(process.env.CHESS_REVIEW_PLAYWRIGHT||require.resolve('playwright',{paths:[process.cwd()]}));
async function main(){
 const [input,out]=process.argv.slice(2);
 if(!input||!out)throw Error('Usage: node check_insights.cjs review.html screenshot-directory');
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.CHESS_REVIEW_BROWSER?{executablePath:process.env.CHESS_REVIEW_BROWSER}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:1080}}),errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route(/^https?:/,route=>{requests.push(route.request().url());return route.abort()});
  await page.goto(pathToFileURL(path.resolve(input)).href);
  const data=await page.evaluate(()=>DATA),a=data.analytics;
  async function assertBoard(fen){
   const names={K:'白王',Q:'白后',R:'白车',B:'白象',N:'白马',P:'白兵',k:'黑王',q:'黑后',r:'黑车',b:'黑象',n:'黑马',p:'黑兵'},expected={};
   fen.split(' ')[0].split('/').forEach((row,r)=>{let f=0;for(const c of row){if(/[1-8]/.test(c)){for(let n=0;n<Number(c);n++)expected[String.fromCharCode(97+f++)+(8-r)]='空格'}else expected[String.fromCharCode(97+f++)+(8-r)]=names[c]}});
   const actual=await page.locator('#board .square').evaluateAll(es=>Object.fromEntries(es.map(e=>[e.dataset.square,e.getAttribute('aria-label').split(' ')[1]])));
   assert.deepEqual(actual,expected);
  }
  assert.equal(await page.locator('#eval-rail').evaluate(e=>e.classList.contains('flipped')),data.meta.user_color==='black');
  if(!a){
   assert(await page.locator('#insight-empty').isVisible());
   assert(await page.locator('#insight-grid').isHidden());
   assert.equal(await page.locator('#eval-readout').innerText(),'未分析');
   assert(await page.locator('#forecast-open').isDisabled());
  }else{
   assert.equal(await page.locator('#score-user, #score-opponent, #phase-scores, [id^="score-"]').count(),0);
   assert(!/参考分|满分 100|分数怎么算/.test(await page.locator('body').innerText()));
   for(const [id,side] of [['stats-user',data.meta.user_color],['stats-opponent',data.meta.user_color==='white'?'black':'white']]){
    const stats=a.sides[side],good=new Set(data.lessons.filter(l=>l.positive&&l.color===side).map(l=>l.ply)).size;
    for(const [key,value,unit] of [['moves',stats.moves,'手'],['blunders',stats.blunders,'次'],['mistakes',stats.mistakes,'次'],['good',good,'次']])assert.equal(await page.locator(`#${id} [data-stat="${key}"]`).innerText(),value+' '+unit);
   }
   assert(a.rows.every(r=>!Object.hasOwn(r,'quality')));
   assert(Object.values(a.sides).every(s=>!Object.hasOwn(s,'score')));
   assert(Object.values(a.phases).every(p=>Object.values(p).every(s=>!Object.hasOwn(s,'score'))));
   assert(!(await page.locator('#insight-events button').evaluateAll(bs=>bs.some(b=>/参考分/.test(b.title)))));

   const whiteLabel='↑ 白方（'+(data.meta.user_color==='white'?'我':'对手')+'）占优';
   const blackLabel='↓ 黑方（'+(data.meta.user_color==='black'?'我':'对手')+'）占优';
   assert.equal(await page.locator('#chart-white-label').innerText(),whiteLabel);
   assert.equal(await page.locator('#chart-black-label').innerText(),blackLabel);
   await page.locator('#flip').click();
   assert.equal(await page.locator('#chart-white-label').innerText(),whiteLabel);
   assert.equal(await page.locator('#chart-black-label').innerText(),blackLabel);
   await page.locator('#flip').click();
   // Every event opens its own authored lesson, including across actor filters and modes.
   const eventIndices=await page.locator('#insight-events button').evaluateAll(bs=>bs.map(b=>Number(b.dataset.lessonIndex)));
   for(let i=0;i<eventIndices.length;i++){
    const index=eventIndices[i],l=data.lessons[index];assert(l,'Event must have an exact authored lesson');
    const opposite=l.actor==='user'?'opponent':'user';
    const filter=page.locator(`[data-actor-filter="${opposite}"]`);
    await page.locator('#tab-lessons').click();
    if(await filter.isEnabled())await filter.click();
    await page.locator('#try').click();
    if(i%2===0)await page.locator('#tab-replay').click();
    const event=page.locator('#insight-events button').nth(i);
    if(i%3===0){await event.focus();await page.keyboard.press('Enter')}
    else if(i%3===1){await event.focus();await page.keyboard.press('Space')}
    else await event.click();
    assert(await page.locator('#lessons-panel').isVisible());
    assert(await page.locator('#replay-panel').isHidden());
    assert(await page.locator('#forecast-panel').isHidden());
    assert.equal(await page.locator('#tab-lessons').getAttribute('aria-pressed'),'true');
    assert.equal(await page.locator('#actual').getAttribute('aria-pressed'),'true');
    assert.equal(await page.locator('#lesson-title').innerText(),l.title);
    assert.equal(await page.locator('#explain-text').innerText(),l.why);
    assert.equal(await page.locator('#lesson-list button').nth(index).getAttribute('aria-pressed'),'true');
    assert(await page.locator('#lesson-list button').nth(index).isVisible());
    await assertBoard(l.actualStates[Math.min(1,l.actualStates.length-1)].fen);
   }
   assert.equal(await page.locator('#eval-chart circle').count(),data.states.length);
   for(const i of [0,Math.floor((data.states.length-1)/2),data.states.length-1]){
    await page.locator('#eval-chart circle').nth(i).focus();await page.keyboard.press('Enter');
    assert.equal(await page.locator('#timeline').inputValue(),String(i));
    await assertBoard(data.states[i].fen);
    const before=await page.locator('#eval-readout').innerText();
    const whiteHeight=await page.locator('#eval-white').evaluate(e=>e.style.height);
    assert(Math.abs(parseFloat(whiteHeight)-a.positions[i].advantage)<.01);
    await page.locator('#flip').click();assert.equal(await page.locator('#eval-readout').innerText(),before);
    assert.equal(await page.locator('#eval-white').evaluate(e=>e.style.height),whiteHeight);
    await page.locator('#flip').click();
   }
   // Traverse one PV that reaches mate if available, plus a nonterminal PV.
   const candidates=[a.positions.findIndex(e=>e.forecast.some(f=>f.mate)),a.positions.findIndex(e=>e.forecast.length>2)];
   for(const index of new Set(candidates.filter(i=>i>=0))){
    await page.locator('#eval-chart circle').nth(index).focus();await page.keyboard.press('Enter');
    await page.locator('#forecast-open').click();assert(await page.locator('#forecast-panel').isVisible());
    assert.equal(await page.locator('#branch-badge').innerText(),'引擎示范');
    const frames=a.positions[index].forecast;
    for(let i=1;i<frames.length;i++){
     await page.locator('#next').click();await assertBoard(frames[i].fen);
     if(!a.positions.some(e=>e.fen===frames[i].fen)){
      assert.equal(await page.locator('#eval-readout').innerText(),'未分析');
      assert.equal(await page.locator('#chart-marker').getAttribute('visibility'),'hidden');
     }
     if(frames[i].mate)assert((await page.locator('#risk-text').innerText()).includes('将死已发生'));
    }
    await page.locator('#forecast-back').click();assert(await page.locator('#lessons-panel').isVisible());
   }
  }
  for(const actor of ['user','opponent']){
   const index=data.lessons.findIndex(l=>l.actor===actor);if(index<0)continue;
   await page.locator('#tab-lessons').click();await page.locator(`[data-actor-filter="${actor}"]`).click();
   assert.equal(await page.locator('#lesson-list button:visible').count(),data.lessons.filter(l=>l.actor===actor).length);
   await page.locator('#try').click();const l=data.lessons[index];
   const missing=l.legal.find(m=>!a?.positions.some(e=>e.fen===m.state.fen)&&m.uci.length===4);
   if(missing){await page.locator(`[data-square="${missing.uci.slice(0,2)}"]`).click();await page.locator(`[data-square="${missing.uci.slice(2,4)}"]`).click();assert.equal(await page.locator('#eval-readout').innerText(),'未分析')}
  }
  if(data.opening){
   await page.locator('#opening-learn summary').click();await page.locator('#opening-jump').click();
   await assertBoard(data.states[data.opening.ply].fen);
   assert.equal(await page.locator('#opening-resource').getAttribute('href'),data.opening.resource);
  }
  await page.locator('#tab-lessons').click();await page.locator('[data-actor-filter="all"]').click();
  await page.locator('#lesson-list button').first().click();await page.locator('#better').click();
  await page.locator('#next').click();await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
  for(const width of [390,320]){
   await page.setViewportSize({width,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow at ${width}`);
   await page.screenshot({path:path.join(out,`mobile-${width}.png`),fullPage:true});
  }
  assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
  console.log(JSON.stringify({status:'passed',analytics:!!a,user_color:data.meta.user_color,offline:true,screenshots:out}));
 }finally{await browser.close()}
}
main().catch(e=>{console.error(e);process.exit(1)});
