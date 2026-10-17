'use strict';
const $=id=>document.getElementById(id);
const token=document.querySelector('meta[name="stress-token"]').content;
let current=null;
const fmt=(v,n=1)=>v==null?'—':Number(v).toFixed(n);
async function action(name,data){
 try{const response=await fetch('/api/'+name,{method:'POST',headers:{'Content-Type':'application/json','X-StressLab-Token':token},body:JSON.stringify(data||{})});const result=await response.json();if(!response.ok)throw Error(result.error||'Request failed');$('message').textContent='';await poll();}
 catch(e){$('message').textContent=e.message;}
}
$('controls').onsubmit=e=>{e.preventDefault();const level=$('level').value;let confirmed=false;if(level==='High'&&+$('workers').value>0){confirmed=confirm('High intensity increases CPU load, heat and fan activity. Save other work. Continue with this bounded test?');if(!confirmed)return;}action('start',{workers:Number($('workers').value),memory_mib:Number($('memory').value),duration:Number($('duration').value),level,confirm_high:confirmed});};
$('stop').onclick=()=>action('stop');$('reset').onclick=()=>{if(confirm('Clear the displayed result? Export CSV first if you need it.'))action('reset');};
$('level').onchange=()=>{$('warning').hidden=$('level').value!=='High';};
$('export').onclick=e=>{if($('export').classList.contains('disabled'))e.preventDefault();};
function chart(id,rows,key,color){
 const c=$(id),rect=c.getBoundingClientRect(),dpr=window.devicePixelRatio||1;c.width=rect.width*dpr;c.height=rect.height*dpr;const ctx=c.getContext('2d');ctx.scale(dpr,dpr);const w=rect.width,h=rect.height,L=39,R=12,T=14,B=26;const pw=w-L-R,ph=h-T-B;
 ctx.font='10px Segoe UI';ctx.textAlign='right';
 for(let n=0;n<=100;n+=25){const y=T+ph*(1-n/100);ctx.strokeStyle='#e7eef1';ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(w-R,y);ctx.stroke();ctx.fillStyle='#718b98';ctx.fillText(n+'%',L-7,y+3);}
 if(!rows.length)return;const x=i=>L+(rows.length>1?i/(rows.length-1):0)*pw,y=v=>T+ph*(1-v/100);
 rows.forEach((r,i)=>{ctx.fillStyle=r.phase==='Running'?'#0c9d9510':r.phase==='Recovery'?'#8c7cc913':'#a6b6c110';ctx.fillRect(x(i),T,Math.max(2,pw/Math.max(rows.length-1,1)),ph);});
 ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();rows.forEach((r,i)=>i?ctx.lineTo(x(i),y(r[key])):ctx.moveTo(x(i),y(r[key])));ctx.stroke();
 ctx.fillStyle='#718b98';ctx.textAlign='left';ctx.fillText(rows[0].phase==='Idle'?'Live history':fmt(rows[0].seconds)+' s',L,h-5);ctx.textAlign='right';ctx.fillText(rows.at(-1).phase==='Idle'?'Now':fmt(rows.at(-1).seconds)+' s',w-R,h-5);
}
function render(s){current=s;const m=s.latest,lim=s.limits,active=['Baseline','Running','Stopping','Recovery'].includes(s.status);$('status').textContent=s.status;$('elapsed').textContent=fmt(s.elapsed)+' s';
 $('workers').max=lim.max_workers;$('memory').max=lim.max_memory_mib;$('duration').max=lim.max_duration;$('workerlimit').textContent='(0–'+lim.max_workers+')';$('memlimit').textContent='Current safe maximum: '+lim.max_memory_mib+' MiB';$('budget').textContent='Effective budget: '+lim.effective_available_mib+' MiB available';
 ['level','workers','memory','duration','start','reset'].forEach(id=>$(id).disabled=active);$('stop').disabled=!active||s.status==='Recovery';$('export').classList.toggle('disabled',!s.summary);
 if(m){$('cpu').textContent=fmt(m.cpu_percent)+'%';$('ram').textContent=fmt(m.ram_percent)+'%';$('ramdetail').textContent=fmt(m.ram_used_mib/1024,2)+' / '+fmt(m.ram_total_mib/1024,2)+' GiB';$('available').textContent=fmt(m.ram_available_mib/1024,2)+' GiB';$('rss').textContent=fmt(m.worker_rss_mib)+' MiB';$('allocated').textContent=m.allocated_mib+' MiB initialized test memory';}
 chart('cpuchart',s.samples,'cpu_percent','#078782');chart('ramchart',s.samples,'ram_percent','#7061b0');
 $('phases').replaceChildren();if(s.summary){const z=s.summary;$('summary').textContent=`${z.outcome}. ${z.settings.workers} CPU worker(s), ${z.settings.level}, ${z.settings.memory_mib} MiB requested. Workload: ${fmt(z.workload_seconds,2)} s. Sampled peak CPU: ${fmt(z.peak_cpu_percent)}%. Peak system RAM: ${fmt(z.peak_ram_used_mib)} MiB. Peak worker RSS: ${fmt(z.peak_worker_rss_mib)} MiB. Peak initialized memory: ${fmt(z.peak_allocated_mib,0)} MiB. ${z.reason||''}`;
 Object.entries(z.phases).forEach(([name,p])=>{const tr=document.createElement('tr');[name,p.samples,fmt(p.mean_cpu_percent)+'%',fmt(p.mean_ram_used_mib)+' MiB'].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td);});$('phases').append(tr);});}else{$('summary').textContent=active?'Collecting '+s.status.toLowerCase()+' samples…':'Run a test to compare baseline, workload and recovery.';}
 if(s.reason)$('message').textContent=s.reason;
}
let polling=false;async function poll(){if(polling)return;polling=true;try{const r=await fetch('/api/status',{cache:'no-store'});if(!r.ok)throw Error('Server unavailable');render(await r.json());$('connection').textContent='● Connected locally';}catch(e){$('connection').textContent='Connection lost';$('message').textContent='Server unreachable. Keep the terminal open; workers still have a time limit.';}finally{polling=false;}}
window.addEventListener('resize',()=>{if(current)render(current);});poll();setInterval(poll,1000);