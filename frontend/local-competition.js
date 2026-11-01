/* GrowthLens AI v0.5 local competitor panel. No dependencies. */
(() => {
  'use strict';
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const panel = document.createElement('section');
  panel.className = 'card';
  panel.id = 'localCompetition';
  panel.innerHTML = `
    <h2>Coordinated Intelligence Team &amp; Local Competition</h2>
    <p class="muted">Run independent public-data, website, corporate and competitor intelligence together. This works even when a website blocks crawling if you provide an address and industry.</p>
    <fieldset id="localRadiusGroup" style="border:0;padding:0;margin:12px 0">
      <legend style="font-weight:700;margin-bottom:8px">Competitor search radius</legend>
      <div style="display:flex;gap:14px;flex-wrap:wrap">
        <label><input type="radio" name="localRadius" value="15" checked> 15 miles</label>
        <label><input type="radio" name="localRadius" value="25"> 25 miles</label>
        <label><input type="radio" name="localRadius" value="50"> 50 miles</label>
      </div>
    </fieldset>
    <label for="localAddress" style="display:block;margin:10px 0 4px">Business street address (optional; use if website location is missing or incorrect)</label>
    <input id="localAddress" type="text" maxlength="220" placeholder="Street, city, state, ZIP" style="width:100%;max-width:520px;padding:9px;box-sizing:border-box">

    <p id="localStatus" class="muted" role="status"></p>
    <label for="publicIndustry" style="display:block;margin-top:8px">Business industry (optional; enables discovery when website blocks audits)</label>
    <select id="publicIndustry"><option value="">Detect from website</option><option value="pizza">Pizza restaurant</option><option value="restaurant">Restaurant</option><option value="roofing">Roofing</option><option value="dentist">Dentist</option><option value="plumber">Plumber</option><option value="electrician">Electrician</option><option value="hair">Hair salon</option><option value="auto">Auto repair</option><option value="hotel">Hotel</option><option value="pharmacy">Pharmacy</option><option value="landscaping">Landscaping</option><option value="hvac">HVAC</option><option value="bakery">Bakery</option><option value="coffee">Coffee shop</option></select>
    <button id="publicIntelRun" type="button">Analyze website & competition (15 miles)</button>
    <label for="publicCik" style="display:block;margin-top:8px">SEC CIK (optional, for public corporations)</label>
    <input id="publicCik" type="text" maxlength="10" inputmode="numeric" placeholder="Company CIK, if known">
    <p id="publicIntelStatus" class="muted" role="status"></p>
    <div id="publicIntelOutput"></div>
    <div id="localOutput"></div>
    <h3>Learning feedback (optional)</h3>
    <p class="muted small">Save a correction or verified-by-you observation. This is not independently verified and may be lost on free hosting.</p>
    <label for="learningField">Field</label><select id="learningField" style="padding:10px;background:#0c1d27;color:white"><option value="industry">Industry</option><option value="name">Business name</option><option value="address">Address</option><option value="service">Service</option><option value="correction">Other correction</option></select>
    <label for="learningValue">Correction or observation</label><input id="learningValue" maxlength="300" placeholder="e.g. Pizza restaurant">
    <button type="button" id="learningSave">Record feedback</button><p id="learningStatus" role="status"></p>`;
  const results = document.getElementById('results');
  if (!results) return;
  // Keep the intelligence team visible above audit results, even before any audit.
  results.parentNode.insertBefore(panel, results);
  const style = document.createElement('style');
  style.textContent = `
    #localOutput{max-width:100%;overflow-x:auto;overflow-wrap:anywhere}\n    #localCompetition table{width:100%;border-collapse:collapse;font-size:13px}
    #localCompetition th,#localCompetition td{padding:9px;text-align:left;border-bottom:1px solid #34515b;vertical-align:top}
    #localCompetition img{max-height:60px;max-width:160px;object-fit:contain;background:white;padding:5px;border-radius:6px}
    #localCompetition .localNote{font-size:12px;opacity:.85}
    @media print{
      #localCompetition{display:block!important;background:white!important;color:#172b36!important;border:0!important;padding:0!important;margin-top:20px!important}
      #localCompetition button,#localStatus,#localRadiusGroup,#localAddress,#localCompetition label[for="localAddress"]{display:none!important}
      #localCompetition h2,#localCompetition h3{color:#172b36!important}
      #localCompetition table{font-size:9pt}
      #localCompetition th,#localCompetition td{border-bottom:1px solid #dce5e8!important;color:#172b36!important}
      #localCompetition a{color:#087f70!important}
      #localCompetition tr{break-inside:avoid}
      #localCompetition .localNote{color:#52636c!important}
    }`;
  document.head.appendChild(style);
  const $ = id => document.getElementById(id);
  const selectedRadius = () => Number(document.querySelector('input[name="localRadius"]:checked')?.value || 15);
  panel.querySelectorAll('input[name="localRadius"]').forEach(input => input.addEventListener('change', () => {
    $('publicIntelRun').textContent = `Analyze website & competition (${selectedRadius()} miles)`;
  }));
  $('learningSave').onclick = async () => {
    const key=$('privateKey')?.value.trim(), website=$('url')?.value.trim(), value=$('learningValue').value.trim();
    if (!key || !website || !value) { $('learningStatus').textContent='Enter the access key, website, and feedback.'; return; }
    try {
      const r=await fetch('/api/intelligence/evidence',{method:'POST',headers:{'Content-Type':'application/json','X-GrowthLens-Key':key},body:JSON.stringify({website,field:$('learningField').value,value})});
      const d=await r.json(); if (!r.ok) throw Error(d.detail || 'Could not save feedback');
      $('learningStatus').textContent='Feedback recorded as user-asserted (not independently verified). Free-host storage is temporary.';
    } catch(e) { $('learningStatus').textContent=String(e.message); }
  };
  $('publicIntelRun').onclick = async () => {
    const key=$('privateKey')?.value.trim(), url=$('url')?.value.trim(), cik=$('publicCik').value.trim();
    if (!key || !url) { $('publicIntelStatus').textContent='Enter your access key and website URL first.'; return; }
    $('publicIntelRun').disabled=true;
    $('publicIntelStatus').textContent='Querying independent public-data providers concurrently...';
    try {
      const response=await fetch('/api/intelligence-team',{method:'POST',
        headers:{'Content-Type':'application/json','X-GrowthLens-Key':key},
        body:JSON.stringify({url,cik:cik||null,radius_miles:selectedRadius(),business_address:$('localAddress').value.trim()||null,industry:$('publicIndustry').value||null})});
      const data=await response.json();
      if (!response.ok) throw Error(data.detail||'Public intelligence request failed');
      const names={website:'Website intelligence',discovery:'Competitor discovery',pagespeed_mobile:'Mobile performance',pagespeed_desktop:'Desktop performance',corporate_filings:'SEC public-company filings',verification:'Evidence verification',opportunities:'Growth opportunities'};
      $('publicIntelOutput').replaceChildren();
      const heading=document.createElement('h3');heading.textContent='Independent public intelligence';$('publicIntelOutput').append(heading);
      for (const [id,result] of Object.entries(data.engines||{})) {
        const paragraph=document.createElement('p');
        const label=document.createElement('strong');label.textContent=(names[id]||id)+': ';
        paragraph.append(label,document.createTextNode(result.status==='available'
          ? (result.performance_score!=null?result.performance_score+'/100 lab performance score':result.company_name||(id==='discovery'?(result.competitors||[]).length+' competitor listings':id==='verification'?(result.available_engines||[]).length+' sources available':id==='opportunities'?(result.recommendations||[]).length+' evidence-backed recommendations':'Available'))
          : (result.reason||result.status)));
        if (result.evidence_url && /^https:\/\//.test(result.evidence_url)) {
          const link=document.createElement('a');link.href=result.evidence_url;link.target='_blank';link.rel='noopener noreferrer';link.textContent=' · Source';paragraph.append(link);
        }
        $('publicIntelOutput').append(paragraph);
      }
      const discovery=data.engines?.discovery||{};
      const rivals=Array.isArray(discovery.competitors)?discovery.competitors:[];
      const opportunities=data.engines?.opportunities||{};
      const output=$('localOutput'); output.replaceChildren();
      const title=document.createElement('h3'); title.textContent='Nearby competition ('+rivals.length+' public listings)'; output.append(title);
      const note=document.createElement('p'); note.className='muted'; note.textContent=discovery.warning||discovery.reason||discovery.source||'Public listings may be incomplete.'; output.append(note);
      if(rivals.length){ const table=document.createElement('table'); const head=document.createElement('thead'); head.innerHTML='<tr><th>Business</th><th>Distance</th><th>Source</th></tr>';table.append(head); const body=document.createElement('tbody'); for(const rival of rivals){const tr=document.createElement('tr'); for(const value of [rival.name||'Unnamed',rival.distance_miles!=null?rival.distance_miles+' mi':'Unknown',(rival.source_providers||[rival.provider||'Public listing']).join(', ')]){const td=document.createElement('td');td.textContent=value;tr.append(td);}body.append(tr);}table.append(body);output.append(table);}
      const opportunityHeading=document.createElement('h3');opportunityHeading.textContent='Evidence-supported opportunities';output.append(opportunityHeading);
      const list=document.createElement('ul');for(const item of opportunities.recommendations||[]){const li=document.createElement('li');li.textContent=(item.issue||'Opportunity')+': '+(item.recommendation||'')+' ('+(item.evidence||'limited evidence')+')';list.append(li);}if(!list.children.length){const li=document.createElement('li');li.textContent='No verified opportunities established from available evidence.';list.append(li);}output.append(list);
      $('publicIntelStatus').textContent='Coordinated engines complete. Missing results are not scored as zero.';
    } catch(e) { $('publicIntelStatus').textContent=String(e.message); }
    finally { $('publicIntelRun').disabled=false; }
  };
})()
