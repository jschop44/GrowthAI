/* GrowthLens AI v0.5 local competitor panel. No dependencies. */
(() => {
  'use strict';
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const panel = document.createElement('section');
  panel.className = 'card';
  panel.id = 'localCompetition';
  panel.innerHTML = `
    <h2>Local Competitor Intelligence</h2>
    <p class="muted">Discover nearby businesses using free OpenStreetMap data and compare publicly accessible webpages.</p>
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
    <button id="localRun" type="button">Analyze Local Competition (15 miles)</button>
    <p id="localStatus" class="muted" role="status"></p>\n    <label for="publicIndustry" style="display:block;margin-top:8px">Business industry (optional; enables discovery when website blocks audits)</label>\n    <select id="publicIndustry"><option value="">Detect from website</option><option value="pizza">Pizza restaurant</option><option value="restaurant">Restaurant</option><option value="roofing">Roofing</option><option value="dentist">Dentist</option><option value="plumber">Plumber</option><option value="electrician">Electrician</option><option value="hair">Hair salon</option><option value="auto">Auto repair</option><option value="hotel">Hotel</option><option value="pharmacy">Pharmacy</option><option value="landscaping">Landscaping</option><option value="hvac">HVAC</option><option value="bakery">Bakery</option><option value="coffee">Coffee shop</option></select>\n    <button id="publicIntelRun" type="button">Run coordinated intelligence team</button>\n    <label for="publicCik" style="display:block;margin-top:8px">SEC CIK (optional, for public corporations)</label>\n    <input id="publicCik" type="text" maxlength="10" inputmode="numeric" placeholder="Company CIK, if known">\n    <p id="publicIntelStatus" class="muted" role="status"></p>\n    <div id="publicIntelOutput"></div>
    <div id="localOutput"></div>
    <h3>Learning feedback (optional)</h3>
    <p class="muted small">Save a correction or verified-by-you observation. This is not independently verified and may be lost on free hosting.</p>
    <label for="learningField">Field</label><select id="learningField" style="padding:10px;background:#0c1d27;color:white"><option value="industry">Industry</option><option value="name">Business name</option><option value="address">Address</option><option value="service">Service</option><option value="correction">Other correction</option></select>
    <label for="learningValue">Correction or observation</label><input id="learningValue" maxlength="300" placeholder="e.g. Pizza restaurant">
    <button type="button" id="learningSave">Record feedback</button><p id="learningStatus" role="status"></p>`;
  const results = document.getElementById('results');
  if (!results) return;
  results.parentNode.insertBefore(panel, results.nextSibling);
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
    $('localRun').textContent = `Analyze Local Competition (${selectedRadius()} miles)`;
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
      $('publicIntelStatus').textContent='Coordinated engines complete. Missing results are not scored as zero.';
    } catch(e) { $('publicIntelStatus').textContent=String(e.message); }
    finally { $('publicIntelRun').disabled=false; }
  };
  $('localRun').onclick = async () => {
    const key = $('privateKey')?.value.trim();
    const url = $('url')?.value.trim() || (typeof activeAuditUrl !== 'undefined' ? activeAuditUrl : '');
    if (!key || !url) { $('localStatus').textContent='Enter your access key and website URL first.'; return; }
    const radius_miles = selectedRadius();
    $('localRun').disabled=true;
    $('localStatus').textContent=`Checking business metadata, location, and competitor websites within ${radius_miles} miles. This may take a minute...`;
    try {
      const res = await fetch('/api/local-competition', {
        method:'POST', headers:{'Content-Type':'application/json','X-GrowthLens-Key':key},
        body:JSON.stringify({url, radius_miles, business_address: $('localAddress').value.trim() || null})
      });
      const data = await res.json();
      if (!res.ok) throw new Error(typeof data.detail==='string'?data.detail:'Request failed ('+res.status+')');
      const company=data.identity;
      const logo=company.logo_url ? `<img src="${esc(company.logo_url)}" alt="Company logo reported by website" referrerpolicy="no-referrer" onerror="this.style.display='none'">` : '<span class="muted">No logo detected</span>';
      const rivals=data.competitors.map(c=>`<tr><td>${esc(c.name)}</td><td>${esc(c.distance_miles)} mi</td><td>${c.score===null?'N/A':esc(c.score)+'/100'}</td><td>${c.website ? `<a href="${esc(c.website)}" target="_blank" rel="noopener noreferrer">Website</a>` : "Not listed"}</td><td>${esc(c.status)}</td></tr>`).join('');
      const actions=data.opportunities.slice(0,8).map(o=>`<li><strong>${esc(o.issue)}:</strong> ${esc(o.recommendation)} ${o.competitors_passing_check.length?'<span class="localNote">Competitors passing: '+esc(o.competitors_passing_check.join(', '))+'</span>':''}</li>`).join('');
      $('localOutput').innerHTML=`
        <div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin:15px 0">${logo}<div><h3 style="margin:0">${esc(company.name)}</h3><p class="muted" style="margin:5px 0">${esc(company.address||'Physical address not detected')} · ${esc(company.name_source)}</p></div></div>
        <p><strong>Detected business type:</strong> ${esc(data.classification?.label || 'Unknown')} · <strong>Confidence:</strong> ${esc(data.classification?.confidence || 'unknown')}</p>
        <p class="localNote"><strong>Classification evidence:</strong> ${(data.classification?.evidence || []).map(e => esc(e.source) + ' (' + esc((e.matched_terms || []).join(', ')) + ')').join('; ') || 'Insufficient evidence'}</p>
        <p><strong>Location source:</strong> ${esc(data.location_source || "Not established")} ${company.address ? `· ${esc(company.address)}` : ""}</p>
        <p><strong>Target technical score:</strong> ${esc(data.audit.score)}/100 · <strong>Radius:</strong> ${esc(data.radius_miles)} miles</p>
        ${data.warning?'<p class="bad">'+esc(data.warning)+'</p>':''}
        <h3>Nearby competitors (${data.competitors.length} found in public listings)</h3>
        <table><thead><tr><th>Business</th><th>Distance</th><th>Technical score</th><th>Source website</th><th>Audit status</th></tr></thead><tbody>${rivals||'<tr><td colspan="5">No matching competitors were found in available public listings.</td></tr>'}</tbody></table>
        <p class="localNote">${esc(data.discovery_source)}. All scores use the same single-page technical checklist. N/A is not zero.</p>
        <h3>Industry-specific opportunities</h3><ol>${(data.industry_recommendations||[]).map(x=>`<li><strong>${esc(x.issue)}:</strong> ${esc(x.recommendation)} <span class="localNote">${esc(x.evidence)}</span></li>`).join('') || '<li>No additional homepage-specific signals identified.</li>'}</ol>
        <h3>Business-specific action plan</h3><ol>${actions||'<li>No failed technical checks were identified on the target page.</li>'}</ol>
        <h3>Observed competitor capabilities</h3>
        <p class="localNote">Homepage evidence only; absence is not established.</p>
        <ul>${(data.feature_comparison||[]).map(x=>"<li>"+esc(x.feature)+": target "+(x.target_observed?"observed":"not observed")+"; competitors observed: "+esc(x.competitors_with_feature.join(", ")||"none")+"</li>").join("")}</ul>
        <h3>Automatic financial scenarios</h3>
        <p class="localNote">Hypothetical opportunity ranges only, NOT verified lost revenue. Very low confidence; do not add scenarios together.</p>
        <ul>${(data.financial_scenarios?.opportunities||[]).map(x=>"<li>"+esc(x.feature)+": annual illustrative revenue range $"+Number(x.annual_revenue_scenarios.conservative).toLocaleString()+" to $"+Number(x.annual_revenue_scenarios.optimistic).toLocaleString()+"; baseline $"+Number(x.annual_revenue_scenarios.baseline).toLocaleString()+"; based on hypothetical conversion lift and transaction values, not measured sales.</li>").join("")||"<li>No modeled opportunities with observed competitor evidence.</li>"}</ul>
        <h3>Traffic and revenue evidence</h3>
        <p><strong>Verified visits:</strong> Unavailable. ${esc(data.traffic.status)}</p>
        <p><strong>Verified revenue opportunity:</strong> Unavailable. ${esc(data.revenue.status)}</p>
        <p class="localNote">${esc(data.limitations.join(' '))}</p>`;
      panel.dispatchEvent(new CustomEvent('growthlens:report', {detail:data}));
      $('localStatus').textContent=`Local ${data.radius_miles}-mile analysis complete. You can print this section with the main report.`;
    } catch(e) { $('localStatus').textContent=e.message; }
    finally { $('localRun').disabled=false; }
  };
})()
