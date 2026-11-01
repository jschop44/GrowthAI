const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    for (const viewport of [{width:390,height:844},{width:1280,height:800}]) {
      const page = await browser.newPage({viewport});
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.goto('http://127.0.0.1:8000/', {waitUntil:'networkidle'});
      await page.locator('#localCompetition').waitFor();
      if (!(await page.locator('#localRun').isVisible())) throw Error('Local intelligence panel missing');
      if (!(await page.locator('input[name="localRadius"]').count() === 3)) throw Error('Radius controls missing');
      await page.locator('input[name="localRadius"][value="50"]').check();
      if (!(await page.locator('#localRun').innerText()).includes('50 miles')) throw Error('Radius selection not reflected');
      if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 3))
        throw Error('Horizontal viewport overflow at '+viewport.width);
      await page.locator('#url').fill('https://example.com');
      await page.locator('#localRun').click();
      await page.locator('#localStatus').getByText('Enter your access key').waitFor();
      if (errors.length) throw Error('Browser errors: '+errors.join('; '));
      await page.close();
    }
    console.log('Mobile and desktop browser smoke tests passed');
  } finally { await browser.close(); }
})().catch(err=>{console.error(err);process.exit(1)});
