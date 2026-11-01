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
    <h3>Neural memory connection</h3>
    <button id="memoryHealthRun" type="button">Test Neural Memory &amp; Backup</button>
    <p id="memoryHealthStatus" class="muted" role="status"></p>
    <h3>Learning feedback (optional)</h3>
    <p class="muted small">Save a correction or observation. User feedback is not independently verified; durable storage is checked separately.</p>
    <label for="learningField">Field</label><select id="learningField" style="padding:10px;background:#0c1d27;color:white"><option value="industry">Industry</option><option value="name">Business name</option><option value="address">Address</option><option value="service">Service</option><option value="correction">Other correction</option></select>
    <label for="learningValue">Correction or observation</label><input id="learningValue" maxlength="300" placeholder="e.g. Pizza restaurant">
    <button type="button" id="learningSave">Record feedback</button><p id="learningStatus" role="status"></p>
    <h3>Neural intelligence &amp; outcomes</h3>
    <p class="muted">Search saved evidence, compare historical observations, and record measured outcomes. Results retain their verification status.</p>
    <label for="neuralQuery">Evidence question</label><input id="neuralQuery" maxlength="500" placeholder="e.g. Website performance and local competitors">
    <button type="button" id="neuralSearch">Search evidence</button>
    <button type="button" id="historyCompare">Compare historical audits</button>
    <div id="neuralResults" role="status"></div>
    <h3>Measure recommendation results</h3>
    <label for="outcomeId">Recommendation ID</label><input id="outcomeId" maxlength="120" placeholder="e.g. improve-mobile-speed">
    <label for="outcomeMetric">Metric</label><input id="outcomeMetric" maxlength="80" placeholder="e.g. Mobile performance score">
    <label for="outcomeBaseline">Before</label><input id="outcomeBaseline" type="number" step="any">
    <label for="outcomeObserved">After</label><input id="outcomeObserved" type="number" step="any">
    <label for="outcomeDirection">Desired direction</label><select id="outcomeDirection"><option value="increase">Increase</option><option value="decrease">Decrease</option></select>
    <label for="outcomeSource">Evidence URL</label><input id="outcomeSource" type="url" placeholder="https://your-website.com/evidence">
    <button type="button" id="outcomeSave">Record measured outcome</button>
    <button type="button" id="outcomeLoad">View outcomes</button>
    <div id="outcomeResults" role="status"></div>`;
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
      $('memoryHealthStatus').textContent=
        'Qdrant: '+(d.qdrant_write_and_read_verified?'verified persistent read/write':d.qdrant_configured?'configured; read/write not verified':'not configured')+
        '. Embeddings: '+(d.neural_inference_verified?'Qdrant neural inference verified':d.free_embedding_fallback?'free deterministic fallback':'not verified')+
        '. PostgreSQL backup: '+(d.postgres_backup_read_verified?'verified write and recovery':d.postgres_backup_write_verified?'write verified; recovery not verified':d.postgres_backup_configured?'configured; write failed':'not configured')+
        '. Overall: '+d.status+'. '+Object.entries(d.provider_diagnostics||{}).map(([name,info])=>name+': '+(info.http_status?'HTTP '+info.http_status:info.error_type||'not configured')).join('; ')+'.';
    }catch(e){$('memoryHealthStatus').textContent=String(e.message);}
    finally{$('memoryHealthRun').disabled=false;}
  };
  $('learningSave').onclick = async () => {
    const key=$('privateKey')?.value.trim(), website=$('url')?.value.trim(), value=$('learningValue').value.trim();
    if (!key || !website || !value) { $('learningStatus').textContent='Enter the access key, website, and feedback.'; return; }
    try {
      const r=await fetch('/api/intelligence/evidence',{method:'POST',headers:{'Content-Type':'application/json','X-GrowthLens-Key':key},body:JSON.stringify({website,field:$('learningField').value,value})});
      const d=await r.json(); if (!r.ok) throw Error(d.detail || 'Could not save feedback');
      $('learningStatus').textContent='Feedback recorded as user-asserted (not independently verified). Persistence: '+(d.durable?'durable':'not verified')+'.';
    } catch(e) { $('learningStatus').textContent=String(e.message); }
  };
  const intelGet=async path=>{
    const key=$('privateKey')?.value.trim(),website=$('url')?.value.trim();
    if(!key||!website)throw Error('Enter the access key and website first.');
    const res=await fetch(path+(path.includes('?')?'&':'?')+'website='+encodeURIComponent(website),{headers:{'X-GrowthLens-Key':key}});
    const data=await res.json();if(!res.ok)throw Error(data.detail||'Request failed');return data;
  };
  const showIntel=(id,data)=>{const el=$(id);el.replaceChildren();const pre=document.createElement('pre');pre.style.whiteSpace='pre-wrap';pre.style.overflowWrap='anywhere';pre.textContent=JSON.stringify(data,null,2);el.append(pre);};
  $('neuralSearch').onclick=async()=>{try{
    const query=$('neuralQuery').value.trim();if(query.length<2)throw Error('Enter a question.');
    const data=await intelGet('/api/intelligence/evidence-ranking?query='+encodeURIComponent(query));
    showIntel('neuralResults',data);
  }catch(e){$('neuralResults').textContent=String(e.message);}};
  $('historyCompare').onclick=async()=>{try{showIntel('neuralResults',await intelGet('/api/intelligence/history-changes'));}
    catch(e){$('neuralResults').textContent=String(e.message);}};
  $('outcomeSave').onclick=async()=>{try{
    const key=$('privateKey')?.value.trim(),website=$('url')?.value.trim();
    if(!key||!website)throw Error('Enter the access key and website first.');
    const baseline=$('outcomeBaseline').value,observed=$('outcomeObserved').value;
    if(!baseline.trim()||!observed.trim())throw Error('Enter before and after measurements.');
    const res=await fetch('/api/intelligence/outcomes',{method:'POST',headers:{'Content-Type':'application/json','X-GrowthLens-Key':key},
      body:JSON.stringify({website,recommendation_id:$('outcomeId').value.trim(),metric:$('outcomeMetric').value.trim(),
      baseline:Number(baseline),observed:Number(observed),direction:$('outcomeDirection').value,
      source_url:$('outcomeSource').value.trim()})});
    const data=await res.json();if(!res.ok)throw Error(JSON.stringify(data.detail||'Unable to record outcome'));
    showIntel('outcomeResults',data);
  }catch(e){$('outcomeResults').textContent=String(e.message);}};
  $('outcomeLoad').onclick=async()=>{try{showIntel('outcomeResults',await intelGet('/api/intelligence/outcomes'));}
    catch(e){$('outcomeResults').textContent=String(e.message);}};
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
      const names={website:'Website intelligence',discovery:'Competitor discovery',pagespeed_mobile:'Mobile performance',pagespeed_desktop:'Desktop performance',corporate_filings:'SEC public-company filings',crux_mobile:'Real-user mobile experience',crux_desktop:'Real-user desktop experience',verification:'Evidence verification',opportunities:'Growth opportunities'};
      $('publicIntelOutput').replaceChildren();
      const heading=document.createElement('h3');heading.textContent='Independent public intelligence';$('publicIntelOutput').append(heading);
      const skipped=[];
      for (const [id,result] of Object.entries(data.engines||{})) {
        if(result.status==='not_requested'||result.status==='not_configured'){skipped.push(names[id]||id);continue;}
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
      if(data.memory){const memory=document.createElement('p');memory.className='muted';memory.textContent='Intelligence memory: '+data.memory.prior_observations+' previous observations; '+data.memory.new_observations+' new; '+(data.memory.persistent?'persistent storage':'temporary local storage')+'; '+(data.memory.neural_embeddings?'neural embeddings':'deterministic embeddings (neural inference unavailable)')+'.';$('publicIntelOutput').append(memory);}
      $('publicIntelStatus').textContent='Analysis complete. '+(skipped.length?skipped.length+' optional sources skipped (not configured or not applicable). ':'')+'Unavailable provider results are not scored as zero.';
    } catch(e) { $('publicIntelStatus').textContent=String(e.message); }
    finally { $('publicIntelRun').disabled=false; }
  };
})()
