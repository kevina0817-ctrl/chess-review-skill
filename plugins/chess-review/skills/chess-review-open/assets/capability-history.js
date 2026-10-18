if(D.capability_history){
 const C=D.capability_history,ws=C.windows||[],recent=ws.at(-1),names={rapid:'快棋',blitz:'超快棋',bullet:'子弹棋',daily:'日棋'};
 $('progress-evidence')?.remove();$('capability-section').hidden=false;$('positive-nav').hidden=false;
 const date=t=>new Date(t*1000).toLocaleDateString('zh-CN'),rate=m=>m.total?m.count/m.total*100:null;
 const value=(m,k)=>!m.total?'—':rate(m).toFixed(1)+(k==='errors'?' 次/100手':'%');
 const enough=(m,k)=>m.total>=(k==='errors'?200:8)&&m.games>=(k==='errors'?10:5);
 const metrics=[{key:'errors',title:'明显失误频率',hint:'越低越好',action:'落子前先检查：这步会不会漏掉被攻击的棋子，或给对方将军、吃子机会。'},
  {key:'mate',title:'一步将杀把握',hint:'越高越好',action:'每次轮到你，先扫描所有将军，逐一确认对方能否逃、挡或吃；有一步将死就先完成它。'},
  {key:'defense',title:'一步将杀威胁的化解',hint:'越高越好',action:'落子前先找对方下一步的将军；若能将死，先找吃掉进攻子、挡住路线或移动王的解法。'}];
 function insight(tag,title,number,description){const el=document.createElement('article');el.className='cap-insight';for(const [type,text] of [['small',tag],['h3',title],['strong',number],['p',description]]){const n=document.createElement(type);n.textContent=text;el.append(n)}$('capability-insights').append(el)}
 $('capability-scope').textContent=C.games?'分析范围：最近 '+C.games+' 盘'+(names[C.pool]||C.pool)+'，含赢、和、输 · '+date(C.start)+' — '+date(C.end)+'。各项按实际走法与机会计数。':'尚无完整能力统计。';
 $('capability-status').textContent=C.status==='stale'?'本次能力统计未更新，以下是上次完整分析（'+date(C.synced_at)+'），不能代表最新对局。':C.status!=='ok'?'能力统计暂不可用；评分历史仍可查看。':ws.length<3?'完整阶段不足三组，暂不判断持续进步。':'以下结论只描述这段样本；一次好棋不会被单独记作一次进步。';
 if(recent){
  const strong=metrics.filter(m=>m.key!=='errors'&&enough(recent[m.key],m.key)&&rate(recent[m.key])>=70).sort((a,b)=>rate(recent[b.key])-rate(recent[a.key]))[0];
  if(strong){const m=recent[strong.key];insight('近期表现较好的能力',strong.title,value(m,strong.key),`最近 ${m.total} 次机会完成 ${m.count} 次，来自 ${m.games} 盘。这是近期表现，是否能保持请继续看后续阶段。`)}
  else{const phases=recent.phases.map((m,i)=>({m,i})).filter(x=>x.m.total>=100&&x.m.games>=10).sort((a,b)=>rate(a.m)-rate(b.m));const best=phases[0];if(best){insight('当前相对更稳的阶段',['前 10 回合','第 11–25 回合','第 26 回合以后'][best.i],value(best.m,'errors'),`最近一组中，这个阶段的失误频率最低：${best.m.count} 次 / ${best.m.total} 手。它与其他阶段的局面难度不同，暂不能叫稳定优势。`)}else insight('优势判断','样本还不够','继续积累','暂时没有足够的跨局机会支持优势结论。下方先展示实际次数，不用单次好棋代替。')}
  let continuous=metrics.find(m=>ws.length===3&&ws.every(w=>enough(w[m.key],m.key))&&Math.abs(rate(ws.at(-1)[m.key])-rate(ws[0][m.key]))>=(m.key==='errors'?2:10)&&ws.slice(1).every((w,i)=>{const delta=rate(w[m.key])-rate(ws[i][m.key]);return m.key==='errors'?delta<0:delta>0}));
  if(continuous){insight('三个阶段连续改善',continuous.title,ws.map(w=>rate(w[continuous.key]).toFixed(1)).join(' → ')+(continuous.key==='errors'?'':'%'),(continuous.key==='errors'?'单位：次／100 手。':'')+'三个不重叠的 20 盘窗口都达到样本门槛，方向连续改善。这是已观察到的变化，仍需要后续对局确认。')}
  else if(ws.length>=2){const prev=ws.at(-2);const candidates=metrics.filter(m=>enough(recent[m.key],m.key)&&enough(prev[m.key],m.key)).map(m=>({...m,delta:(rate(recent[m.key])-rate(prev[m.key]))*(m.key==='errors'?-1:1)})).sort((a,b)=>b.delta-a.delta);const better=candidates.find(m=>m.delta>=(m.key==='errors'?2:10));if(better){insight('最近一组的变化',better.title,value(prev[better.key],better.key)+' → '+value(recent[better.key],better.key),'最近 20 盘比前 20 盘有所改善；三个阶段尚未形成连续改善，先观察能否保持。')}else insight('趋势判断','尚未看到连续改善','如实保留起伏','目前没有指标达到三组连续改善的条件。下方的实际次数会持续更新，不因几次成功就判断能力提升。')}
  else insight('趋势判断','先建立基线','1 个完整阶段','至少需要三个可比较阶段，才按同一规则观察持续变化。');
  const opportunity=metrics.filter(m=>m.key!=='errors'&&enough(recent[m.key],m.key)).sort((a,b)=>rate(recent[a.key])-rate(recent[b.key]))[0];
  const target=opportunity&&rate(recent[opportunity.key])<70?opportunity:metrics[0],m=recent[target.key];
  insight('下一阶段优先练习',target.title,target.key==='errors'?value(m,target.key):m.count+' / '+m.total+' 次机会',target.action+' 下一组仍看同一指标，并保留机会数。');
 }
 const head=document.createElement('tr'),label=document.createElement('th');label.textContent='能力 / 阶段';head.append(label);
 ws.forEach((w,i)=>{const th=document.createElement('th');th.textContent=ws.length===3?['较早 20 盘','上一组 20 盘','最近 20 盘'][i]:'第 '+(i+1)+' 组 · 20 盘';const small=document.createElement('small');small.textContent=date(w.start)+' — '+date(w.end);th.append(small);head.append(th)});$('capability-columns').append(head);
 function row(title,hint,get,key){const tr=document.createElement('tr'),th=document.createElement('th');th.scope='row';th.textContent=title;const h=document.createElement('small');h.textContent=hint;th.append(h);tr.append(th);ws.forEach(w=>{const m=get(w),td=document.createElement('td'),b=document.createElement('b'),small=document.createElement('small');b.textContent=value(m,key);small.textContent=key==='errors'?m.count+' 次失误 / '+m.total+' 手':m.count+' 次成功 / '+m.total+' 次机会';const games=document.createElement('small');games.textContent='来自 '+m.games+' 盘'+(key!=='errors'&&!enough(m,key)?' · 样本偏少':'');const bar=document.createElement('div');bar.className='cap-bar';const fill=document.createElement('i');fill.style.width=(rate(m)||0)+'%';bar.append(fill);td.append(b,small,games,bar);tr.append(td)});$('capability-rows').append(tr)}
 metrics.forEach(m=>row(m.title,m.hint,w=>w[m.key],m.key));
 ['前 10 回合','第 11–25 回合','第 26 回合以后'].forEach((phase,i)=>row(phase,'明显失误频率 · 越低越好',w=>w.phases[i],'errors'));
 $('capability-engine').textContent=C.engine?C.engine+' · 统计版本 '+C.version+' · 完整分析更新于 '+date(C.synced_at)+'。原始逐步分析保存在本地，每次复盘仅计算新对局；旧缓存保持相同口径。':'';
 if(recent){for(const kind of ['mate','defense']){const p=document.createElement('p');p.className='cap-source';p.append(document.createTextNode((kind==='mate'?'最近一步将杀机会：':'最近防杀机会：')));for(const e of recent[kind].examples.slice(-3)){const a=document.createElement('a');a.href=e.game;a.target='_blank';a.rel='noopener';a.textContent=e.opponent+' · 第 '+Math.ceil(e.ply/2)+' 回合 · '+(e.success?'成功':'未完成');p.append(a,document.createTextNode('； '))}$('capability-sources').append(p)}}
}
