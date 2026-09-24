// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Capture the real local demo; no image editing or private account data.
const fs = require('fs');
const path = require('path');
const {pathToFileURL} = require('url');
const {chromium} = require(process.env.CHESS_REVIEW_PLAYWRIGHT || 'playwright');

(async () => {
  const input = process.argv[2];
  if (!input) throw new Error('Usage: node scripts/capture_demo.cjs demo/common-leaks.html [output-directory]');
  const out = path.resolve(process.argv[3] || path.join(__dirname, '../docs/screenshots'));
  fs.mkdirSync(out, {recursive: true});
  const browser = await chromium.launch({headless: true, ...(process.env.CHESS_REVIEW_BROWSER ? {executablePath: process.env.CHESS_REVIEW_BROWSER} : {})});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1100}, deviceScaleFactor: 1});
    await page.goto(pathToFileURL(path.resolve(input)).href);
    await page.evaluate(() => document.fonts.ready);
    if (!(await page.locator('body').innerText()).includes('10 盘虚构教学棋谱')) throw new Error('Only capture the fictional teaching demo.');
    await captureRegion('.wrap > p', '#player', 'common-leaks-overview.png');
    async function captureRegion(first, last, name) {
      await page.evaluate(() => window.scrollTo(0, 0));
      const clip = await page.evaluate(([a,b]) => {
        const r=document.querySelector(a).getBoundingClientRect(), s=document.querySelector(b).getBoundingClientRect();
        return {x:r.left-16, y:r.top+scrollY-16, width:r.width+32, height:s.bottom-r.top+32};
      }, [first,last]);
      await page.screenshot({path:path.join(out,name),fullPage:true,clip});
    }
    await page.setViewportSize({width: 1440, height: 1480});
    await page.locator('#player').evaluate(el => window.scrollTo(0, el.getBoundingClientRect().top + scrollY - 24));
    await page.locator('#comparison').screenshot({path:path.join(out,'common-leaks-comparison.png')});
    await page.locator('#positive-nav').click();
    await page.locator('.learning-nav').evaluate(el => window.scrollTo(0, el.getBoundingClientRect().top + scrollY - 24));
    await captureRegion('.learning-nav', '#positive-section', 'common-leaks-progress.png');
    console.log(JSON.stringify({screenshots: out, source: path.resolve(input), data: 'fictional teaching demo'}));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
