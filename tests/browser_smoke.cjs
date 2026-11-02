const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    for (const viewport of [{width:390,height:844},{width:1280,height:800}]) {
      const page = await browser.newPage({viewport});
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.goto('http://127.0.0.1:8000/', {waitUntil:'domcontentloaded'});
      await page.locator('#auditForm').waitFor();
      if (!(await page.locator('#auditButton').isVisible())) throw Error('Audit action missing');
      if (!(await page.locator('#scenarioForm').count())) throw Error('Scenario calculator missing');
      await page.locator('#privateKey').fill('testing-secret');
      await page.route('**/api/business-lookup', route => route.fulfill({
        status:200,contentType:'application/json',
        body:JSON.stringify({status:'matches',matches:[
          {name:'Tamberinos Pizza',address:'Sample Street, Maryland',
           website:'https://example.com',source:'Synthetic test fixture'}
        ]})
      }));
      await page.locator('#url').fill('Tamberinos pizza');
      await page.locator('#auditButton').click();
      await page.locator('#businessMatches').getByText('Tamberinos Pizza',{exact:false}).waitFor();
      if (!(await page.locator('#businessMatches').innerText()).includes('Sample Street'))
        throw Error('Business results must show distinguishing location');
      await page.route('**/api/financial-estimate', route => route.fulfill({
        status:200,contentType:'application/json',
        body:JSON.stringify({annual_incremental_revenue_usd:2400,
          annual_incremental_gross_profit_usd:480,
          estimated_downtime_sales_loss_usd:0,
          first_year_total_cost_usd:740,
          first_year_net_contribution_usd:-260,
          payback_months:25,note:'Synthetic scenario, not a forecast'})
      }));
      await page.locator('#scenarioForm button[type=submit]').click();
      await page.locator('#scenarioResult').getByText('Hypothetical annual added sales',{exact:false}).waitFor();
      if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 3))
        throw Error('Horizontal viewport overflow at '+viewport.width);
      if (errors.length) throw Error('Browser errors: '+errors.join('; '));
      await page.close();
    }
    console.log('GrowthLens mobile and desktop smoke tests passed');
  } finally { await browser.close(); }
})().catch(err=>{console.error(err);process.exit(1)});
