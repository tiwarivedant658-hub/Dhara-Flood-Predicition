const state={map:null,markers:{},riskById:{},activeId:null,refreshMs:300000,stateFilter:'all',satellite:false,satelliteLayer:null,streetLayer:null};
const BAND_COLORS={green:'#2E7D4F',yellow:'#D9A400',orange:'#E07A1F',red:'#C13B2E',maroon:'#7A2020'};
const $=s=>document.querySelector(s);
function el(tag,cls,html){const e=document.createElement(tag);if(cls)e.className=cls;if(html!==undefined)e.innerHTML=html;return e}
function setStatus(kind,text){const dot=$('#live-dot');dot.className='status-dot '+(kind==='live'?'live':kind==='down'?'down':'');$('#status-text').textContent=text}
function tickClock(){$('#clock').textContent=new Date().toLocaleTimeString('en-IN',{hour12:false})}setInterval(tickClock,1000);tickClock();

function initMap(){
 state.map=L.map('map',{zoomControl:true,preferCanvas:true}).setView([32.4,77.5],6);
 state.streetLayer=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; OpenStreetMap contributors',maxZoom:18});
 state.satelliteLayer=null;
 state.streetLayer.addTo(state.map);
}
function setSatellite(on){state.satellite=!!on;if(state.satellite){state.map.removeLayer(state.streetLayer);state.satelliteLayer.addTo(state.map)}else{state.map.removeLayer(state.satelliteLayer);state.streetLayer.addTo(state.map)}
 document.querySelectorAll('.view-btn').forEach(b=>b.classList.toggle('active',b.id===(on?'satellite-btn':'overview-btn')));$('#map-mode-label').textContent=on?'Satellite imagery':'Street / terrain';}
function riskPinIcon(color){return L.divIcon({className:'',html:`<div class="risk-pin" style="background:${color}"></div>`,iconSize:[18,18],iconAnchor:[9,17]})}
async function loadConfig(){try{const r=await fetch('/api/config');const c=await r.json();state.refreshMs=(c.refresh_interval_seconds||300)*1000;state.satelliteLayer=L.tileLayer(c.satellite_tile_url,{attribution:c.satellite_attribution,maxZoom:18})}catch(e){console.warn(e);state.satelliteLayer=L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{attribution:'&copy; Esri, Maxar, Earthstar Geographics, and the GIS User Community',maxZoom:18})}}
async function loadLocationsAndRisk(){setStatus('loading','Fetching live rainfall + soil data…');try{const res=await fetch('/api/risk-data');if(!res.ok)throw Error('risk-data failed');const data=await res.json();data.results.forEach(item=>{state.riskById[item.id]=item;upsertMarker(item)});renderSidebar();renderDashboard(data.results);if(state.activeId)renderDetail(state.activeId);const offline=data.results.some(r=>r.risk.live.source.includes('unreachable'));const now=new Date().toLocaleTimeString('en-IN',{hour12:false});$('#sidebar-update').textContent=now;setStatus(offline?'down':'live',offline?'Live feed unreachable – showing fallback values':`Live • ${data.results.length} locations • updated ${now}`)}catch(err){console.error(err);setStatus('down','Could not reach the backend API. Is Flask running?')}}
function upsertMarker(item){const color=BAND_COLORS[item.risk.level]||'#888';if(state.markers[item.id]){state.markers[item.id].setIcon(riskPinIcon(color));state.markers[item.id].setPopupContent(popupHtml(item));return}const marker=L.marker([item.lat,item.lon],{icon:riskPinIcon(color)}).addTo(state.map);marker.bindPopup(popupHtml(item));marker.on('click',()=>selectLocation(item.id));state.markers[item.id]=marker}
function popupHtml(item){const c=BAND_COLORS[item.risk.level]||'#888';const p=item.prediction||item.risk.prediction||{};return `<div class="popup-title">${item.name}</div><div>${item.state}</div><div class="popup-band" style="color:${c}">${p.label||item.risk.label} · ${p.probability??item.risk.score}% next 6h</div>`}
function renderSidebar(){const list=$('#location-list');list.innerHTML='';const items=Object.values(state.riskById).filter(it=>state.stateFilter==='all'||it.state===state.stateFilter).sort((a,b)=>b.risk.score-a.risk.score);if(!items.length){list.appendChild(el('li','skeleton','No locations match this filter.'));return}items.forEach(item=>{const li=el('li','location-item'+(item.id===state.activeId?' active':''));const color=BAND_COLORS[item.risk.level]||'#888';li.innerHTML=`<span class="dot" style="background:${color}"></span><span class="li-text"><span class="li-name">${item.name}</span><span class="li-state">${item.state}</span></span><span class="li-score">${item.risk.score}</span>`;li.onclick=()=>selectLocation(item.id);list.appendChild(li)})}
$('#state-filter').addEventListener('change',e=>{state.stateFilter=e.target.value;renderSidebar()});

function destroyCharts(){
  if(window.riskBarChart){window.riskBarChart.destroy();window.riskBarChart=null;}
  if(window.riskPieChart){window.riskPieChart.destroy();window.riskPieChart=null;}
}

function renderCharts(results, counts){
  if(typeof Chart==='undefined') return;
  destroyCharts();
  const palette=[BAND_COLORS.green,BAND_COLORS.yellow,BAND_COLORS.orange,BAND_COLORS.red,BAND_COLORS.maroon];
  const top=[...results].sort((a,b)=>b.risk.score-a.risk.score).slice(0,8);
  const barCtx=$('#risk-bar-chart');
  if(barCtx){
    window.riskBarChart=new Chart(barCtx,{type:'bar',data:{labels:top.map(x=>x.name),datasets:[{label:'Next 6h prediction %',data:top.map(x=>(x.prediction||x.risk.prediction).probability),backgroundColor:top.map(x=>BAND_COLORS[x.risk.level]||BAND_COLORS.green),borderRadius:5,borderSkipped:false}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:(ctx)=>` Predicted probability: ${ctx.raw}%`}}},scales:{x:{beginAtZero:true,max:100,grid:{color:'rgba(33,43,34,.08)'},ticks:{color:'#5B6459',font:{size:10}}},y:{grid:{display:false},ticks:{color:'#212B22',font:{size:10}}}}}});
  }
  const pieCtx=$('#risk-pie-chart');
  if(pieCtx){
    window.riskPieChart=new Chart(pieCtx,{type:'pie',data:{labels:['Safe','Watch','Warning','Danger','Severe'],datasets:[{data:[counts.green,counts.yellow,counts.orange,counts.red,counts.maroon],backgroundColor:palette,borderColor:'#F4F5EF',borderWidth:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{color:'#212B22',boxWidth:11,padding:10,font:{size:10}}}}}});
    const total=results.length;const center=$('#pie-center');if(center)center.innerHTML=`<strong>${total}</strong><span>locations</span>`;
  }
}

function renderDashboard(results){
  if(!results.length)return;
  const highest=[...results].sort((a,b)=>b.risk.score-a.risk.score)[0];
  const rain=Math.max(...results.map(x=>x.risk.live.rainfall_next_6h_mm||0));
  const soil=Math.round(results.reduce((a,x)=>a+(x.risk.live.soil_moisture_0_7cm||0),0)/results.length*100);
  const alerts=results.filter(x=>x.risk.score>=25).length;
  $('#kpi-risk').textContent=`${(highest.prediction||highest.risk.prediction).probability}%`;
  $('#kpi-risk-sub').textContent=`${highest.name} · ${(highest.prediction||highest.risk.prediction).label} prediction`;
  $('#kpi-rain').textContent=`${rain.toFixed(1)} mm`;
  $('#kpi-rain-sub').textContent='Highest forecast accumulation · next 6h';
  $('#kpi-soil').textContent=`${soil}%`;
  $('#kpi-soil-sub').textContent='Average shallow soil moisture';
  $('#kpi-alerts').textContent=alerts;
  $('#kpi-alerts-sub').textContent=`of ${results.length} locations · next 6h`;
  const counts={green:0,yellow:0,orange:0,red:0,maroon:0};
  results.forEach(x=>counts[x.risk.level]=(counts[x.risk.level]||0)+1);
  const dist=$('#risk-distribution');
  if(dist)dist.innerHTML=`<div class="distribution">${Object.entries(counts).map(([k,v])=>`<span title="${k}: ${v}" style="background:${BAND_COLORS[k]};flex:${v||.01}"></span>`).join('')}</div><div class="distribution-legend">${[['green','Safe'],['yellow','Watch'],['orange','Warning'],['red','Danger'],['maroon','Severe']].map(([k,l])=>`<div class="dist-item"><b>${counts[k]}</b>${l}</div>`).join('')}</div>`;
  const top=[...results].sort((a,b)=>b.risk.score-a.risk.score).slice(0,6);
  $('#priority-list').innerHTML=top.map((x,i)=>`<div class="priority-item" data-id="${x.id}"><span class="rank">0${i+1}</span><div><strong>${x.name}</strong><span>${x.state} · ${x.risk.label}</span></div><span class="priority-score">${x.risk.score}</span></div>`).join('');
  document.querySelectorAll('.priority-item').forEach(x=>x.onclick=()=>selectLocation(x.dataset.id));
  renderCharts(results,counts);
}
async function selectLocation(id){state.activeId=id;renderSidebar();const marker=state.markers[id];if(!marker)return;if(window.closeChatIfOpen)window.closeChatIfOpen();const target=marker.getLatLng();state.map.flyTo(target,Math.max(state.map.getZoom(),13),{duration:.65});state.map.once('moveend',()=>marker.openPopup());await renderDetail(id)}
async function renderDetail(id){$('#detail-empty').hidden=true;const content=$('#detail-content');content.hidden=false;content.innerHTML='<p class="skeleton">Loading city intelligence…</p>';try{const res=await fetch(`/api/risk-data/${id}`);if(!res.ok)throw Error();const item=await res.json();const r=item.risk,live=r.live,color=BAND_COLORS[r.level]||'#888';content.innerHTML=`
 <p class="section-kicker">PREDICTIVE CITY INTELLIGENCE</p><div class="detail-state">${item.state} · ${item.district}</div><div class="detail-hero"><div><h3 class="detail-name">${item.name}</h3><span class="band-badge" style="background:${color}">${r.label}<span class="score">${r.score}/100</span></span></div><div class="detail-hero-actions"><div class="detail-risk-number">${(r.prediction||{}).probability ?? r.score}<small>%</small></div><a class="report-btn" href="/api/report/${item.id}" title="Download district prediction report as PDF">↓ Prediction report</a></div></div>
 <p class="band-desc">${r.description}</p>
 <div class="prediction-card"><div class="prediction-head"><div><p class="section-kicker">MODEL FORECAST</p><h4>Next 6-hour flash-flood probability</h4></div><div class="prediction-probability">${(r.prediction||{}).probability ?? r.score}<small>%</small></div></div><div class="prediction-meta"><span>Prediction horizon <b>6 hours</b></span><span>Estimated lead time <b>${(r.prediction||{}).lead_time?.label||'Unknown'}</b></span><span>Data confidence <b>${(r.prediction||{}).confidence||'—'}%</b></span></div><div class="forecast-strip">${((live.forecast_hourly_precipitation||[]).slice(0,6)).map((v,i)=>`<div><span>+${i+1}h</span><b>${Number(v||0).toFixed(1)}</b><small>mm</small></div>`).join('')}</div><p class="model-note">${(r.prediction||{}).model||'DHARA predictive engine'} · Confidence reflects input completeness, not field accuracy.</p></div>
 <div class="metric-grid"><div class="metric-box"><div class="m-label">Rain · next 6h</div><div class="m-value">${live.rainfall_next_6h_mm} mm</div></div><div class="metric-box"><div class="m-label">Rain · next 24h</div><div class="m-value">${live.rainfall_next_24h_mm} mm</div></div><div class="metric-box"><div class="m-label">Peak hourly</div><div class="m-value">${live.max_hourly_intensity_mm} mm/hr</div></div><div class="metric-box"><div class="m-label">Soil moisture</div><div class="m-value">${(live.soil_moisture_0_7cm*100).toFixed(0)}%</div></div></div>
 <div class="factor-bars"><div class="evidence-heading"><div><h4>Why the model is leaning this way</h4><p>Top feature contributions from the predictive model.</p></div></div>${((r.prediction||{}).drivers||[]).map(d=>factorRow(d.name,d.importance)).join('')}</div>
 <div class="terrain-facts"><div><span>River basin</span><span>${item.river_basin||'—'}</span></div><div><span>Slope class</span><span>${item.slope_class||'—'}</span></div><div><span>Soil type</span><span>${item.soil_type||'—'}</span></div><div><span>Elevation</span><span>${item.elevation_m?item.elevation_m+' m':'—'}</span></div></div>
 <div class="emergency-section"><div class="evidence-heading"><div><h4>Emergency contacts</h4><p>Quick access to national, state and district response teams.</p></div><span class="evidence-tip">Tap a number to call</span></div><div id="emergency-contacts" class="emergency-grid"><div class="evidence-empty">Loading emergency contacts…</div></div><div id="contact-source-note" class="contact-source-note"></div><div id="official-links" class="official-links"><div class="evidence-heading"><div><h4>Official help & complaints</h4><p>Open the official NDRF, state disaster-management and grievance portals.</p></div></div><div id="official-links-grid" class="official-links-grid"><div class="evidence-empty">Loading official links…</div></div></div></div>
 <div class="satellite-card"><div class="satellite-preview"><span class="sat-marker"></span></div><div class="satellite-actions"><span>Satellite context · ${item.lat.toFixed(3)}, ${item.lon.toFixed(3)}</span><button id="detail-satellite">Open map</button></div></div>
 <div class="evidence-section"><div class="evidence-heading"><div><h4>Field photos</h4><p>Real observations can sit beside the modelled numbers.</p></div><span class="evidence-tip">JPG · PNG · WEBP · up to 8 MB</span></div><div id="evidence-grid" class="evidence-grid"><div class="evidence-empty">Loading field photos…</div></div><div class="evidence-actions"><select id="evidence-category" aria-label="Photo category"><option value="soil">Soil</option><option value="terrain">Terrain / slope</option><option value="river">River / drainage</option><option value="landuse">Land use / vegetation</option><option value="flood_evidence">Flood evidence</option></select><label class="upload-photo-btn" for="evidence-input">＋ Add field photo<input id="evidence-input" type="file" accept="image/jpeg,image/png,image/webp" capture="environment"></label></div><div id="upload-preview" class="upload-preview" hidden></div></div>
 <div class="data-source-note">Forecast source: ${live.source==='open-meteo-live'?'Open-Meteo':'fallback'} · updated ${live.fetched_at?new Date(live.fetched_at*1000).toLocaleTimeString('en-IN'):'—'}. Terrain reference values are prototype baselines.</div>`;
 $('#detail-satellite').onclick=()=>{setSatellite(true);state.map.flyTo([item.lat,item.lon],15,{duration:.8})};$('#evidence-input').addEventListener('change',e=>{const f=e.target.files&&e.target.files[0];if(f){showUploadPreview(f,$('#evidence-category').value);uploadEvidence(id,$('#evidence-category').value,f)}});$('#evidence-category').addEventListener('change',()=>{const input=$('#evidence-input');if(input)input.value=''});loadEvidence(id);loadEmergencyContacts(id)
 }catch(e){content.innerHTML='<p class="skeleton">Could not load city intelligence.</p>'}}
function factorRow(label,value){return `<div class="factor-row"><div class="f-label"><span>${label}</span><span>${value}</span></div><div class="factor-track"><div class="factor-fill" style="width:${value}%"></div></div></div>`}
async function loadEvidence(id){const grid=$('#evidence-grid');if(!grid)return;try{const r=await fetch(`/api/evidence/${id}`),d=await r.json();if(!d.items.length){grid.innerHTML='<div class="evidence-empty" style="grid-column:1/-1">No field photos yet. Add soil, terrain, river, land-use or flood evidence for this city.</div>';return}grid.innerHTML=d.items.map(x=>`<div class="evidence-card"><img src="${x.image_url}?t=${x.uploaded_at}" alt="${x.category_label} evidence"><div class="ev-body"><strong>${x.category_label}</strong><span>${new Date(x.uploaded_at*1000).toLocaleDateString('en-IN')}</span></div></div>`).join('')}catch(e){grid.innerHTML='<div class="evidence-empty">Evidence service unavailable.</div>'}}
async function loadEmergencyContacts(id){const grid=$('#emergency-contacts');const note=$('#contact-source-note');const linksGrid=$('#official-links-grid');if(!grid)return;try{const r=await fetch(`/api/emergency-contacts/${id}`),d=await r.json();if(!r.ok)throw Error(d.error||'Unable to load contacts');grid.innerHTML=d.contacts.map(c=>`<a class="emergency-card emergency-${c.type||'general'}" href="tel:${c.phone.replace(/[^0-9+]/g,'')}"><strong>${c.name}</strong><span>${c.service}</span><b>${c.phone}</b></a>`).join('');if(note)note.textContent=d.source_note||'Verify local contacts before operational use.';if(linksGrid){linksGrid.innerHTML=(d.official_links||[]).map(c=>`<a class="official-link-card official-${c.type||'website'}" href="${c.url}" target="_blank" rel="noopener noreferrer"><strong>${c.name}</strong><span>${c.service}</span><b>Open official site ↗</b></a>`).join('')||'<div class="evidence-empty">No official web links configured for this state.</div>'}}catch(e){grid.innerHTML=`<div class="evidence-empty" style="grid-column:1/-1">${e.message}</div>`;if(linksGrid)linksGrid.innerHTML='<div class="evidence-empty">Official links unavailable.</div>'}}
function showUploadPreview(file,category){
 const preview=$('#upload-preview'); if(!preview)return;
 const url=URL.createObjectURL(file); preview.hidden=false; preview.innerHTML=`<img src="${url}" alt="Selected ${category} photo"><div><strong>Ready to add</strong><span>${file.name} · ${category}</span></div>`;
}
async function uploadEvidence(id,category,file){const grid=$('#evidence-grid');if(grid)grid.innerHTML='<div class="evidence-empty" style="grid-column:1/-1">Uploading and storing field evidence…</div>';const fd=new FormData();fd.append('photo',file);try{const r=await fetch(`/api/evidence/${id}/${category}`,{method:'POST',body:fd});const d=await r.json();if(!r.ok)throw Error(d.error||'Upload failed');loadEvidence(id)}catch(e){if(grid)grid.innerHTML=`<div class="evidence-empty" style="grid-column:1/-1">${e.message}</div>`}}

$('#overview-btn').onclick=()=>setSatellite(false);$('#satellite-btn').onclick=()=>setSatellite(true);$('#satellite-small').onclick=()=>setSatellite(!state.satellite);$('#locate-active').onclick=()=>{if(state.activeId)selectLocation(state.activeId)};
async function boot(){initMap();await loadConfig();await loadLocationsAndRisk();setInterval(loadLocationsAndRisk,state.refreshMs)}boot();
