// Self-contained view: fetching is performed by the build script, never by the browser.
if(D.rating_history){
 const H=D.rating_history, poolNames={rapid:'快棋 · Rapid',blitz:'超快棋 · Blitz',bullet:'子弹棋 · Bullet',daily:'日棋 · Daily'},resultNames={win:'胜',draw:'和',loss:'负',unknown:'结果未知'};
 const standard=H.games.filter(g=>g.rules==='chess'),pools=Object.keys(poolNames).filter(k=>standard.some(g=>g.pool===k)||H.current[k]);
 const date=(t,full=false)=>new Date(t*1000).toLocaleString('zh-CN',full?{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}:{year:'numeric',month:'2-digit',day:'2-digit'});
 const sign=n=>(n>0?'+':'')+n;
 let displayed=[],points=[],selected=0,positions=[],plotWidth=1000;
 $('rating-section').hidden=false;$('positive-nav').hidden=false;$('positive-nav').textContent='成长趋势';
 $('progress-evidence').open=false;$('progress-evidence').hidden=!D.progress?.length;
 $('progress-evidence').querySelector('summary').textContent='好棋与改善的具体例子 · '+(D.progress||[]).length+' 条';
 $('archive-summary').textContent=D.cases.length+' 处待练对比 · '+H.games.length+' 盘历史对局';
 for(const pool of pools){const opt=document.createElement('option');opt.value=pool;opt.textContent=poolNames[pool];$('rating-pool').append(opt)}
 $('rating-pool').value=pools.includes('rapid')?'rapid':pools[0]||'';
 $('rating-sync').textContent=(H.status==='stale'?'本次同步未完成，正在显示上次完整记录。上次成功同步：':'数据同步于：')+date(H.synced_at,true)+' · 官方接口可能延迟更新。';
 $('rating-coverage').textContent='本次快照覆盖 '+H.archives.length+' 个月度档案、'+H.games.length+' 盘已完成对局，其中标准国际象棋 '+standard.length+' 盘、不计分 '+standard.filter(g=>!g.rated).length+' 盘。'+(H.games.length?('结束日期 '+date(H.games[0].end_time)+' 至 '+date(H.games.at(-1).end_time)+'。'):'')+'仅包括官方公开档案可获取的记录。';
 function choose(index){
  if(!points.length)return;
  selected=Math.max(0,Math.min(index,points.length-1));const g=points[selected];
  $('rating-slider').value=selected;$('rating-position').textContent=(selected+1)+' / '+points.length;
  $('rating-prev').disabled=selected===0;$('rating-next').disabled=selected===points.length-1;
  $('rating-detail-title').textContent=g.rating+' 分 · '+resultNames[g.result]+' · 对阵 '+g.opponent;
  const all=standard.filter(x=>x.rated&&x.pool===g.pool&&Number.isFinite(x.rating)),i=all.findIndex(x=>x.id===g.id),delta=i>0?' · 较上一条评分记录 '+sign(g.rating-all[i-1].rating):' · 这是首条评分记录';
  $('rating-detail-meta').textContent=date(g.end_time,true)+' · 我执'+(g.side==='white'?'白':'黑')+' · 对手赛后 '+(g.opponent_rating??'未知')+' 分'+delta;
  $('rating-game-link').href=g.url;
  const [x,y]=positions[selected]||[0,0];const marker=$('rating-marker');if(marker){marker.setAttribute('cx',x);marker.setAttribute('cy',y)}
  $('rating-chart').setAttribute('aria-label',poolNames[g.pool]+'评分曲线，当前选择 '+date(g.end_time)+'，'+g.rating+' 分，'+resultNames[g.result]);
 }
 function draw(){
  const svg=$('rating-chart');if(!points.length){svg.replaceChildren();return}
  plotWidth=Math.max(280,svg.clientWidth||1000);const w=plotWidth,h=300,l=45,r=w-17,t=24,b=258;
  svg.setAttribute('viewBox',`0 0 ${w} ${h}`);
  const min=Math.min(...points.map(g=>g.rating)),max=Math.max(...points.map(g=>g.rating)),span=Math.max(60,max-min),lo=Math.max(0,Math.floor((min-span*.12)/20)*20),hi=Math.ceil((max+span*.12)/20)*20;
  const start=points[0].end_time,end=points.at(-1).end_time;
  positions=points.map(g=>[end===start?(l+r)/2:l+(g.end_time-start)/(end-start)*(r-l),b-(g.rating-lo)/(hi-lo)*(b-t)]);
  let markup='';for(let i=0;i<=4;i++){const y=t+(b-t)*i/4,value=Math.round(hi-(hi-lo)*i/4);markup+=`<line x1="${l}" x2="${r}" y1="${y}" y2="${y}" stroke="#e2e8e1"/><text x="${l-8}" y="${y+4}" text-anchor="end" font-size="12" fill="#617168">${value}</text>`}
  markup+=`<text x="${l}" y="284" font-size="12" fill="#617168">${date(start)}</text><text x="${r}" y="284" text-anchor="end" font-size="12" fill="#617168">${end!==start?date(end):''}</text>`;
  markup+=`<polyline points="${positions.map(p=>p.join(',')).join(' ')}" fill="none" stroke="#235c45" stroke-width="2.5" stroke-linejoin="round"/>`;
  positions.forEach(([x,y],i)=>markup+=`<circle data-index="${i}" cx="${x}" cy="${y}" r="${points.length>80?2.5:3.5}" fill="#235c45"><title>${date(points[i].end_time)} · ${points[i].rating} 分</title></circle>`);
  markup+='<circle id="rating-marker" pointer-events="none" r="6" fill="#b57b19" stroke="white" stroke-width="2"/>';
  svg.innerHTML=markup;choose(selected);
 }
 function render(){
  const pool=$('rating-pool').value,period=$('rating-period').value,cut=period==='all'?0:H.synced_at-Number(period)*86400;
  displayed=standard.filter(g=>g.pool===pool&&g.end_time>=cut);
  points=displayed.filter(g=>g.rated&&Number.isFinite(g.rating));selected=Math.max(0,points.length-1);
  const current=H.current[pool];$('rating-current').textContent=current?.rating??'—';$('rating-current-date').textContent=current?'最近计分对局 '+date(current.date):'官方未提供当前评分';
  $('rating-change').textContent=points.length>=2?sign(points.at(-1).rating-points[0].rating):'—';
  $('rating-peak').textContent=points.length?Math.max(...points.map(g=>g.rating)):'—';
  const rated=displayed.filter(g=>g.rated);$('rating-count').textContent=rated.length+' 盘';
  $('rating-results').textContent=['win','draw','loss'].map(k=>rated.filter(g=>g.result===k).length+resultNames[k]).join(' · ')+(rated.some(g=>g.result==='unknown')?' · 含未知结果':'');
  $('rating-range').textContent=(points.length?date(points[0].end_time)+' — '+date(points.at(-1).end_time):'暂无评分记录')+(rated.length>points.length?' · '+(rated.length-points.length)+' 盘缺少评分':'');
  $('rating-chart').hidden=!points.length;$('rating-empty').hidden=!!points.length;
  $('rating-detail').hidden=!points.length;$('rating-slider').disabled=!points.length;$('rating-slider').max=Math.max(0,points.length-1);
  $('rating-prev').disabled=$('rating-next').disabled=!points.length;$('rating-position').textContent='0 / 0';
  $('rating-rows').replaceChildren();for(const g of [...displayed].reverse()){
   const tr=document.createElement('tr');for(const value of [date(g.end_time,true),g.opponent+' ('+(g.opponent_rating??'—')+')',resultNames[g.result],g.rated?(g.rating??'缺失'):'不计分']){const td=document.createElement('td');td.textContent=value;tr.append(td)}$('rating-rows').append(tr)
  }
  draw();
 }
 $('rating-slider').oninput=e=>choose(Number(e.target.value));$('rating-prev').onclick=()=>choose(selected-1);$('rating-next').onclick=()=>choose(selected+1);
 $('rating-pool').onchange=render;$('rating-period').onchange=render;
 $('rating-chart').onclick=e=>{if(!points.length)return;if(e.target.dataset.index!==undefined){choose(Number(e.target.dataset.index));return}const bounds=e.currentTarget.getBoundingClientRect(),x=(e.clientX-bounds.left)/bounds.width*plotWidth,y=(e.clientY-bounds.top)/bounds.height*300;let best=0,dist=Infinity;positions.forEach(([px,py],i)=>{const d=(x-px)**2+(y-py)**2;if(d<dist){best=i;dist=d}});choose(best)};
 new ResizeObserver(()=>{if(!$('positive-section').hidden)draw()}).observe($('rating-chart'));
 render();
}
