export const names = {noah:'NOAH',njpw:'新日本プロレス',ajpw:'全日本プロレス'};
export function summary(events){
  const unique = [...new Map(events.map(e=>[e.event_id,e])).values()];
  const known = unique.map(e=>e.attendance_reported).filter(n=>Number.isInteger(n)&&n>=0).sort((a,b)=>a-b);
  const total = known.length ? known.reduce((a,b)=>a+b,0) : null;
  const middle=Math.floor(known.length/2);
  return {count:unique.length,known:known.length,total,mean:known.length?total/known.length:null,
    median:known.length?(known.length%2?known[middle]:(known[middle-1]+known[middle])/2):null,
    rate:unique.length?known.length/unique.length:null};
}
export function eligible(events,{year='all',promotion='all',country='domestic'}={}){
  return events.filter(e=>e.event_status==='held'&&(year==='all'||e.event_date.slice(0,4)===year)
    &&(promotion==='all'||e.primary_promotion_id===promotion)&&(country==='all'||e.country_code==='JP'));
}
export function monthly(events){
  const groups=new Map();
  for(const e of events){const key=e.event_date.slice(0,7);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(e);}
  return [...groups].sort(([a],[b])=>a.localeCompare(b)).map(([month,rows])=>({month,...summary(rows)}));
}
export function priorPeriod(all,selected,filters){
  if(filters.year==='all'||!selected.length)return null;
  const cutoff=selected.map(e=>e.event_date).sort().at(-1);
  const lastDay=new Date(Date.UTC(Number(filters.year)-1,Number(cutoff.slice(5,7)),0)).getUTCDate();
  const priorCutoff=`${Number(filters.year)-1}-${cutoff.slice(5,7)}-${String(Math.min(Number(cutoff.slice(8,10)),lastDay)).padStart(2,'0')}`;
  const prior=eligible(all,{...filters,year:String(Number(filters.year)-1)}).filter(e=>e.event_date<=priorCutoff);
  if(!prior.length)return null;
  const priorPromotions=new Set(prior.map(e=>e.primary_promotion_id));
  if(selected.some(e=>!priorPromotions.has(e.primary_promotion_id)))return null;
  const current=summary(selected), previous=summary(prior);
  return {cutoff,priorCutoff,current,previous,
    countEffect:previous.mean===null?null:(current.known-previous.known)*previous.mean,
    meanEffect:previous.mean===null||current.mean===null?null:current.known*(current.mean-previous.mean),
    yoy:previous.total&&current.total!==null?current.total/previous.total-1:null};
}
