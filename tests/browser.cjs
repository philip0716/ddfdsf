// Optional: npm install --no-save playwright && npx playwright install chromium
// Run from repository root: node tests/browser.cjs
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const { strict: assert } = require('node:assert');
const { join } = require('node:path');
const port=18765;
const server=spawn('python',['server.py','--no-browser','--port',String(port)],{cwd:join(__dirname,'..'),stdio:'pipe'});
let browser;
(async()=>{
 try{
  for(let i=0;i<150;i++){
   try{const r=await fetch(`http://127.0.0.1:${port}/api/catalog`);if(r.ok)break;}catch{}
   if(i===149)throw new Error('Server did not start');
   await new Promise(r=>setTimeout(r,100));
  }
  browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1100},permissions:['clipboard-read','clipboard-write']});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const firstResponse=page.waitForResponse(r=>r.url().endsWith('/api/optimize'));
  await page.goto(`http://127.0.0.1:${port}`);
  await page.locator('#pitch .player').nth(10).waitFor();
  const before=await page.locator('#pitch .player b').allTextContents();
  assert.equal(await page.locator('#pitch .role-line[data-phase=ip]').count(),11);
  assert.equal(await page.locator('#pitch .role-line[data-phase=oop]').count(),11);
  assert.equal(await page.locator('#xi-roles tbody tr').count(),11);
  assert.equal(await page.locator('#bench .role-line[data-phase=ip]').count(),9);
  assert.equal(await page.locator('#bench .role-line[data-phase=oop]').count(),9);
  const catalogue=await (await page.request.get(`http://127.0.0.1:${port}/api/catalog`)).json();
  const first=await (await firstResponse).json();
  for(const c of first.xi){for(const phase of ['ip','oop'])assert((await page.locator('#xi-roles').textContent()).includes(catalogue.roles[c.slot[phase+'_role']].name));}
  assert.equal(await page.getByLabel('IP-Rolle Platz 1',{exact:true}).inputValue(),'auto');
  const fixedResponse=page.waitForResponse(r=>r.url().endsWith('/api/optimize'));
  await page.getByLabel('IP-Rolle Platz 1',{exact:true}).selectOption('ip:No-Nonsense Goalkeeper');
  const fixed=await (await fixedResponse).json();assert.equal(fixed.xi[0].slot.ip_role,'ip:No-Nonsense Goalkeeper');assert.equal(fixed.xi[0].role_selection.ip,'manual');
  await page.locator('.results:not(.pending)').waitFor();assert((await page.locator('.role-preview[data-slot="0"][data-phase="ip"]').textContent()).includes('Fixiert: No-Nonsense Goalkeeper'));
  const autoResponse=page.waitForResponse(r=>r.url().endsWith('/api/optimize'));await page.locator('#auto-roles').click();
  const auto=await (await autoResponse).json();assert(auto.xi.every(c=>c.role_selection.ip==='automatic'&&c.role_selection.oop==='automatic'));
  await page.locator('.results:not(.pending)').waitFor();
  if(process.env.FM26_SCREENSHOT_DIR)await page.screenshot({path:join(process.env.FM26_SCREENSHOT_DIR,'desktop.png'),fullPage:true});
  await page.selectOption('#objective','potential');
  await page.getByRole('heading',{name:'Talente mit Zukunft'}).waitFor();
  const after=await page.locator('#pitch .player b').allTextContents();assert.notDeepEqual(before,after);
  await page.locator('#copy-xi').click();assert.equal((await page.evaluate(()=>navigator.clipboard.readText())).split('\n').length,11);
  await page.locator('#pitch .player').first().click();assert(await page.locator('#detail').isVisible());assert(await page.locator('.figures').isVisible());
  assert.equal(await page.locator('#detail-content>.role-pair .role-line').count(),2);
  assert((await page.locator('#detail-content>.role-pair').textContent()).includes('Out of Possession'));
  assert(await page.locator('.alternative-card .role-line[data-phase=oop]').count()>0);
  await page.locator('#close-detail').click();
  await page.locator('#phase-oop').click();assert.equal(await page.locator('#pitch .player').count(),11);assert.equal(await page.locator('#pitch .role-line').count(),22);
  await page.selectOption('#formation','3-4-3');await page.locator('.results:not(.pending)').waitFor();assert.equal(await page.locator('#pitch .player').count(),11);
  const old=await page.locator('#pitch .player b').allTextContents();
  const name=old[0];const row=page.locator('#roster tr').filter({has:page.locator('b',{hasText:name})}).first();await row.locator('select').selectOption('injured');await page.locator('.results:not(.pending)').waitFor();assert(!(await page.locator('#pitch .player b').allTextContents()).includes(name));
  await page.setViewportSize({width:390,height:844});
  const cards=await page.locator('#pitch .player').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,cy:r.top+r.height/2};}));
  for(let i=0;i<cards.length;i++)for(let j=i+1;j<cards.length;j++)if(Math.abs(cards[i].cy-cards[j].cy)<1)assert(Math.min(cards[i].right,cards[j].right)<=Math.max(cards[i].left,cards[j].left));
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  if(process.env.FM26_SCREENSHOT_DIR)await page.screenshot({path:join(process.env.FM26_SCREENSHOT_DIR,'mobile.png'),fullPage:true});
  for(const squad of ['senior','second','u19']){
   const response=page.waitForResponse(r=>r.url().endsWith('/api/optimize')&&r.request().method()==='POST');
   await page.selectOption('#squad',squad);const r=await (await response).json();assert.equal(r.xi.length,11);assert(r.xi.concat(r.bench).every(c=>c.player.squad===squad));
  }
  const data=await (await page.request.get(`http://127.0.0.1:${port}/api/data`)).json();for(const p of data.players)p.squad='unknown';
  const imported=page.waitForResponse(r=>r.url().endsWith('/api/import-json'));
  await page.locator('#upload').setInputFiles({name:'squads.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data))});
  await imported;await page.locator('#squad option:checked[value=""]').waitFor({state:'attached'});
  await page.getByText('Kaderzuordnung prüfen',{exact:true}).click();
  await page.getByLabel('Kader für Team demo-u19',{exact:true}).selectOption('u19');
  const mappedResponse=page.waitForResponse(r=>r.url().endsWith('/api/optimize')&&r.request().method()==='POST');await page.selectOption('#squad','u19');
  const mapped=await (await mappedResponse).json();assert(mapped.xi.every(c=>c.player.team_id==='demo-u19'));
  assert.deepEqual(errors,[]);console.log('Browser checks passed: XI, objective switch, clipboard, details, OOP, formation, availability, mobile overflow, three squad filters raw team mapping automatic role selection, manual locks, and simultaneous IP/OOP roles.');
 }finally{if(browser)await browser.close();server.kill('SIGTERM');}
})().catch(e=>{console.error(e);process.exitCode=1;});
