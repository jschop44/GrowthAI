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
      await page.route('**/api/local-competition', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
        identity:{name:'Sample Roofing',address:'Test City',name_source:'website metadata'},
        classification:{label:'Roofing contractor',confidence:'medium',evidence:[]},
        location_source:'structured data',audit:{score:72},radius_miles:50,
        competitors:[{name:'Nearby Roofer',distance_miles:2,score:83,website:'https://example.com',status:'audited'}],
        discovery_source:'Synthetic browser test data',warning:null,
        industry_recommendations:[],opportunities:[],
        feature_comparison:[{feature:'financing',target_observed:false,competitors_with_feature:['Nearby Roofer']}],
        financial_scenarios:{opportunities:[{feature:'financing',annual_revenue_scenarios:{conservative:1000,baseline:3000,optimistic:6000}}]},
        traffic:{status:'Unavailable'},revenue:{status:'Unavailable'},limitations:['Synthetic test data only']
      })}));
      await page.locator('#privateKey').fill('testing-secret');
      await page.locator('#localRun').click();
      await page.locator('#localOutput').getByText('Sample Roofing').waitFor();
      if (!(await page.locator('#localOutput').innerText()).includes('Hypothetical opportunity ranges'))
        throw Error('Financial disclosure missing from report');
      if (!(await page.locator('#localOutput').innerText()).includes('Nearby Roofer'))
        throw Error('Competitor comparison missing from report');
      await page.locator('#glPremium').waitFor();
      if (!(await page.locator('#glPremium').innerText()).includes('Market intelligence overview'))
        throw Error('Premium dashboard absent');
      await page.locator('#glPremium input[aria-label="Search businesses"]').fill('nonmatching');
      if (!(await page.locator('#glPremium').innerText()).includes('0 of 1 listings'))
        throw Error('Business explorer search failed');
      await page.locator('#glPremium input[aria-label="Search businesses"]').fill('Nearby');
      if (!(await page.locator('#glPremium').innerText()).includes('1 of 1 listings'))
        throw Error('Business explorer search reset failed');
      if (await page.locator('#glVisits').count()) throw Error('Manual financial calculator should be removed');
      if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 3))
        throw Error('Report overflows mobile viewport '+viewport.width);
      if (errors.length) throw Error('Browser errors: '+errors.join('; '));
      await page.close();
    }
    console.log('Mobile and desktop browser smoke tests passed');
  } finally { await browser.close(); }
})().catch(err=>{console.error(err);process.exit(1)});
