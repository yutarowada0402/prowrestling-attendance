import {names,summary,eligible,monthly,priorPeriod} from './model.mjs';
const $=s=>document.querySelector(s);
const fmt=(n,d=0)=>n===null||n===undefined?'—':Number(n).toLocaleString('ja-JP',{maximumFractionDigits:d});
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let all=[],coverage=[],metric='total',page=0,descending=true;
let state={year:'2025',promotion:'all',country:'domestic'};
function card(label,value,unit,detail,icon,extra=''){return `<article class="metric"><h2 class="metric-label">${label}<span class="metric-icon" aria-hidden="true">${icon}</span></h2><div class="metric-value">${value}<small>${unit}</small></div><p class="metric-detail">${detail}</p>${extra}</article>`;}
function render(){
 const rows=eligible(all,state),s=summary(rows); page=0;
 $('#metrics').innerHTML=card('開催興行数',fmt(s.count),'大会','観衆不明の開催済み興行も含む','▤')
  +card('公表観衆合計',fmt(s.total),'人',`観衆判明 ${fmt(s.known)} 大会の合計`,'♧')
  +card('1興行あたり平均',fmt(s.mean,1),'人',`中央値 ${fmt(s.median,1)} 人 / 判明興行のみ`,'↗')
  +card('観衆判明率',s.rate===null?'—':fmt(s.rate*100,1),'%',`${fmt(s.known)} / ${fmt(s.count)} 大会・不明 ${fmt(s.count-s.known)} 大会`,'◉',`<div class="rate-track"><span style="width:${(s.rate??0)*100}%"></span></div>`);
 const relevant=coverage.filter(c=>(state.year==='all'||c.month.startsWith(state.year))&&(state.promotion==='all'||c.source===state.promotion));
 const partial=relevant.filter(c=>c.status!=='listing_complete').length;
 $('#scope').textContent=`${state.year==='all'?'収集済み全期間':state.year+'年'} / ${state.promotion==='all'?'全団体（event_idで重複排除）':names[state.promotion]} / ${state.country==='domestic'?'国内・開催済み':'国不明を含む全開催地・開催済み'}。${partial?`一部取得・未対応の月が ${partial} 件あります。`:'収集された興行を対象に集計。'} 公式サイトの掲載範囲と現実の全興行の網羅性は異なります。${state.country==='domestic'?` 国不明の除外 ${eligible(all,{...state,country:'all'}).filter(e=>e.country_code===null).length} 大会。`:''}`;
 renderChart(rows);renderVenues(rows);renderComparison(rows);renderTable();renderCoverage();
}
function renderChart(rows){
 let data=monthly(rows);
 if(state.year!=='all')data=Array.from({length:12},(_,i)=>{const month=`${state.year}-${String(i+1).padStart(2,'0')}`;return data.find(d=>d.month===month)||{month,total:null,mean:null,count:0,known:0};});
 if(!rows.length){$('#monthly').innerHTML='<p class="empty">選択した条件のデータはまだありません。</p>';return;}
 const W=700,H=290,L=48,R=12,T=24,B=40,plotH=H-T-B,plotW=W-L-R;
 const max=Math.max(...data.map(d=>d[metric]??0),1),ceil=Math.ceil(max/4/Math.pow(10,Math.floor(Math.log10(max/4))))*Math.pow(10,Math.floor(Math.log10(max/4)))*4;
 const step=plotW/data.length,bar=Math.min(30,step*.5);
 let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="月別${metric==='total'?'合計':'平均'}公表観衆。数値不明は棒を表示しません。">`;
 for(let i=0;i<=4;i++){const y=T+plotH*(1-i/4);svg+=`<line x1="${L}" y1="${y}" x2="${W-R}" y2="${y}" stroke="#edf1f5"/><text x="${L-10}" y="${y+4}" text-anchor="end">${fmt(ceil*i/4)}</text>`;}
 for(let i=0;i<data.length;i++){const d=data[i],value=d[metric],x=L+step*(i+.5),h=value===null?0:(value/ceil)*plotH;
  if(value!==null)svg+=`<rect x="${x-bar/2}" y="${T+plotH-h}" width="${bar}" height="${Math.max(h,1)}" rx="3" fill="${i===data.length-1?'#175fc3':'#3b8af0'}"><title>${esc(d.month)}: ${fmt(value,1)}人 / ${d.known}大会判明</title></rect>`;
  if(data.length<=24||i%Math.ceil(data.length/14)===0)svg+=`<text x="${x}" y="${H-14}" text-anchor="middle">${state.year==='all'?d.month.slice(2):Number(d.month.slice(5))+'月'}</text>`;
 }svg+='</svg>';$('#monthly').innerHTML=svg;
 $('#chart-legend').innerHTML=`<span><i></i>${metric==='total'?'公表観衆合計':'判明興行あたり平均'}（人）</span><span>未取得・未公表の月は空欄</span>`;
}
function renderVenues(rows){const groups=new Map();for(const r of rows){if(!groups.has(r.venue_id))groups.set(r.venue_id,{name:r.venue,events:[]});groups.get(r.venue_id).events.push(r);}
 const data=[...groups.values()].map(v=>({...v,...summary(v.events)})).filter(v=>v.total!==null).sort((a,b)=>b.total-a.total).slice(0,6),max=data[0]?.total||1;
 $('#venues').innerHTML=data.length?data.map((v,i)=>`<div class="venue-row"><div class="venue-label"><span>${String(i+1).padStart(2,'0')} &nbsp; ${esc(v.name)}</span><strong>${fmt(v.total)}<small> 人</small></strong></div><div class="venue-track"><span style="width:${v.total/max*100}%"></span></div></div>`).join(''):'<p class="empty">観衆が判明したデータはまだありません。</p>';}
function renderComparison(rows){let p=priorPeriod(all,rows,state);if(p){const sources=[...new Set(rows.map(r=>r.primary_promotion_id))];const last=Number(p.cutoff.slice(5,7));const comparable=sources.every(source=>[String(Number(state.year)-1),state.year].every(year=>Array.from({length:last},(_,i)=>`${year}-${String(i+1).padStart(2,'0')}`).every(month=>coverage.some(c=>c.source===source&&c.month===month&&c.status==='listing_complete'))));if(!comparable)p=null;}$('#comparison-scope').textContent=p?`${p.cutoff} まで / 前年は ${p.priorCutoff} まで。収集範囲の差を含む参考値。`:'前年も同じ月日までのYTDで比較します。';
 if(!p){$('#comparison').innerHTML='<p class="empty">同じ団体・対象月の前年データと一覧巡回記録が揃うと、件数と平均の変化を表示します。</p>';return;}
 const val=(label,v,unit,detail)=>`<div class="compare-value"><span>${label}</span><strong>${v}${unit}</strong><small>${detail}</small></div>`;
 const change=p.current.count-p.previous.count;
 $('#comparison').innerHTML=`<div class="compare-values">${val('開催興行数の差',(change>0?'+':'')+fmt(change),' 大会',`前年 ${fmt(p.previous.count)} → 今期 ${fmt(p.current.count)}`)}${val('公表観衆合計 前年比',p.yoy===null?'—':(p.yoy>0?'+':'')+fmt(p.yoy*100,1),'%',`前年 ${fmt(p.previous.total)} 人`)}${val('判明興行の平均の差',p.current.mean===null||p.previous.mean===null?'—':fmt(p.current.mean-p.previous.mean,1),' 人',`前年 ${fmt(p.previous.mean,1)} 人`)}</div><p class="small-note">合計差の内訳：判明件数効果 ${fmt(p.countEffect,1)} 人 ＋ 平均効果 ${fmt(p.meanEffect,1)} 人。判明率の変化も含みます。</p>`;}
function renderTable(){let rows=eligible(all,state);const search=$('#search').value.trim().toLowerCase();if(search)rows=rows.filter(r=>`${r.event_name} ${r.venue}`.toLowerCase().includes(search));rows.sort((a,b)=>(descending?-1:1)*a.event_date.localeCompare(b.event_date)||a.event_id.localeCompare(b.event_id));
 const start=page*30;$('#event-rows').innerHTML=rows.slice(start,start+30).map(r=>`<tr><td>${r.event_date}<br><small class="unknown">${r.start_time||'時刻不明'}</small></td><td><span class="promotion">${esc(names[r.primary_promotion_id]||r.primary_promotion_id)}</span><span class="event-name">${esc(r.event_name)}</span></td><td>${esc(r.venue)}</td><td class="numeric">${r.attendance_reported===null?'<span class="unknown">未公表</span>':fmt(r.attendance_reported)+' 人'}${r.conflict_flag?'<br><span class="unknown">競合・要確認</span>':''}</td><td>${/^https:\/\/(www\.noah\.co\.jp|www\.njpw\.co\.jp|www\.all-japan\.co\.jp)\//.test(r.source_url)?`<a class="source-link" href="${esc(r.source_url)}" target="_blank" rel="noopener">公式 ↗</a>`:'—'}</td></tr>`).join('')||'<tr><td colspan="5" class="empty">該当する興行がありません。</td></tr>';
 $('#event-count').textContent=`${fmt(rows.length)} 大会中 ${rows.length?start+1:0}–${Math.min(start+30,rows.length)} 件`;$('#previous').disabled=page===0;$('#next').disabled=start+30>=rows.length;
}
function renderCoverage(){const relevant=coverage.filter(c=>(state.year==='all'||c.month.startsWith(state.year))&&(state.promotion==='all'||state.promotion===c.source));const keys=[...new Set(relevant.map(c=>`${c.source}|${c.month.slice(0,4)}`))].sort().reverse();
 $('#coverage-grid').innerHTML=keys.length?`<table><thead><tr><th>団体 / 年</th>${Array.from({length:12},(_,i)=>`<th>${i+1}月</th>`).join('')}</tr></thead><tbody>${keys.map(key=>{const[source,year]=key.split('|');return `<tr><td>${esc(names[source])}<br>${year}</td>${Array.from({length:12},(_,i)=>{const c=relevant.find(c=>c.source===source&&c.month===`${year}-${String(i+1).padStart(2,'0')}`);const cls=c?.status==='listing_complete'?'complete':c?.status==='partial'?'partial':'unsupported';return `<td><span class="coverage-cell ${cls}" title="${c?`収集 ${c.collected} / 発見 ${c.discovered}・失敗 ${c.failed}`:'未取得'}">${c?`${c.collected}/${c.discovered}`:'—'}</span></td>`;}).join('')}</tr>`;}).join('')}</tbody></table>`:'<p class="empty">この条件の巡回記録はありません。</p>';}
async function load(){try{const [eventsResponse,coverageResponse,manifestResponse]=await Promise.all(['events.json','coverage.json','manifest.json'].map(f=>fetch('./data/'+f).then(r=>{if(!r.ok)throw new Error(`${f}: HTTP ${r.status}`);return r.json();})));all=eventsResponse;coverage=coverageResponse;const years=[...new Set([...all.map(e=>e.event_date.slice(0,4)),...coverage.map(c=>c.month.slice(0,4))])].sort().reverse();state.year=years.includes('2025')?'2025':years[0]||'all';$('#year').innerHTML=years.map(y=>`<option value="${y}" ${y===state.year?'selected':''}>${y}年</option>`).join('')+'<option value="all">すべての年</option>';$('#promotion').innerHTML='<option value="all">すべての団体</option>'+Object.entries(names).map(([key,name])=>`<option value="${key}">${name}</option>`).join('');$('#updated').textContent=`最終収集 ${manifestResponse.last_checked_at?new Date(manifestResponse.last_checked_at).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}):'未取得'} JST`;render();}catch(error){$('#error').hidden=false;$('#error').textContent='データを読み込めませんでした。時間をおいて再読み込みしてください。';$('#scope').textContent='読み込みエラー';console.error(error);}}
for(const id of ['year','promotion','country'])$('#'+id).addEventListener('change',e=>{state[id]=e.target.value;render();});
document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('.tab-panel').forEach(p=>p.hidden=p.id!==button.dataset.tab);document.querySelectorAll('[data-tab]').forEach(b=>{b.classList.toggle('active',b===button);if(b===button)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});}));
document.querySelectorAll('[data-metric]').forEach(button=>button.addEventListener('click',()=>{metric=button.dataset.metric;document.querySelectorAll('[data-metric]').forEach(b=>{b.classList.toggle('selected',b===button);b.setAttribute('aria-pressed',String(b===button));});renderChart(eligible(all,state));}));
$('#search').addEventListener('input',()=>{page=0;renderTable();});$('#sort-date').addEventListener('click',()=>{descending=!descending;$('#sort-date').textContent=`開催日 ${descending?'↓':'↑'}`;renderTable();});$('#previous').addEventListener('click',()=>{page--;renderTable();});$('#next').addEventListener('click',()=>{page++;renderTable();});
load();
