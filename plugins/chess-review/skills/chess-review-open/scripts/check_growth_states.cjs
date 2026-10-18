// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Verify absent, stale and small samples without network access or fictional user claims.
const fs=require('fs'),path=require('path'),assert=require('assert'),{pathToFileURL}=require('url');
const {chromium}=require(process.env.CHESS_REVIEW_PLAYWRIGHT||'playwright');
(async()=>{const [input,output]=process.argv.slice(2),out=path.resolve(output);fs.mkdirSync(out,{recursive:true});const source=fs.readFileSync(input,'utf8'),re=/(<script id="visual-data" type="application\/json">)([\s\S]*?)(<\/script>)/,base=JSON.parse(source.match(re)[2]);
const browser=await chromium.launch({headless:true,executablePath:process.env.CHESS_REVIEW_BROWSER});try{const p=await browser.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));await p.context().setOffline(true);
for(const kind of ['absent','empty','small','stale']){const d=structuredClone(base);if(kind==='absent'){delete d.rating_history;delete d.capability_history}else if(kind==='empty'){d.rating_history.games=[];d.rating_history.current={};d.capability_history.windows=[];d.capability_history.games=0}else if(kind==='small'){d.capability_history.windows=d.capability_history.windows.slice(0,1);d.capability_history.games=20;for(const w of d.capability_history.windows){for(const m of [w.errors,w.mate,w.defense,...w.phases]){m.count=0;m.total=0;m.games=0}}}else{d.rating_history.status='stale';d.capability_history.status='stale'}
const target=path.join(out,kind+'.html');fs.writeFileSync(target,source.replace(re,(_,a,b,c)=>a+JSON.stringify(d).replace(/</g,'\\u003c')+c));await p.goto(pathToFileURL(target).href+'#progress');const en=await p.locator('html').getAttribute('lang')==='en';
if(kind==='absent'){assert(await p.locator('#rating-section').isHidden());assert(await p.locator('#capability-section').isHidden())}
if(kind==='empty'){assert(await p.locator('#rating-empty').isVisible());assert(await p.locator('#rating-detail').isHidden());assert.equal(await p.locator('#capability-insights article').count(),0)}
if(kind==='small'){assert((await p.locator('#capability-rows').innerText()).includes('—'));assert(!(await p.locator('#capability-insights').innerText()).includes(en?'Improved across three groups':'连续改善'))}
if(kind==='stale'){assert((await p.locator('#rating-sync').innerText()).includes(en?'last complete':'上次'));assert((await p.locator('#capability-status').innerText()).includes(en?'last complete':'上次'))}
assert(!(await p.locator('#positive-section').innerText()).match(/NaN|Infinity/));}
assert.deepEqual(errors,[]);console.log(JSON.stringify({passed:true,states:['absent','empty','small','stale'],offline:true}));}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
