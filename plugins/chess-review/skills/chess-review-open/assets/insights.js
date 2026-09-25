 const analytics=DATA.analytics;
 const evalByFen=new Map();
 if(analytics)for(const item of analytics.positions){const prior=evalByFen.get(item.fen);if(!prior||(item.depth||0)>=(prior.depth||0))evalByFen.set(item.fen,item)}
 let forecast=null,lessonFilter='all';
 function evalText(e){if(!e)return '未分析';if(e.terminal)return e.terminal==='draw'?'规则判和':(e.terminal==='white'?'白方':'黑方')+'已将死对方';if(e.mate!==null)return(e.mate>0?'白方':'黑方')+'将杀 M'+Math.abs(e.mate);return(e.cp>=0?'+':'−')+(Math.abs(e.cp)/100).toFixed(2)+' · 白方视角'}
 function jumpToPly(n){stop();mode='replay';ply=n;selected=null;trial=null;draw()}
 function updateInsights(){
  const e=evalByFen.get(current().fen);$('eval-readout').textContent=evalText(e);$('eval-depth').textContent=e?'深度 '+(e.depth??'—'):'当前局面无引擎数据';
  $('eval-rail').classList.toggle('flipped',flipped);$('eval-rail').classList.toggle('unknown',!e);$('eval-rail').setAttribute('aria-label',e?evalText(e):'当前局面未分析');
  const value=e?e.advantage:50;$('eval-white').style.height=value+'%';$('eval-black').style.height=(100-value)+'%';
  const s=current();let note=s.mate?'将死已发生。':s.check?s.turn+'当前正被将军，必须先解将。':e?.mate!==null&&e?.mate!==undefined?evalText(e)+'：引擎在此搜索深度发现将杀；对手走法可能不同。':'先检查对手的将军、吃子与直接威胁。';
  if(!s.mate&&e?.forecast?.length>1){const tactical=e.forecast.slice(1,7).find(f=>f.mate||f.check||f.san.includes('x'));if(tactical)note+=' 示范后续含 '+tactical.san+'，可回放查看。'}
  $('risk-text').textContent=note;$('forecast-open').disabled=!e||e.forecast.length<2;$('forecast-open').textContent=e&&e.forecast.length>1?'查看引擎后续与威胁 →':'当前局面暂无引擎后续';
  if(analytics){const n=DATA.states.findIndex(f=>f.fen===s.fen);const marker=$('chart-marker');marker.setAttribute('visibility',n<0?'hidden':'visible');if(n>=0){marker.setAttribute('x1',12+576*n/(DATA.states.length-1));marker.setAttribute('x2',12+576*n/(DATA.states.length-1));}$('chart-current').textContent=(mode==='forecast'?'引擎示范 · ':s.san?s.san+' · ':'第 '+s.number+' 回合 · '+s.turn+'走棋前 · ')+evalText(e)}
 }
 function openForecast(){const e=evalByFen.get(current().fen);if(!e||e.forecast.length<2)return;stop();forecast=e;mode='forecast';step=0;selected=null;trial=null;draw()}
 function drawForecast(){
  $('forecast-summary').textContent='从刚才的局面出发，回放引擎的一条建议变化。将军不等于将死；合法变化不代表对手必然这样下。';
  $('forecast-moves').replaceChildren();forecast.forecast.forEach((f,i)=>{const b=document.createElement('button');b.textContent=i?f.san+(f.mate?' · 将死':f.check?' · 将军':f.san.includes('x')?' · 吃子':''):'推演起点';b.classList.toggle('active',step===i);b.onclick=()=>{stop();step=i;draw()};$('forecast-moves').append(b)});
 }
 function initInsights(){
  $('forecast-open').onclick=openForecast;$('forecast-back').onclick=()=>setMode('lesson');
  for(const button of document.querySelectorAll('[data-actor-filter]'))button.onclick=()=>{lessonFilter=button.dataset.actorFilter;document.querySelectorAll('[data-actor-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));document.querySelectorAll('#lesson-list button').forEach((b,i)=>b.hidden=lessonFilter!=='all'&&DATA.lessons[i].actor!==lessonFilter);const i=DATA.lessons.findIndex(l=>lessonFilter==='all'||l.actor===lessonFilter);if(i>=0)chooseLesson(i)};
  for(const b of document.querySelectorAll('[data-actor-filter]'))if(b.dataset.actorFilter!=='all')b.disabled=!DATA.lessons.some(l=>l.actor===b.dataset.actorFilter);
  if(analytics){
   $('insights').hidden=false;const ours=analytics.sides[DATA.meta.user_color],other=analytics.sides[DATA.meta.user_color==='white'?'black':'white'];
   $('score-user').textContent=ours.score??'—';$('score-opponent').textContent=other.score??'—';$('score-user-n').textContent=ours.moves+' 手 · '+ours.blunders+' 严重失误 · '+ours.mistakes+' 失误';$('score-opponent-n').textContent=other.moves+' 手 · '+other.blunders+' 严重失误 · '+other.mistakes+' 失误';
   $('score-caption').textContent='我方平均兵值损失 '+(ours.acpl===null?'无样本':(ours.acpl/100).toFixed(2)+' 兵')+' · '+ours.cp_samples+' 手可比样本（不含将杀评分）。平均分不等于胜负，记得看关键失误。';
   const phases=analytics.phases[DATA.meta.user_color];for(const [key,name]of Object.entries({opening:'开局',middlegame:'中局',endgame:'残局'})){const v=phases[key],row=document.createElement('div');row.className='phase-row';row.innerHTML='<span>'+name+'</span><div><div class="phase-track"><i style="width:'+(v.score??0)+'%"></i></div><span class="phase-count">'+(v.moves?v.moves+' 手':'无样本')+'</span></div><strong>'+(v.score??'—')+'</strong>';$('phase-scores').append(row)}
   const points=analytics.positions.map((e,i)=>[12+576*i/(analytics.positions.length-1),12+126*(1-e.advantage/100)]);
   const svg=$('eval-chart');svg.innerHTML='<rect x="12" y="12" width="576" height="63" fill="#f2f5ed"/><rect x="12" y="75" width="576" height="63" fill="#e0e7e0"/><path d="M12 75H588" stroke="#b7c1b6" stroke-dasharray="4 4"/><path d="'+points.map(([x,y],i)=>(i?'L':'M')+x.toFixed(2)+' '+y.toFixed(2)).join(' ')+'" fill="none" stroke="#235c45" stroke-width="2.5"/><line id="chart-marker" x1="12" x2="12" y1="10" y2="140" stroke="#ad6942" stroke-width="1.5"/>';
   points.forEach(([x,y],i)=>{const dot=document.createElementNS('http://www.w3.org/2000/svg','circle');dot.setAttribute('cx',x);dot.setAttribute('cy',y);dot.setAttribute('r','4');dot.setAttribute('fill','#235c45');dot.setAttribute('tabindex','0');dot.setAttribute('role','button');const name=(DATA.states[i].san||'起始局面')+' · '+evalText(analytics.positions[i]);dot.setAttribute('aria-label',name);const title=document.createElementNS('http://www.w3.org/2000/svg','title');title.textContent=name;dot.append(title);dot.onclick=e=>{e.stopPropagation();jumpToPly(i)};dot.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();jumpToPly(i)}};svg.append(dot)});
   svg.onclick=e=>{const rect=svg.getBoundingClientRect();jumpToPly(Math.max(0,Math.min(points.length-1,Math.round(((e.clientX-rect.left)/rect.width*600-12)/576*(points.length-1)))))};
   const events=[];for(const side of [DATA.meta.user_color,DATA.meta.user_color==='white'?'black':'white']){const rows=analytics.rows.filter(r=>r.side===side);events.push(...rows.filter(r=>r.classification!=='steady').sort((a,b)=>b.loss-a.loss).slice(0,2));events.push(...rows.filter(r=>r.preferred&&(r.check||r.capture)&&r.classification==='steady').slice(-2))}
   events.sort((a,b)=>a.ply-b.ply);for(const r of events){const b=document.createElement('button');const bad=r.classification!=='steady';b.className=bad?'bad':'good';b.textContent=(r.side===DATA.meta.user_color?'我方 ':'对手 ')+r.move+' · '+(bad?{blunder:'严重失误',mistake:'失误',inaccuracy:'不精确'}[r.classification]:'引擎首选');b.title='参考分 '+r.quality.toFixed(1)+'；点击回放此步';b.onclick=()=>jumpToPly(r.ply+1);$('insight-events').append(b)}
   $('metric-engine').textContent=(analytics.engine.name||'Stockfish')+' · 每局面 '+analytics.screen_seconds+' 秒初筛，关键步加深 '+analytics.refine_seconds+' 秒';
  }else{$('insights').hidden=false;$('insight-grid').hidden=true;$('insight-empty').hidden=false;$('metric-method').hidden=true}
  if(DATA.opening){const o=DATA.opening;$('opening-learn').hidden=false;$('opening-name').textContent=o.eco+' · '+o.name;$('opening-line').textContent=o.line;$('opening-match').textContent='本盘在 '+(DATA.states[o.ply].san||'对应局面')+' 后匹配到命名开局局面（包含转置识别）。这不表示后续每一步都符合理论。';$('opening-notes').textContent=o.notes||'先回到匹配局面，观察中心兵、轻子发展和王的安全，再看开局资料。';$('opening-jump').onclick=()=>{jumpToPly(o.ply);$('board').scrollIntoView({block:'center',behavior:'smooth'})};$('opening-resource').href=o.resource;$('opening-source').href=o.source;
   if(o.name.startsWith('Italian Game')){$('opening-specific').hidden=false;$('opening-specific').href='https://www.chess.com/openings/Italian-Game';$('opening-specific').textContent='意大利开局：计划与常见变化 ↗'}
   if(o.name.startsWith('Philidor Defense')){$('opening-specific').hidden=false;$('opening-specific').href='https://www.chess.com/openings/Philidor-Defense';$('opening-specific').textContent='菲利多尔防御：计划与常见变化 ↗'}
   if(o.name.startsWith('Sicilian Defense')){$('opening-specific').hidden=false;$('opening-specific').href='https://www.chess.com/openings/Sicilian-Defense';$('opening-specific').textContent='西西里防御：计划与常见变化 ↗'}
  }
 }
