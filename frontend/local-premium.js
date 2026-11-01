/* GrowthLens premium private beta: evidence-first local market explorer and editable what-if math. */
(() => {
  'use strict';
  const panel = document.getElementById('localCompetition');
  if (!panel) return;
  const style = document.createElement('style');
  style.textContent = `
    #glPremium{margin:22px 0}
    #glPremium .gl-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px;margin:12px 0 20px}
    #glPremium .gl-kpi{border:1px solid #41616c;border-radius:12px;padding:15px;background:#0c212b}
    #glPremium .gl-kpi strong{display:block;font-size:1.7rem;color:#73e0c0}
    #glPremium .gl-toolbar{display:flex;flex-wrap:wrap;align-items:end;gap:10px;margin:14px 0}
    #glPremium .gl-toolbar label{flex:1;min-width:135px}
    #glPremium input,#glPremium select{width:100%;max-width:100%;padding:11px;background:#0c1d27;color:#fff;border:1px solid #55727b;border-radius:8px}
    #glPremium table{width:100%;border-collapse:collapse;min-width:580px}
    #glPremium .gl-table-scroll{width:100%;max-width:100%;overflow-x:auto}
    #glPremium th,#glPremium td{text-align:left;padding:9px;border-bottom:1px solid #33515b;vertical-align:top}
    #glPremium .gl-alert{color:#e8bfa9;font-size:.86rem}
    #glPremium .gl-box{border:1px solid #33515b;border-radius:11px;padding:18px;margin:16px 0}
    #glPremium .gl-help{font-size:.84rem;color:#a5bac2}
    #glPremium .gl-calculator{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px}
    #glPremium .gl-result{font-size:1.4rem;font-weight:800;color:#73e0c0}
    @media print{#glPremium{break-before:page}#glPremium .gl-toolbar,#glPremium .gl-calculator{display:none!important}#glPremium .gl-table-scroll{overflow:visible}#glPremium table{min-width:0;font-size:9pt}#glPremium .gl-box{break-inside:avoid}#glPremium .gl-kpi{background:white!important;color:#142a35!important}}
  `;
  document.head.appendChild(style);
  const element = (tag, cls, value) => {
    const el=document.createElement(tag);
    if (cls) el.className=cls;
    if (value!==undefined) el.textContent=String(value);
    return el;
  };
  const money = n => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n);
  const finite = (value,min,max) => {
    const n=Number(value);
    return Number.isFinite(n) && n>=min && n<=max ? n : null;
  };
  const metric = (root,label,value) => {
    const card=element('div','gl-kpi');
    card.append(element('strong','',value),element('span','',label));
    root.append(card);
  };
  const input = (id,label,value,min,max,step) => {
    const wrap=element('label');
    wrap.append(element('span','',label));
    const field=element('input');
    field.id=id;field.type='number';field.value=String(value);field.min=String(min);field.max=String(max);field.step=String(step);
    wrap.append(field);return wrap;
  };
  function renderPremium(data) {
    document.getElementById('glPremium')?.remove();
    const root=element('section'); root.id='glPremium';
    const output=document.getElementById('localOutput');
    if (!output) return;
    output.append(root);
    root.append(element('h2','', 'Market intelligence overview'));
    root.append(element('p','gl-help','Public listings and single-page evidence only. Comparisons are not a market-share, rankings, or sales measurement.'));
    const rivals=Array.isArray(data.competitors)?data.competitors:[];
    const scanned=rivals.filter(c=>c.status==='audited');
    const kpis=element('div','gl-kpis');
    metric(kpis,'Listings discovered',rivals.length);
    metric(kpis,'Websites audited',scanned.length);
    metric(kpis,'Listings without websites',rivals.filter(c=>!c.website).length);
    metric(kpis,'Homepage gaps to investigate',(data.feature_comparison||[]).filter(f=>!f.target_observed && (f.competitors_with_feature||[]).length).length);
    root.append(kpis);
    root.append(element('h3','', 'Business explorer'));
    const toolbar=element('div','gl-toolbar');
    const search=element('input'); search.placeholder='Search business names';search.setAttribute('aria-label','Search businesses');
    const searchLabel=element('label');searchLabel.append(element('span','','Business search'),search);
    const filter=element('select'); filter.setAttribute('aria-label','Filter audit coverage');
    for(const [v,t] of [['all','All listings'],['audited','Audited websites'],['no-site','Without listed website'],['not-audited','Not audited']]) {
      const o=element('option','',t);o.value=v;filter.append(o);
    }
    const filterLabel=element('label');filterLabel.append(element('span','','Coverage'),filter);
    const sort=element('select');sort.setAttribute('aria-label','Sort competitors');
    for(const [v,t] of [['distance','Closest'],['name','Business A–Z'],['score','Highest technical score']]) {
      const o=element('option','',t);o.value=v;sort.append(o);
    }
    const sortLabel=element('label');sortLabel.append(element('span','','Sort'),sort);
    toolbar.append(searchLabel,filterLabel,sortLabel);root.append(toolbar);
    const scroll=element('div','gl-table-scroll');
    const table=element('table');
    const head=element('thead');const hrow=element('tr');
    for(const name of ['Business','Distance','Single-page score','Website','Coverage'])hrow.append(element('th','',name));
    head.append(hrow);
    const body=element('tbody');table.append(head,body);scroll.append(table);root.append(scroll);
    const count=element('p','gl-help');
    root.append(count);
    function paint() {
      let rows=rivals.filter(c=>String(c.name||'').toLowerCase().includes(search.value.toLowerCase()));
      rows=rows.filter(c=>filter.value==='all'||(filter.value==='audited'&&c.status==='audited')||(filter.value==='no-site'&&!c.website)||(filter.value==='not-audited'&&c.status!=='audited'));
      rows=[...rows].sort((a,b)=>sort.value==='name'?String(a.name).localeCompare(String(b.name)):sort.value==='score'?(b.score??-1)-(a.score??-1):(a.distance_miles??Infinity)-(b.distance_miles??Infinity));
      body.replaceChildren();
      for(const c of rows){
        const tr=element('tr');
        tr.append(element('td','',c.name||'Unnamed'),element('td','',c.distance_miles==null?'Unknown':c.distance_miles+' mi'),element('td','',c.score==null?'N/A':c.score+'/100'));
        const site=element('td');
        if(c.website && /^https?:\/\//i.test(c.website)){
          const a=element('a','','Visit site');a.href=c.website;a.target='_blank';a.rel='noopener noreferrer';site.append(a);
        } else site.textContent='Not listed';
        tr.append(site,element('td','',c.status||'Unknown'));body.append(tr);
      }
      count.textContent=rows.length+' of '+rivals.length+' listings shown; coverage may be incomplete.';
    }
    for(const ctl of [search,filter,sort])ctl.addEventListener(ctl===search?'input':'change',paint);
    paint();
    root.append(element('h3','', 'Evidence-linked feature comparison'));
    root.append(element('p','gl-help','Observed means visible on one audited page; not observed does not establish absence across the website. Unknown means no usable page evidence.'));
    const evidence=element('div','gl-box');
    for(const item of data.feature_comparison||[]) {
      const paragraph=element('p');
      paragraph.append(element('strong','',item.feature+': '),element('span','',item.target_observed?'Observed on target homepage':'Not observed on target homepage'));
      const known=item.competitor_details||[];
      const matching=known.filter(x=>x.status==='observed');
      if(matching.length){
        paragraph.append(element('span','', ' · Observed at: '));
        matching.forEach((x,i)=>{
          if(i) paragraph.append(element('span','',', '));
          if(x.evidence_url && /^https?:\/\//i.test(x.evidence_url)) {
            const link=element('a','',x.name||'Competitor');link.href=x.evidence_url;link.target='_blank';link.rel='noopener noreferrer';paragraph.append(link);
          } else paragraph.append(element('span','',x.name||'Competitor'));
        });
      }
      const unknown=known.filter(x=>x.status==='unknown').length;
      if(unknown) paragraph.append(element('small','gl-help',' · '+unknown+' competitor pages unknown'));
      evidence.append(paragraph);
    }
    if(!(data.feature_comparison||[]).length)evidence.append(element('p','gl-help','No industry-specific feature evidence is available.'));
    root.append(evidence);
    root.append(element('h3','', 'Prioritized opportunity playbooks'));
    const playbooks=element('ol','gl-box');
    const issues=(data.opportunities||[]).slice(0,6);
    for(const issue of issues){
      const li=element('li');
      li.append(element('strong','',issue.issue||'Technical issue'),element('p','',issue.recommendation||'Investigate this finding'));
      li.append(element('p','gl-help','Confidence: limited to audited page evidence. Effort: confirm scope, implement fix, and validate.'));
      li.append(element('p','gl-help','Measure success: repeat audit, verify the affected element, and monitor real first-party conversions if available.'));
      playbooks.append(li);
    }
    if(!issues.length)playbooks.append(element('li','', 'No failed target-page checks to prioritize.'));
    root.append(playbooks);
    root.append(element('h3','', 'Financial what-if simulator'));
    root.append(element('p','gl-alert','Not a verified loss. No competitor financial performance was measured. These figures use only your own editable hypothetical inputs and cannot predict sales.'));
    const calculator=element('div','gl-calculator');
    for(const spec of [
      ['glVisits','Monthly website visits (input)',1000,0,100000000,1],
      ['glConversion','Baseline conversion rate (%)',2,0,100,.1],
      ['glValue','Revenue per conversion ($)',150,0,100000000,1],
      ['glUplift','Hypothetical relative conversion improvement (%)',10,0,1000,1],
      ['glCost','One-time implementation cost ($)',1000,0,100000000,1],
      ['glDelay','Delay before improvement (months)',1,0,12,1]
    ])calculator.append(input(...spec));
    root.append(calculator);
    const result=element('p','gl-result');
    const note=element('p','gl-help','Revenue, not profit. No statistical confidence or causal lift is established. Do not combine with automatic scenario rows.');
    root.append(result,note);
    const update=()=>{
      const vals=['glVisits','glConversion','glValue','glUplift','glCost','glDelay'].map((id,i)=>finite(document.getElementById(id)?.value,0,[1e8,100,1e8,1000,1e8,12][i]));
      if(vals.some(v=>v===null)){result.textContent='Enter valid nonnegative values within each field range.';return;}
      const [visits,conversion,value,lift,cost,delay]=vals;
      const annualIncrement=visits*12*(conversion/100)*(lift/100)*value;
      const firstYear=Math.max(0,12-delay)/12*annualIncrement-cost;
      result.textContent=money(firstYear)+' illustrative first-year revenue less implementation cost';
    };
    calculator.querySelectorAll('input').forEach(el=>el.addEventListener('input',update));
    update();
    root.append(element('p','gl-help','Source coverage: '+String(data.discovery_source||'Unspecified')+'. Generated values are illustrative unless independently verified.'));
  }
  panel.addEventListener('growthlens:report',e=>renderPremium(e.detail||{}));
})();
