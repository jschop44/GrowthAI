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
    <h3>Data protection &amp; connection</h3><p class="muted small">Connection and backup checks run automatically.</p>
    <button id="memoryHealthRun" type="button" style="display:none">Check connection</button>
    <p id="memoryHealthStatus" class="muted" role="status"></p>
    <h3>Neural intelligence &amp; outcomes</h3>
    <p class="muted">Search saved evidence, compare historical observations, and record measured outcomes. Results retain their verification status.</p>
    <label for="neuralQuery">Evidence question</label><input id="neuralQuery" maxlength="500" placeholder="e.g. Website performance and local competitors">
    <button type="button" id="neuralSearch">Search evidence</button>
    <button type="button" id="historyCompare">Compare historical audits</button>
    <div id="neuralResults" role="status"></div>
`;
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
  $('memoryHealthRun').onclick = async () => {
    const key=$('privateKey')?.value.trim();
    if(!key){$('memoryHealthStatus').textContent='Enter the private access key first.';return;}
    $('memoryHealthRun').disabled=true;
    $('memoryHealthStatus').textContent='Testing persistent storage and neural inference...';
    try {
      const r=await fetch('/api/intelligence/memory-health',{headers:{'X-GrowthLens-Key':key}});
      const d=await r.json();
      if(!r.ok)throw Error(d.detail||'Connection test failed');
      $('memoryHealthStatus').textContent=d.status==='fully_connected'
        ?'Connected and protected. Website intelligence and backups are working.'
        :'Some storage checks need attention. Automatic monitoring will retry.';
    }catch(e){$('memoryHealthStatus').textContent=String(e.message);}
    finally{$('memoryHealthRun').disabled=false;}
  };
  // Check in the background when the access key is available.
  let lastHealthKey='';
  const autoHealth=()=>{const key=$('privateKey')?.value.trim();if(key && key!==lastHealthKey){lastHealthKey=key;$('memoryHealthRun').click();}};
  $('privateKey')?.addEventListener('change',autoHealth);
  setInterval(()=>{lastHealthKey='';autoHealth();},30*60*1000);
  autoHealth();
  const intelGet=async path=>{
    const key=$('privateKey')?.value.trim(),website=$('url')?.value.trim();
    if(!key||!website)throw Error('Enter the access key and website first.');
    const res=await fetch(path+(path.includes('?')?'&':'?')+'website='+encodeURIComponent(website),{headers:{'X-GrowthLens-Key':key}});
    const data=await res.json();if(!res.ok)throw Error(data.detail||'Request failed');return data;
  };
  // Human-readable results only. Evidence is persisted server-side automatically.
  const showIntel=(id,data)=>{
    const el=$(id);el.replaceChildren();
    const add=(tag,value,parent=el)=>{const node=document.createElement(tag);node.textContent=String(value??'');parent.append(node);return node;};
    const card=(heading)=>{const section=document.createElement('section');section.style.cssText='padding:14px;margin:12px 0;border:1px solid #45616b;border-radius:10px';add('h4',heading,section);el.append(section);return section;};
    if(data.status==='available' && Array.isArray(data.results)){
      add('h3',data.results.length?'Saved website evidence':'No saved evidence yet');
      if(!data.results.length){add('p','Complete a new website or competitor audit to automatically build your evidence library. No copying or manual saving is needed.');return;}
      data.results.forEach((item,i)=>{
        const evidence=item.evidence||{},section=card((evidence.title||evidence.company_name||item.kind||'Audit evidence')+' · '+(i+1));
        add('p','Source: '+(item.source||evidence.source||'Website audit'),section);
        if(typeof evidence.score==='number')add('p','Website audit score: '+evidence.score+'/100',section);
        add('p',item.verified?'Observed from the public website':'Reported or third-party information — not independently verified',section);
        const failed=(evidence.findings||[]).filter(f=>f.passed===false).slice(0,5);
        if(failed.length){add('strong','Recommended improvements',section);const ul=document.createElement('ul');failed.forEach(f=>add('li',f.recommendation||f.name||f.id,ul));section.append(ul);}
        (evidence.opportunities||[]).slice(0,4).forEach(o=>add('p',o.recommendation||o.issue,section));
      });return;
    }
    if(Array.isArray(data.changes)){
      add('h3',data.changes.length?'Changes between audits':'No changes to compare yet');
      if(!data.changes.length){add('p',data.observations_examined<2?'Complete at least two audits of this website to compare results.':'No measurable changes were found between the saved audits.');return;}
      data.changes.forEach(c=>{const section=card(String(c.field||'Measurement').replace(/_/g,' '));add('p','Previous: '+c.before+'  →  Latest: '+c.after,section);add('p',c.independently_verified?'Verified source observations':'Comparison of recorded observations',section);});return;
    }
    if(Array.isArray(data.outcomes)){
      add('h3',data.outcomes.length?'Recorded recommendation outcomes':'No recommendation outcomes recorded yet');
      data.outcomes.forEach(o=>{const d=o.data||o,section=card(d.metric||d.recommendation_id||'Outcome');add('p','Before: '+d.baseline+'  →  After: '+d.observed,section);add('p',d.verification==='user_asserted'?'User-reported measurement':'Recorded measurement',section);});return;
    }
    if(data.status==='recorded'||Object.hasOwn(data,'improved')){
      add('h3','Recommendation result saved');
      add('p',data.persistent?'Saved to persistent intelligence memory.':'Received, but durable storage has not been confirmed.');
      add('p',data.improved?'The reported measurement improved.':'No improvement was reported for this measurement.');
      add('small','Results are user-reported and do not prove causation.');return;
    }
    add('p',data.note||data.message||'No results available yet.');
  };
  $('neuralSearch').onclick=async()=>{try{
    const query=$('neuralQuery').value.trim();if(query.length<2)throw Error('Enter a question.');
    const data=await intelGet('/api/intelligence/evidence-ranking?query='+encodeURIComponent(query));
    showIntel('neuralResults',data);
  }catch(e){$('neuralResults').textContent=String(e.message);}};
  $('historyCompare').onclick=async()=>{try{showIntel('neuralResults',await intelGet('/api/intelligence/history-changes'));}
    catch(e){$('neuralResults').textContent=String(e.message);}};

})()
