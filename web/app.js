'use strict';
const $=id=>document.getElementById(id);
let catalog,data,slots,result,phase='ip',overrides={},revision=0,timer,loading=false;
const labels={form:'Aktuelle Form',ip:'IP-Rolleneignung',oop:'OOP-Rolleneignung',position:'Positionsvertrautheit',readiness:'Fitness & Spielpraxis',potential:'PA-Obergrenze',gap:'Entwicklungsspielraum',window:'Entwicklungsfenster',development:'Entwicklungsbedingungen',future_ip:'Zukünftige IP-Eignung',future_oop:'Zukünftige OOP-Eignung',current:'Aktuelle Einsatzbereitschaft'};
function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function message(text){$('message').textContent=text;}
async function api(path,payload,raw=false){const response=await fetch('/api/'+path,{method:payload===undefined?'GET':'POST',headers:payload===undefined?{}:{'Content-Type':raw?'application/octet-stream':'application/json','X-FM26-Client':'local'},body:payload===undefined?undefined:raw?payload:JSON.stringify(payload)});const body=await response.json();if(!response.ok)throw new Error(body.error||'Anfrage fehlgeschlagen.');return body;}
function option(select,value,text){const o=node('option',text);o.value=value;select.append(o);}
const squadLabels={senior:'Senior Squad',second:'2nd Squad',u19:'U19 Squad',unknown:'Nicht zugeordnet'};
function playerSquad(p){return data.squad_mappings?.[String(p.club_id||'')]?.[String(p.team_id)]||p.squad||'unknown';}
function selectedPlayers(){return data.players.filter(p=>(!$('club').value||String(p.club_id)===$('club').value)&&(!$('squad').value||playerSquad(p)===$('squad').value)&&(!$('nation').value||(p.nation_ids||[]).map(String).includes($('nation').value)));}
function invalidate(){revision++;result=null;document.querySelector('.results').classList.add('pending');$('copy-xi').disabled=true;$('copy-bench').disabled=true;$('score').textContent='—';$('defense').textContent='—';clearTimeout(timer);}
function schedule(){invalidate();renderRoster();timer=setTimeout(calculate,250);}
function renderData(){
 overrides={};result=null;data.squad_mappings=data.squad_mappings||{};$('squad').value='';
 $('source').textContent=data.source||'JSON-Import';$('count').textContent=data.players.length;$('date').textContent='Stand: '+data.date;
 const clubs=new Map(data.players.map(p=>[String(p.club_id||''),p.club||'Ohne Verein']));$('club').replaceChildren();option($('club'),'','Alle Vereine');for(const [id,name]of [...clubs].sort((a,b)=>a[1].localeCompare(b[1])))if(id)option($('club'),id,name);
 const defaultClub=(data.managed_clubs||[]).find(c=>clubs.has(String(c)));if(defaultClub)$('club').value=defaultClub;
 $('nation').replaceChildren();option($('nation'),'','Alle Nationalitäten');const nations=[...new Set(data.players.flatMap(p=>p.nation_ids||[]).map(String))].sort((a,b)=>((data.nation_names||{})[a]||a).localeCompare((data.nation_names||{})[b]||b));for(const id of nations)option($('nation'),id,(data.nation_names||{})[id]||'Nation-ID '+id);
 $('notices').replaceChildren(...(data.notices||[]).map(t=>node('p',t)));renderRoster();schedule();
}
function renderSquadMapping(){
 const root=$('squad-mapping');root.replaceChildren();
 const players=data.players.filter(p=>!$('club').value||String(p.club_id)===$('club').value);
 const teams=new Map();for(const p of players){if(p.team_id==null)continue;const key=JSON.stringify([String(p.club_id||''),String(p.team_id)]);if(!teams.has(key))teams.set(key,[]);teams.get(key).push(p);}
 let shown=0;for(const [key,members]of teams){if(shown++>=100)break;const [club,team]=JSON.parse(key),p=members[0],label=node('label',(p.club||'Ohne Verein')+' · Team '+team+' · '+members.length+' Spieler');
 const select=node('select');select.setAttribute('aria-label','Kader für Team '+team);for(const [v,t]of Object.entries(squadLabels))option(select,v,t);
 const labels=[...new Set(members.map(playerSquad))];select.value=labels.length===1?labels[0]:'unknown';select.onchange=()=>{data.squad_mappings[club]=data.squad_mappings[club]||{};data.squad_mappings[club][team]=select.value;schedule();};label.append(select);root.append(label);}
 if(!teams.size)root.append(node('p','Keine Team-IDs vorhanden. Kaderangabe über das JSON-Feld squad importieren.','hint'));
 if(teams.size>100)root.append(node('p','Bitte einen Verein auswählen, um die weiteren Teams zuzuordnen.','hint'));
}
function renderTactics(){
 $('tactics').replaceChildren();slots.forEach((s,i)=>{const tr=node('tr');tr.append(node('td',String(i+1).padStart(2,'0')));for(const ph of ['ip','oop']){
 const td=node('td'),pos=node('select');pos.setAttribute('aria-label',`${ph.toUpperCase()}-Position Platz ${i+1}`);for(const p of catalog.positions)option(pos,p,p.toUpperCase());pos.value=s[ph+'_position'];td.append(pos);tr.append(td);
 const rt=node('td'),select=node('select');select.setAttribute('aria-label',`${ph.toUpperCase()}-Rolle Platz ${i+1}`);
 function fill(){select.replaceChildren();for(const [key,r] of Object.entries(catalog.roles))if(r.phase===ph&&r.positions.includes(s[ph+'_position']))option(select,key,r.name);if(![...select.options].some(o=>o.value===s[ph+'_role']))s[ph+'_role']=select.options[0].value;select.value=s[ph+'_role'];}
 fill();pos.onchange=()=>{s[ph+'_position']=pos.value;fill();schedule();};select.onchange=()=>{s[ph+'_role']=select.value;schedule();};rt.append(select);tr.append(rt);
 }$('tactics').append(tr);});
}
function config(){return {slots,objective:$('objective').value,club:$('club').value,nation:$('nation').value,squad:$('squad').value,squad_mappings:data.squad_mappings,bench_size:Number($('bench-size').value),min_position:Number($('min-position').value),min_defense:Number($('min-defense').value),min_fitness:Number($('min-fitness').value),horizon:Number($('horizon').value),only_confirmed:$('confirmed').checked,overrides};}
async function calculate(){
 if(loading)return;
 const own=++revision;const button=$('calculate');button.disabled=true;button.textContent='Elf wird berechnet …';message('');
 try{const response=await api('optimize',config());if(own!==revision)return;result=response;document.querySelector('.results').classList.remove('pending');renderResult();message(response.warnings.join('\n'));}
 catch(e){if(own===revision){result=null;$('pitch').replaceChildren(node('p',e.message,'warning'));$('bench').replaceChildren();message(e.message);}}
 finally{button.disabled=false;button.replaceChildren(document.createTextNode('Beste Elf berechnen '),node('span','→'));}
}
function renderResult(){
 $('score').textContent=(result.total_score/11).toFixed(1);$('defense').textContent=result.defense_average.toFixed(1);$('lineup-title').textContent=result.objective==='potential'?'Talente mit Zukunft':'Form, die den Unterschied macht';$('copy-xi').disabled=false;$('copy-bench').disabled=false;
 renderPitch();$('bench').replaceChildren();result.bench.forEach(c=>{const b=node('button');b.append(node('small',c.slot.ip_position.toUpperCase()+' · '+c.score.toFixed(1)),node('b',c.player.name),node('small',c.player.age+' Jahre · CA '+(c.player.ca??'?')+' / PA '+(c.pa??'?')));b.onclick=()=>detail(c);$('bench').append(b);});
 renderRoster();
}
function line(pos){if(pos==='gk')return 0;if(['dl','dc','dr'].includes(pos))return 1;if(['wbl','dm','wbr'].includes(pos))return 2;if(['ml','mc','mr'].includes(pos))return 3;if(['aml','amc','amr'].includes(pos))return 4;return 5;}
function side(pos){return ['dl','wbl','ml','aml'].includes(pos)?0:['dr','wbr','mr','amr'].includes(pos)?2:1;}
function renderPitch(){
 const pitch=$('pitch');pitch.replaceChildren(node('div',undefined,'pitch-line'),node('div',undefined,'pitch-circle'));if(!result)return;
 const lines=new Map();for(const c of result.xi){const p=c.slot[phase+'_position'],l=line(p);if(!lines.has(l))lines.set(l,[]);lines.get(l).push(c);}
 for(const [l,items]of lines){items.sort((a,b)=>side(a.slot[phase+'_position'])-side(b.slot[phase+'_position'])||a.slot_index-b.slot_index);
 items.forEach((c,i)=>{const b=node('button',undefined,'player');b.style.width=Math.min(27,90/items.length)+'%';b.style.left=((i+1)*100/(items.length+1))+'%';b.style.top=(89-l*15.5)+'%';const p=c.player;const r=catalog.roles[c.slot[phase+'_role']];b.title=p.name+' · '+r.name+' · '+c.score.toFixed(1);b.append(node('span',c.score.toFixed(1),'rating'),node('b',p.name),node('small',c.slot[phase+'_position'].toUpperCase()+' · '+r.name));if(p.status==='unknown')b.append(node('small','Verfügbarkeit ungeprüft','unconfirmed'));b.onclick=()=>detail(c);pitch.append(b);});}
}
async function copy(text){try{await navigator.clipboard.writeText(text);message('Namen kopiert.');}catch{message('Kopieren im Browser nicht möglich. Namen im folgenden Fenster markieren.');const d=$('detail-content');d.replaceChildren(node('h2','Namen kopieren'));const textarea=node('textarea');textarea.value=text;textarea.rows=13;textarea.style.width='100%';d.append(textarea);if(!$('detail').open)$('detail').showModal();textarea.select();}}
function detail(c){
 const root=$('detail-content');root.replaceChildren(node('h2',c.player.name),node('p',c.slot.ip_position.toUpperCase()+' → '+c.slot.oop_position.toUpperCase()+' · '+catalog.roles[c.slot.ip_role].name+' / '+catalog.roles[c.slot.oop_role].name));root.append(node('div',c.score.toFixed(1)+' / 100','detail-score'));
 const cp=node('button','Name kopieren');cp.onclick=()=>copy(c.player.name);root.append(cp);
 if(result.objective==='potential'){
 const figures=node('div',undefined,'figures');for(const [title,value]of [['PA-Obergrenze',c.pa],['CA-Szenario',c.projected_ca],['Entwicklungsscore',c.score.toFixed(1)]]){const div=node('div');div.append(node('small',title),node('b',value??'?'));figures.append(div);}root.append(figures,node('p','Szenarioband: '+(c.projection_interval||[]).join('–')+' CA · '+c.projection_label+'. Attributzuwächse sind eine vereinfachte Annahme.','hint'));
 }
 for(const [k,v]of Object.entries(c.parts)){const row=node('div',undefined,'bar-row'),title=node('div',undefined,'bar-label');title.append(node('span',labels[k]+' · '+Math.round(c.weights[k]*100)+' %'),node('b',v.toFixed(1)));const bar=node('div',undefined,'bar'),fill=node('i');fill.style.width=v+'%';bar.append(fill);row.append(title,bar);root.append(row);}
 root.append(node('h3','Datenbasis'),node('p',c.form.source+' · '+c.form.games+' bewertete Spiele · '+c.form.minutes+' Minuten · Form-Datenvertrauen '+c.form.confidence.toFixed(0)+' %','hint'));
 const history=node('div',undefined,'history');const matches=[...(c.player.matches||[])].filter(m=>m.rating!=null&&m.date<=data.date).sort((a,b)=>a.date.localeCompare(b.date)).slice(-20);for(const m of matches){const bar=node('span');bar.style.height=Math.max(5,(m.rating-4)*12)+'px';bar.title=m.date+' · '+m.rating+' · '+m.minutes+' Min.';history.append(bar);}root.append(history,node('p','Gespeicherte Noten, älteste links. Der Formwert nutzt maximal 20 Spiele aus 180 Tagen.','hint'));
 root.append(node('p','Attributabdeckung IP '+(c.coverage.ip*100).toFixed(0)+' % / OOP '+(c.coverage.oop*100).toFixed(0)+' % · Entwicklungsbedingungen '+(c.coverage.development*100).toFixed(0)+' %','hint'));
 for(const text of [...c.warnings,...(c.player.notes||[])])root.append(node('p',text,'warning'));
 const alternatives=result.alternatives[c.slot_index]||[];root.append(node('h3','Alternativen außerhalb der Startelf'));for(const a of alternatives){const b=node('button',a.player.name+' · '+a.score.toFixed(1));b.onclick=()=>detail(a);root.append(b);}root.append(node('p','Einzelplatz-Alternativen. Ein Wechsel kann die optimale Gesamtverteilung oder defensive Mindestqualität verändern.','hint'));
 if(!$('detail').open)$('detail').showModal();
}
function renderRoster(){
 if(!data)return;renderSquadMapping();const filtered=selectedPlayers();$('count').textContent=filtered.length;$('squad-info').textContent=filtered.length+' Spieler im Filter · '+data.players.filter(p=>(!$('club').value||String(p.club_id)===$('club').value)&&playerSquad(p)==='unknown').length+' im Verein noch nicht zugeordnet.';const text=$('search').value.toLowerCase(),eligible=selectedPlayers().filter(p=>p.name.toLowerCase().includes(text));const rows=eligible.slice(0,200);$('roster').replaceChildren();const selected=new Set(result?result.xi.map(c=>c.player.id):[]);
 rows.forEach(p=>{const tr=node('tr');const name=node('td');name.append(node('b',p.name),node('small',(selected.has(p.id)?'Startelf · ':'')+(p.club||'Ohne Verein')+' · '+squadLabels[playerSquad(p)]));tr.append(name,node('td',Object.entries(p.positions).filter(([k,v])=>v>=12).map(([k])=>k.toUpperCase()).join(' / ')),node('td',p.age??'?'),node('td',(p.ca??'?')+' / '+(p.pa??'?')),node('td',p.fitness==null?'Unbekannt':p.fitness.toFixed(0)+' %'));
 const td=node('td'),s=node('select');s.setAttribute('aria-label','Verfügbarkeit '+p.name);for(const [v,t]of [['unknown','Ungeprüft'],['available','Verfügbar'],['injured','Verletzt'],['suspended','Gesperrt'],['unavailable','Nicht verfügbar']])option(s,v,t);s.value=overrides[p.id]||p.status||'unknown';s.onchange=()=>{overrides[p.id]=s.value;schedule();};td.append(s);tr.append(td);const cp=node('td'),button=node('button','Kopieren');button.onclick=()=>copy(p.name);cp.append(button);tr.append(cp);$('roster').append(tr);});
 $('roster-count').textContent=rows.length+' von '+eligible.length+' Spielern im aktuellen Filter angezeigt'+(eligible.length>200?' · Suche eingrenzen. Die Optimierung nutzt den gesamten Filter.':'.');
}
async function importFile(){
 const f=$('upload').files[0];if(!f)return;invalidate();loading=true;$('calculate').disabled=true;message('Spielstand wird lokal eingelesen … Das kann bei großen Dateien einige Minuten dauern.');
 try{const incoming=f.name.toLowerCase().endsWith('.fm')?await api('import-save',f,true):await api('import-json',JSON.parse(await f.text()));data=incoming;renderData();message('Import abgeschlossen: '+data.players.length+' Spieler.');}
 catch(e){message(e.message+' Der bisherige Kader bleibt geladen.');}
 finally{loading=false;$('calculate').disabled=false;$('upload').value='';schedule();}
}
$('upload').onchange=importFile;$('calculate').onclick=()=>{invalidate();calculate();};
$('demo').onclick=async()=>{if(loading)return;invalidate();try{data=await api('demo',{});renderData();}catch(e){message(e.message);}};
$('objective').onchange=()=>{const potential=$('objective').value==='potential';$('objective-help').textContent=potential?'PA, Entwicklungsspielraum und zukünftige Rollenpassung stehen im Vordergrund.':'Aktuelle Leistungen zählen am stärksten. Rollen, Positionen und Fitness bleiben Teil der Auswahl.';$('horizon').disabled=!potential;schedule();};
for(const id of ['club','nation','squad','bench-size','horizon','min-position','min-defense','min-fitness','confirmed'])$(id).onchange=schedule;
$('formation').onchange=()=>{slots=structuredClone(catalog.formations[$('formation').value]);renderTactics();schedule();};
$('phase-ip').onclick=()=>{phase='ip';$('phase-ip').classList.add('active');$('phase-oop').classList.remove('active');renderPitch();};$('phase-oop').onclick=()=>{phase='oop';$('phase-oop').classList.add('active');$('phase-ip').classList.remove('active');renderPitch();};
$('copy-xi').onclick=()=>result&&copy(result.xi.map(c=>c.player.name).join('\n'));$('copy-bench').onclick=()=>result&&copy(result.bench.map(c=>c.player.name).join('\n'));$('search').oninput=renderRoster;$('close-detail').onclick=()=>$('detail').close();
$('export-data').onclick=()=>{const exported={...data,players:data.players.map(p=>({...p,status:overrides[p.id]||p.status||'unknown'}))};const url=URL.createObjectURL(new Blob([JSON.stringify(exported,null,2)],{type:'application/json'}));const a=node('a');a.href=url;a.download='fm26-kader.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
(async()=>{try{catalog=await api('catalog');for(const name of Object.keys(catalog.formations))option($('formation'),name,name);slots=structuredClone(catalog.formations[$('formation').value]);renderTactics();data=await api('data');renderData();$('objective-help').textContent='Aktuelle Leistungen zählen am stärksten. Rollen, Positionen und Fitness bleiben Teil der Auswahl.';$('horizon').disabled=true;}catch(e){message(e.message);}})();
