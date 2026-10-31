
/* GrowthLens AI v0.4 local competitor panel. No dependencies. */
(() => {
  'use strict';
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const panel = document.createElement('section');
  panel.className = 'card';
  panel.id = 'localCompetition';
  panel.innerHTML = `
    <h2>Local Competitor Intelligence</h2>
    <p class="muted">Discover nearby businesses from OpenStreetMap and compare publicly accessible webpages. Fixed search radius: <strong>15 miles</strong>.</p>
    <button id="localRun" type="button">Analyze Local Competition (15 miles)</button>
    <p id="localStatus" class="muted" role="status"></p>
    <div id="localOutput"></div>`;
  const results = document.getElementById('results');
  if (!results) return;
  results.parentNode.insertBefore(panel,results.nextSibling);
  const style = document.createElement('style');
  style.textContent = `
    #localCompetition table{width:100%;border-collapse:collapse;font-size:13px}
    #localCompetition th,#localCompetition td{padding:9px;text-align:left;border-bottom:1px solid #34515b;vertical-align:top}
    #localCompetition img{max-height:60px;max-width:160px;object-fit:contain;background:white;padding:5px;border-radius:6px}
    #localCompetition .localNote{font-size:12px;opacity:.85}
    @media print{
      #localCompetition{display:block!important;background:white!important;color:#172b36!important;border:0!important;padding:0!important;margin-top:20px!important}
      #localCompetition button,#localStatus{display:none!important}
      #localCompetition h2,#localCompetition h3{color:#172b36!important}
      #localCompetition table{font-size:9pt}
      #localCompetition th,#localCompetition td{border-bottom:1px solid #dce5e8!important;color:#172b36!important}
      #localCompetition a{color:#087f70!important}
      #localCompetition tr{break-inside:avoid}
      #localCompetition .localNote{color:#52636c!important}
    }`;
  document.head.appendChild(style);
  const $ = id => document.getElementById(id);
  $('localRun').onclick = async () => {
    const key = $('privateKey')?.value.trim();
    const url = $('url')?.value.trim() || (typeof activeAuditUrl !== 'undefined' ? activeAuditUrl : '');
    if (!key || !url) { $('localStatus').textContent='Enter your access key and website URL first.'; return; }
    $('localRun').disabled=true;
    $('localStatus').textContent='Checking business metadata, location, and public competitor websites. This may take a minute...';
    try {
      const res = await fetch('/api/local-competition', {
        method:'POST', headers:{'Content-Type':'application/json','X-GrowthLens-Key':key},
        body:JSON.stringify({url})
      });
      const data = await res.json();
      if (!res.ok) throw new Error(typeof data.detail==='string'?data.detail:'Request failed ('+res.status+')');
      const company=data.identity;
      const logo=company.logo_url ? `<img src="${esc(company.logo_url)}" alt="Company logo reported by website" referrerpolicy="no-referrer" onerror="this.style.display='none'">` : '<span class="muted">No logo detected</span>';
      const rivals=data.competitors.map(c=>`<tr><td>${esc(c.name)}</td><td>${esc(c.distance_miles)} mi</td><td>${c.score===null?'N/A':esc(c.score)+'/100'}</td><td><a href="${esc(c.website)}" target="_blank" rel="noopener noreferrer">Website</a></td><td>${esc(c.status)}</td></tr>`).join('');
      const actions=data.opportunities.slice(0,8).map(o=>`<li><strong>${esc(o.issue)}:</strong> ${esc(o.recommendation)} ${o.competitors_passing_check.length?'<span class="localNote">Competitors passing: '+esc(o.competitors_passing_check.join(', '))+'</span>':''}</li>`).join('');
      $('localOutput').innerHTML=`
        <div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin:15px 0">${logo}<div><h3 style="margin:0">${esc(company.name)}</h3><p class="muted" style="margin:5px 0">${esc(company.address||'Physical address not detected')} · ${esc(company.name_source)}</p></div></div>
        <p><strong>Target technical score:</strong> ${esc(data.audit.score)}/100 · <strong>Radius:</strong> 15 miles</p>
        ${data.warning?'<p class="bad">'+esc(data.warning)+'</p>':''}
        <h3>Nearby competitors (${data.competitors.length} found with websites)</h3>
        <table><thead><tr><th>Business</th><th>Distance</th><th>Technical score</th><th>Source website</th><th>Audit status</th></tr></thead><tbody>${rivals||'<tr><td colspan="5">No category-matched competitors with public websites were verified.</td></tr>'}</tbody></table>
        <p class="localNote">${esc(data.discovery_source)}. All scores use the same single-page technical checklist. N/A is not zero.</p>
        <h3>Business-specific action plan</h3><ol>${actions||'<li>No failed technical checks were identified on the target page.</li>'}</ol>
        <h3>Traffic and revenue evidence</h3><p><strong>Verified visits:</strong> Unavailable. ${esc(data.traffic.status)}</p><p><strong>Verified revenue opportunity:</strong> Unavailable. ${esc(data.revenue.status)}</p>
        <p class="localNote">${esc(data.limitations.join(' '))}</p>`;
      $('localStatus').textContent='Local analysis complete. You can print this section with the main report.';
    } catch(e) { $('localStatus').textContent=e.message; }
    finally { $('localRun').disabled=false; }
  };
})();
