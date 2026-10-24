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
  await page.goto(`http://127.0.0.1:${port}`);
  await page.locator('#pitch .player').nth(10).waitFor();
  const before=await page.locator('#pitch .player b').allTextContents();
  if(process.env.FM26_SCREENSHOT_DIR)await page.screenshot({path:join(process.env.FM26_SCREENSHOT_DIR,'desktop.png'),fullPage:true});
  await page.selectOption('#objective','potential');
  await page.getByRole('heading',{name:'Talente mit Zukunft'}).waitFor();
  const after=await page.locator('#pitch .player b').allTextContents();assert.notDeepEqual(before,after);
  await page.locator('#copy-xi').click();assert.equal((await page.evaluate(()=>navigator.clipboard.readText())).split('\n').length,11);
  await page.locator('#pitch .player').first().click();assert(await page.locator('#detail').isVisible());assert(await page.locator('.figures').isVisible());await page.locator('#close-detail').click();
  await page.locator('#phase-oop').click();assert.equal(await page.locator('#pitch .player').count(),11);
  await page.selectOption('#formation','3-4-3');await page.locator('.results:not(.pending)').waitFor();assert.equal(await page.locator('#pitch .player').count(),11);
  const old=await page.locator('#pitch .player b').allTextContents();
  const name=old[0];const row=page.locator('#roster tr').filter({has:page.locator('b',{hasText:name})}).first();await row.locator('select').selectOption('injured');await page.locator('.results:not(.pending)').waitFor();assert(!(await page.locator('#pitch .player b').allTextContents()).includes(name));
  await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  if(process.env.FM26_SCREENSHOT_DIR)await page.screenshot({path:join(process.env.FM26_SCREENSHOT_DIR,'mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);console.log('Browser checks passed: XI, objective switch, clipboard, details, OOP, formation, availability, mobile overflow.');
 }finally{if(browser)await browser.close();server.kill('SIGTERM');}
})().catch(e=>{console.error(e);process.exitCode=1;});
