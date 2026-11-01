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
      if (!(await page.locator('#publicIntelRun').isVisible())) throw Error('Unified intelligence button missing');
      if (!(await page.locator('#memoryHealthRun').isVisible())) throw Error('Memory diagnostic button missing');
      if (!(await page.locator('input[name="localRadius"]').count() === 3)) throw Error('Radius controls missing');
      await page.locator('input[name="localRadius"][value="50"]').check();
      if (!(await page.locator('#publicIntelRun').innerText()).includes('50 miles')) throw Error('Radius selection not reflected');
      if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 3))
        throw Error('Horizontal viewport overflow at '+viewport.width);
      await page.locator('#url').fill('https://example.com');
      await page.locator('#publicIntelRun').click();
      await page.locator('#publicIntelStatus').getByText('Enter your access key').waitFor();
      await page.route('**/api/intelligence-team', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
        status:'complete_with_partial_results',
        engines:{
          website:{status:'available',source:'website',identity:{name:'Sample Roofing'},classification:{label:'Roofing contractor',confidence:'high'}},
          discovery:{status:'available',source:'Geoapify / Overpass',competitors:[{name:'Nearby Roofer',distance_miles:2,source_providers:['Geoapify','Overpass']}]},
          pagespeed_mobile:{status:'unavailable',reason:'Synthetic provider outage'},
          verification:{status:'available',source:'Evidence registry',reconciliation:{conflicts:[]}},
          opportunities:{status:'available',recommendations:[{issue:'Local presence',recommendation:'Review local competition',evidence:'Public listing'}]}
        },
        memory:{prior_observations:1,new_observations:2,persistent:true,neural_embeddings:true},
        limitations:['Synthetic test data only']
      })}));
      await page.locator('#privateKey').fill('testing-secret');
      await page.locator('#publicIntelRun').click();
      await page.locator('#localOutput').getByText('Nearby Roofer').waitFor();
      if (!(await page.locator('#localOutput').innerText()).includes('Review local competition'))
        throw Error('Evidence-supported opportunity missing');
      if (!(await page.locator('#publicIntelOutput').innerText()).includes('Intelligence memory'))
        throw Error('Memory status missing');
      if (await page.locator('#localRun').count()) throw Error('Redundant competition button should be removed');
      if (await page.locator('#glVisits').count()) throw Error('Manual financial calculator should be removed');
      if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 3))
        throw Error('Report overflows mobile viewport '+viewport.width);
      if (errors.length) throw Error('Browser errors: '+errors.join('; '));
      await page.close();
    }
    console.log('Mobile and desktop browser smoke tests passed');
  } finally { await browser.close(); }
})().catch(err=>{console.error(err);process.exit(1)});
