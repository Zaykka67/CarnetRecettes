/* Carnet de recettes — interface */
'use strict';

/* ---------- Données de référence ---------- */
const SEASONS = [
  {k:'printemps', label:'Printemps', c:'var(--spring)'},
  {k:'ete', label:'Été', c:'var(--summer)'},
  {k:'automne', label:'Automne', c:'var(--autumn)'},
  {k:'hiver', label:'Hiver', c:'var(--winter)'},
];
const SEASON_BY_K = Object.fromEntries(SEASONS.map(s=>[s.k,s]));
const CATEGORIES = ['Apéro','Entrée','Plat','Accompagnement','Dessert','Petit-déj','Boisson','Sauce'];
const MONTHS = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'];
const MAX_SHOTS = 6;
function currentSeason(d=new Date()){
  const md=(d.getMonth()+1)*100+d.getDate();
  if(md>=321 && md<621) return 'printemps';
  if(md>=621 && md<923) return 'ete';
  if(md>=923 && md<1221) return 'automne';
  return 'hiver';
}
const NOW_SEASON = currentSeason();

/* ---------- Utilitaires ---------- */
const $ = (s,r=document)=>r.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ICON = {
  heart:'<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 21s-7.5-4.6-9.6-9.3C.9 8.3 3.1 4.5 6.9 4.5c2.1 0 3.6 1.1 5.1 3 1.5-1.9 3-3 5.1-3 3.8 0 6 3.8 4.5 7.2C19.5 16.4 12 21 12 21z"/></svg>',
  heartO:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20s-7-4.3-9-8.7C1.6 8.1 3.6 5 6.9 5c2 0 3.5 1.1 5.1 3 1.6-1.9 3.1-3 5.1-3 3.3 0 5.3 3.1 3.9 6.3C19 15.7 12 20 12 20z"/></svg>',
  back:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>',
  link:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>',
  pen:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4L19 9l-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/></svg>',
  spark:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/></svg>',
  trash:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg>',
  img:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/></svg>',
  check:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 7"/></svg>',
};
function seasonColor(r){ const s=(r.seasons||[]); return s.length && s.length<4 ? SEASON_BY_K[s[0]]?.c : 'var(--year)'; }
function platformOf(url){
  if(!url) return '';
  try{ const h=new URL(url).hostname.replace(/^www\./,'');
    if(h.includes('tiktok')) return 'TikTok';
    if(h.includes('instagram')) return 'Instagram';
    if(h.includes('youtu')) return 'YouTube';
    if(h.includes('facebook')||h.includes('fb.watch')) return 'Facebook';
    if(h.includes('pinterest')||h.includes('pin.it')) return 'Pinterest';
    return h;
  }catch{ return 'Lien'; }
}
function safeUrl(u){ try{ const x=new URL(u); return /^https?:$/.test(x.protocol) ? x.href : ''; }catch{ return ''; } }
function photoSrc(r){ return r?.photo?.id ? '/photos/'+encodeURIComponent(r.photo.id) : ''; }
function placeholder(r){ const t=(r.title||'?').trim(); return `<div class="ph" style="--c:${seasonColor(r)}"><span>${esc(t.charAt(0).toUpperCase()||'?')}</span></div>`; }
function totalTime(r){ const t=(+r.prepMin||0)+(+r.cookMin||0); if(!t) return ''; if(t<60) return t+' min'; const h=Math.floor(t/60), m=t%60; return h+' h'+(m?' '+String(m).padStart(2,'0'):''); }
function fmtNum(q){
  if(q==null || q==='' || isNaN(q)) return '';
  const fr=[[.25,'¼'],[.5,'½'],[.75,'¾'],[1/3,'⅓'],[2/3,'⅔']];
  const whole=Math.floor(q), rest=q-whole;
  for(const [v,s] of fr){ if(Math.abs(rest-v)<.04) return (whole? whole+' ':'')+s; }
  if(q>=50) return String(Math.round(q/5)*5);
  if(q>=10) return String(Math.round(q));
  return String(Math.round(q*10)/10).replace('.',',');
}
function de(name){ return /^[aeiouyhéèêàâîïôœ]/i.test(name) ? "d'"+name : 'de '+name; }
function ingDisplay(i, factor=1){
  const q = i.qty!=null && i.qty!=='' ? fmtNum(i.qty*factor) : '';
  if(!q) return {q:'', t:i.name};
  if(i.unit) return {q:q+' '+i.unit, t:de(i.name)};
  return {q, t:i.name};
}
const UNIT_RE = /^(kg|mg|g|ml|cl|dl|l|c\.?\s?à\s?s\.?|c\.?\s?à\s?c\.?|càs|càc|cs|cc|cuill[eè]res?\s+à\s+soupe|cuill[eè]res?\s+à\s+caf[eé]|pinc[ée]es?|sachets?|tranches?|gousses?|brins?|verres?|tasses?|bottes?|feuilles?|bo[iî]tes?|pots?|poign[ée]es?|filets?|morceaux?)(?=[\s.]|$)\.?\s*/i;
function normUnit(u){
  const x=u.toLowerCase().replace(/\s+/g,' ');
  if(/^(c\.?\s?à\s?s\.?|càs|cs|cuill[eè]res?\s+à\s+soupe)$/.test(x)) return 'c. à s.';
  if(/^(c\.?\s?à\s?c\.?|càc|cc|cuill[eè]res?\s+à\s+caf[eé])$/.test(x)) return 'c. à c.';
  return x;
}
function toNum(s){ const map={'½':.5,'¼':.25,'¾':.75,'⅓':1/3,'⅔':2/3}; if(map[s]!=null) return map[s];
  if(s.includes('/')){ const [a,b]=s.split('/').map(v=>parseFloat(v)); return b? a/b : null; }
  const n=parseFloat(s.replace(',','.')); return isNaN(n)?null:n; }
function parseIng(line){
  const s=line.trim().replace(/^[-•*·]\s*/,''); if(!s) return null;
  let qty=null, unit='', rest=s;
  const m=s.match(/^(\d+(?:[.,]\d+)?(?:\s*\/\s*\d+)?|[½¼¾⅓⅔])\s*(.*)$/);
  if(m){ qty=toNum(m[1].replace(/\s/g,'')); rest=m[2]; const u=rest.match(UNIT_RE); if(u){ unit=normUnit(u[1]); rest=rest.slice(u[0].length); } rest=rest.replace(/^(de |d['’])/i,''); }
  return {qty, unit, name:rest.trim()||s};
}
function ingToLine(i){ const q=i.qty!=null&&i.qty!==''? fmtNum(i.qty) : ''; if(q&&i.unit) return q+' '+i.unit+' '+de(i.name||''); return [q, i.name||''].filter(Boolean).join(' '); }
function cleanStep(s){ return s.replace(/^\s*(?:\d+[.)-]|[-•*·]|étape\s*\d+\s*:?)\s*/i,'').trim(); }

let toastT;
function toast(msg){ const t=$('#toast'); t.textContent=msg; t.hidden=false; clearTimeout(toastT); toastT=setTimeout(()=>t.hidden=true, 3200); }
function lockScroll(){ document.body.style.overflow = ($('#detail').hidden && $('#editor').hidden && $('#importer').hidden && $('#shopping').hidden && $('#menu').hidden) ? '' : 'hidden'; }

async function resizeImage(file, max=1600, q=.85){
  let bmp; try{ bmp=await createImageBitmap(file,{imageOrientation:'from-image'}); }catch{ bmp=await createImageBitmap(file); }
  const sc=Math.min(1, max/Math.max(bmp.width,bmp.height));
  const cv=document.createElement('canvas'); cv.width=Math.round(bmp.width*sc); cv.height=Math.round(bmp.height*sc);
  cv.getContext('2d').drawImage(bmp,0,0,cv.width,cv.height);
  return new Promise(res=>cv.toBlob(res,'image/jpeg',q));
}

/* ---------- Serveur ---------- */
let cfg={ai:false, auth:false, loggedIn:true};
let recipes=[], loaded=false, offline=false;
let CACHE_KEY='carnet-cache-v1';

class ApiError extends Error{ constructor(status,msg){ super(msg); this.status=status; } }
async function api(path, opts={}){
  let r;
  try{ r=await fetch(path,{credentials:'same-origin',...opts}); }
  catch(e){ if(e.name==='AbortError') throw e; throw new ApiError(0,'Pas de connexion internet.'); }
  if(r.status===401 && path!=='/api/login' && path!=='/api/signup'){ showLogin(); throw new ApiError(401,'Connexion requise.'); }
  if(!r.ok){ let msg=''; try{ msg=(await r.json()).detail; }catch{} throw new ApiError(r.status, typeof msg==='string'&&msg ? msg : 'Une erreur est survenue ('+r.status+').'); }
  return r.status===204 ? null : r.json();
}
const jsonOpts=(method,body)=>({method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});

async function loadRecipes(){
  try{
    recipes=await api('/api/recipes'); offline=false;
    try{ localStorage.setItem(CACHE_KEY, JSON.stringify(recipes)); }catch{}
  }catch(e){
    if(e.status===401) return;
    offline=true;
    try{ recipes=JSON.parse(localStorage.getItem(CACHE_KEY)||'[]'); }catch{ recipes=[]; }
  }
  loaded=true; render(); if(!$('#detail').hidden) renderDetail();
}
function upsertLocal(rec){ const i=recipes.findIndex(r=>r.id===rec.id); if(i>=0) recipes[i]=rec; else recipes.unshift(rec); try{ localStorage.setItem(CACHE_KEY, JSON.stringify(recipes)); }catch{} }

/* ---------- Liste de courses ---------- */
let shop=[];
let SHOP_KEY='carnet-courses-v1';
const PANTRY=['sel','poivre','eau','sel et poivre','sel, poivre','fleur de sel'];
async function loadShop(){
  try{ shop=await api('/api/shopping'); try{ localStorage.setItem(SHOP_KEY, JSON.stringify(shop)); }catch{} }
  catch(e){ if(e.status===401) return; try{ shop=JSON.parse(localStorage.getItem(SHOP_KEY)||'[]'); }catch{ shop=[]; } }
  renderShopBadge(); if(!$('#shopping').hidden) renderShopping();
}
function setShop(list){ shop=list; try{ localStorage.setItem(SHOP_KEY, JSON.stringify(shop)); }catch{} renderShopBadge(); if(!$('#shopping').hidden) renderShopping(); }
function renderShopBadge(){ const n=shop.filter(i=>!i.checked).length, b=$('#shop-badge'); b.textContent=n; b.hidden=!n; }
function niceQty(q,u){ // 100 cl -> 1 l ; 1500 g -> 1,5 kg
  u=(u||'').toLowerCase();
  if(u==='g' && q>=1000) return [q/1000,'kg'];
  if(u==='cl' && q>=100) return [q/100,'l'];
  if(u==='ml' && q>=1000) return [q/1000,'l'];
  return [q,u||''];
}
function shopLine(i){
  if(i.qty==null || i.qty==='') return {q:'', t:i.name};
  const [q,u]=niceQty(i.qty,i.unit); i={...i, qty:q, unit:u};
  if(i.unit) return {q:fmtNum(i.qty)+' '+i.unit, t:de(i.name)};
  return {q:fmtNum(i.qty), t:i.name};
}

/* Fenêtre « Ajouter aux courses » depuis une recette */
let pick=null;
function openShopPicker(){
  const r=recipes.find(x=>x.id===det.id); if(!r) return;
  const base=+r.servings||0, cur=det.servings||base, factor= base&&cur? cur/base : 1;
  pick={title:r.title, servings:cur, items:(r.ingredients||[]).map(i=>({
    name:i.name, unit:i.unit||'', qty: i.qty!=null && i.qty!=='' ? Math.round(i.qty*factor*100)/100 : null,
    on: !PANTRY.includes((i.name||'').trim().toLowerCase())
  }))};
  if(!pick.items.length){ toast("Cette recette n'a pas d'ingrédients."); return; }
  renderShopPicker();
}
function renderShopPicker(){
  const n=pick.items.filter(i=>i.on).length;
  openDialog(`<h3>Ajouter aux courses</h3>
    <p>${esc(pick.title)}${pick.servings?` · pour ${pick.servings} personne${pick.servings>1?'s':''}`:''}. Décoche ce que tu as déjà${pick.multi?' (les ingrédients communs seront additionnés)':''}.</p>
    <div class="pick-tools"><button type="button" data-act="pick-all">Tout cocher</button><button type="button" data-act="pick-none">Tout décocher</button></div>
    <ul class="pick-list">${pick.items.map((i,k)=>{const d=shopLine(i); return `<li data-pick-ing="${k}" class="${i.on?'on':''}"><span class="check"></span><span class="txt">${d.q?`<span class="q">${esc(d.q)}</span> `:''}${esc(d.t)}${pick.multi&&i.recipe?`<span class="from">${esc(i.recipe)}</span>`:''}</span></li>`;}).join('')}</ul>
    <div class="formbar"><button class="btn" type="button" data-act="close-dlg">Annuler</button><button class="btn primary" type="button" data-act="pick-confirm" ${n?'':'disabled'}>Ajouter ${n} article${n>1?'s':''}</button></div>`);
  $('#dlg-box').classList.add('wide');
}
async function confirmShopPicker(){
  const items=pick.items.filter(i=>i.on).map(({name,qty,unit,recipe})=>({name,qty,unit,recipe}));
  const btn=$('[data-act=pick-confirm]'); if(btn){ btn.disabled=true; btn.textContent='Ajout…'; }
  try{
    setShop(await api('/api/shopping/add', jsonOpts('POST',{recipeTitle:pick.title, items})));
    closeDialog(); toast(pick.multi ? `Ingrédients de la semaine ajoutés à la liste de courses` : `${items.length} article${items.length>1?'s':''} ajouté${items.length>1?'s':''} à la liste de courses`);
  }catch(e){ if(btn){ btn.disabled=false; btn.textContent='Réessayer'; } toast(e.message); }
}

/* Écran liste de courses */
function openShopping(){ renderShopping(); const s=$('#shopping'); s.hidden=false; s.scrollTop=0; lockScroll(); loadShop(); }
function closeShopping(){ $('#shopping').hidden=true; lockScroll(); }
function renderShopping(){
  const s=$('#shopping'), total=shop.length, done=shop.filter(i=>i.checked).length;
  const groups={}; shop.forEach(i=>{ (groups[i.aisle]=groups[i.aisle]||[]).push(i); });
  s.innerHTML=`<div class="sheet-bar">
      <button class="btn ghost" type="button" data-act="close-shopping">${ICON.back} Carnet</button>
      <span class="ttl">Liste de courses</span><span style="width:70px"></span>
    </div>
    <div class="sheet-inner">
      <div class="shop-head"><h2>Courses</h2>${total?`<span class="prog">${done} / ${total} pris</span>`:''}</div>
      ${total?`<div class="progress"><span style="width:${Math.round(done/total*100)}%"></span></div>`:''}
      <form class="shop-add" id="shop-add-form" novalidate>
        <label for="shop-new" style="position:absolute;left:-9999px">Ajouter un article</label>
        <input class="input" id="shop-new" placeholder="Ajouter : 2 baguettes, lessive…" autocomplete="off">
        <button class="btn primary" type="submit">Ajouter</button>
      </form>
      ${!total?`<div class="shop-empty"><h3>Ta liste est vide</h3><p>Ouvre une recette et touche « Ajouter à la liste de courses » : les ingrédients arrivent ici, rangés par rayon.</p></div>`:
      Object.keys(groups).map(a=>`<div class="shop-group"><h4>${esc(a)}</h4><ul class="shop-list">${groups[a].map(i=>{const d=shopLine(i); return `<li data-shop="${esc(i.id)}" class="${i.checked?'done':''}"><span class="check"></span><span class="txt">${d.q?`<span class="q">${esc(d.q)}</span> `:''}${esc(d.t)}${i.recipes&&i.recipes.length?`<span class="from">${esc(i.recipes.join(' · '))}</span>`:''}</span><button class="rm" type="button" data-shop-rm="${esc(i.id)}" aria-label="Retirer ${esc(i.name)}">✕</button></li>`;}).join('')}</ul></div>`).join('')}
      ${total?`<div class="shop-actions">
        <button class="btn" type="button" data-act="shop-share">${ICON.link} Envoyer la liste</button>
        ${done?`<button class="btn" type="button" data-act="shop-clear-done">Retirer les articles pris (${done})</button>`:''}
        <button class="btn danger" type="button" data-act="shop-clear-all">${ICON.trash} Tout effacer</button>
      </div>`:''}
    </div>`;
}
function shopText(){
  const groups={}; shop.filter(i=>!i.checked).forEach(i=>{ (groups[i.aisle]=groups[i.aisle]||[]).push(i); });
  return 'Liste de courses\n'+Object.entries(groups).map(([a,items])=>'\n'+a+'\n'+items.map(i=>{const d=shopLine(i); return '- '+(d.q?d.q+' ':'')+d.t;}).join('\n')).join('\n');
}

/* ---------- Menus de la semaine ---------- */
const DAYS=['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'];
const DAYS_S=['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'];
const MEAL_LABEL={midi:'Midi', soir:'Soir'};
const pad=n=>String(n).padStart(2,'0');
const isoDay=d=>`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
const addDays=(d,n)=>{ const x=new Date(d); x.setDate(x.getDate()+n); return x; };
function mondayOf(d){ const x=new Date(d.getFullYear(),d.getMonth(),d.getDate()); x.setDate(x.getDate()-((x.getDay()+6)%7)); return x; }
function weekLabel(start){
  const end=addDays(start,6), m1=MONTHS[start.getMonth()], m2=MONTHS[end.getMonth()];
  return start.getMonth()===end.getMonth() ? `Du ${start.getDate()} au ${end.getDate()} ${m2}` : `Du ${start.getDate()} ${m1} au ${end.getDate()} ${m2}`;
}
let week={start:mondayOf(new Date()), entries:[], loading:false};
async function loadWeek(){
  const start=isoDay(week.start), end=isoDay(addDays(week.start,6));
  week.loading=true;
  try{ week.entries=await api(`/api/menu?start=${start}&end=${end}`); }
  catch(e){ if(e.status!==401) toast(e.message); }
  week.loading=false; if(!$('#menu').hidden) renderMenu();
}
function openMenu(){ const s=$('#menu'); renderMenu(); s.hidden=false; s.scrollTop=0; lockScroll(); loadWeek(); }
function closeMenu(){ $('#menu').hidden=true; lockScroll(); }
function thumbHTML(r){ const src=photoSrc(r); return `<span class="th">${src?`<img src="${esc(src)}" alt="" loading="lazy">`:placeholder(r)}</span>`; }
function entryHTML(e){
  if(!e.recipeId) return `<div class="entry free"><span class="nm">${esc(e.text)}</span><button class="rm" type="button" data-menu-rm="${esc(e.id)}" aria-label="Retirer">✕</button></div>`;
  const r=recipes.find(x=>x.id===e.recipeId);
  if(!r) return `<div class="entry free"><span class="nm">Recette supprimée</span><button class="rm" type="button" data-menu-rm="${esc(e.id)}" aria-label="Retirer">✕</button></div>`;
  return `<div class="entry" data-menu-open="${esc(r.id)}" data-menu-serv="${esc(e.servings||'')}">${thumbHTML(r)}<span class="nm">${esc(r.title)}${e.servings?`<small>${e.servings} pers.</small>`:''}</span><button class="rm" type="button" data-menu-rm="${esc(e.id)}" aria-label="Retirer">✕</button></div>`;
}
function renderMenu(){
  const s=$('#menu'), today=isoDay(new Date()), isThis=isoDay(week.start)===isoDay(mondayOf(new Date()));
  const nRecipes=week.entries.filter(e=>e.recipeId && recipes.find(r=>r.id===e.recipeId)).length;
  s.innerHTML=`<div class="sheet-bar">
      <button class="btn ghost" type="button" data-act="close-menu">${ICON.back} Carnet</button>
      <span class="ttl">Menus de la semaine</span><span style="width:70px"></span>
    </div>
    <div class="sheet-inner">
      <div class="week-nav">
        <div><h2>Menus</h2><div class="sub">${esc(weekLabel(week.start))}${isThis?' · cette semaine':''}</div></div>
        <div class="arrows">
          <button class="iconbtn" type="button" data-act="week-prev" aria-label="Semaine précédente">${ICON.back}</button>
          ${isThis?'':`<button class="btn" type="button" data-act="week-now">Cette semaine</button>`}
          <button class="iconbtn" type="button" data-act="week-next" aria-label="Semaine suivante" style="transform:scaleX(-1)">${ICON.back}</button>
        </div>
      </div>
      <div class="week-tools">
        ${nRecipes?`<button class="btn primary" type="button" data-act="week-shop"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 8H6"/><circle cx="10" cy="20.5" r="1.3"/><circle cx="17" cy="20.5" r="1.3"/></svg> Ajouter la semaine aux courses</button>`:''}
      </div>
      <div class="week">
        ${DAYS.map((name,i)=>{ const d=addDays(week.start,i), iso=isoDay(d);
          return `<div class="day ${iso===today?'today':''}">
            <div class="day-h"><b>${DAYS_S[i]}</b><span>${d.getDate()}</span></div>
            ${['midi','soir'].map(m=>`<div class="slot"><span class="slot-l">${MEAL_LABEL[m]}</span>
              ${week.entries.filter(e=>e.day===iso && e.meal===m).map(entryHTML).join('')}
              <button class="slot-add" type="button" data-slot="${iso}|${m}" aria-label="Ajouter au ${MEAL_LABEL[m].toLowerCase()} du ${name.toLowerCase()} ${d.getDate()}">+ Ajouter</button>
            </div>`).join('')}
          </div>`; }).join('')}
      </div>
    </div>`;
}

/* Ajouter un repas depuis une case : recette ou texte libre */
let slotPick=null; // {day, meal, tab, q}
function openSlotPicker(day, meal){ slotPick={day, meal, tab: recipes.length?'recipe':'free', q:''}; renderSlotPicker(); }
function renderSlotPicker(){
  const d=new Date(slotPick.day+'T12:00:00'), label=`${DAYS[(d.getDay()+6)%7]} ${d.getDate()} · ${MEAL_LABEL[slotPick.meal]}`;
  const q=slotPick.q.trim().toLowerCase();
  const list=recipes.filter(r=>!q || (r.title||'').toLowerCase().includes(q))
    .sort((a,b)=>((b.seasons||[]).includes(NOW_SEASON)-(a.seasons||[]).includes(NOW_SEASON)) || (b.favorite-a.favorite) || a.title.localeCompare(b.title));
  openDialog(`<h3>${esc(label)}</h3>
    <div class="seg" role="tablist"><button type="button" data-slot-tab="recipe" aria-pressed="${slotPick.tab==='recipe'}">Une recette</button><button type="button" data-slot-tab="free" aria-pressed="${slotPick.tab==='free'}">Texte libre</button></div>
    ${slotPick.tab==='recipe'?`
      <label class="search" for="slot-q"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg><input id="slot-q" type="search" placeholder="Chercher une recette…" value="${esc(slotPick.q)}" autocomplete="off"></label>
      ${list.length?`<ul class="rpick">${list.map(r=>`<li data-slot-recipe="${esc(r.id)}">${thumbHTML(r)}<span class="nm">${esc(r.title)}<small>${[totalTime(r), r.servings?r.servings+' pers.':'', (r.seasons||[]).includes(NOW_SEASON)?'de saison':''].filter(Boolean).join(' · ')}</small></span></li>`).join('')}</ul>`:`<p>Aucune recette ne correspond.</p>`}
      <div class="formbar"><button class="btn" type="button" data-act="close-dlg">Fermer</button></div>`
    :`<form id="slot-free-form" novalidate style="display:grid;gap:12px">
        <label for="slot-free" style="position:absolute;left:-9999px">Ce que tu manges</label>
        <input class="input" id="slot-free" placeholder="Restes, resto, pizza…" maxlength="120" autocomplete="off">
        <div class="formbar"><button class="btn" type="button" data-act="close-dlg">Annuler</button><button class="btn primary" type="submit">Ajouter</button></div>
      </form>`}`);
  $('#dlg-box').classList.add('wide');
  setTimeout(()=>{ const el=$('#slot-q')||$('#slot-free'); if(el){ el.focus(); if(el.id==='slot-q') el.setSelectionRange(el.value.length, el.value.length); } },30);
}
async function addMenuEntry(body){
  try{ await api('/api/menu', jsonOpts('POST', body)); await loadWeek(); return true; }
  catch(e){ toast(e.message); return false; }
}

/* Ajouter au menu depuis une recette */
let planPick=null; // {recipeId, start, day, meal, servings}
function openPlanPicker(){
  const r=recipes.find(x=>x.id===det.id); if(!r) return;
  const now=new Date(), start=mondayOf(now);
  planPick={recipeId:r.id, title:r.title, start, day:isoDay(now), meal: now.getHours()<14?'midi':'soir', servings: det.servings||+r.servings||null};
  renderPlanPicker();
}
function renderPlanPicker(){
  const p=planPick;
  openDialog(`<h3>Ajouter au menu</h3><p>${esc(p.title)}</p>
    <div class="row-between"><span class="lab" style="font-size:.8rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em">Jour</span>
      <div class="mini-nav"><button type="button" data-act="plan-prev" aria-label="Semaine précédente">‹</button><span>${esc(weekLabel(p.start))}</span><button type="button" data-act="plan-next" aria-label="Semaine suivante">›</button></div></div>
    <div class="chips-days">${DAYS_S.map((n,i)=>{ const d=addDays(p.start,i), iso=isoDay(d); return `<button type="button" data-plan-day="${iso}" aria-pressed="${p.day===iso}">${n}<b>${d.getDate()}</b></button>`; }).join('')}</div>
    <div class="meal-pick"><button type="button" data-plan-meal="midi" aria-pressed="${p.meal==='midi'}">Midi</button><button type="button" data-plan-meal="soir" aria-pressed="${p.meal==='soir'}">Soir</button></div>
    ${p.servings?`<div class="row-between"><span>Personnes</span><div class="stepper"><button type="button" data-act="plan-serv-" aria-label="Moins">−</button><span class="v" style="font-weight:650">${p.servings}</span><button type="button" data-act="plan-serv+" aria-label="Plus">+</button></div></div>`:''}
    <div class="formbar"><button class="btn" type="button" data-act="close-dlg">Annuler</button><button class="btn primary" type="button" data-act="plan-confirm">Ajouter au menu</button></div>`);
}

/* Toute la semaine vers la liste de courses */
function openWeekShopPicker(){
  const items=[];
  week.entries.forEach(e=>{
    const r=e.recipeId && recipes.find(x=>x.id===e.recipeId); if(!r) return;
    const base=+r.servings||0, factor= base && e.servings ? e.servings/base : 1;
    (r.ingredients||[]).forEach(i=>items.push({name:i.name, unit:i.unit||'', recipe:r.title,
      qty: i.qty!=null && i.qty!=='' ? Math.round(i.qty*factor*100)/100 : null,
      on: !PANTRY.includes((i.name||'').trim().toLowerCase())}));
  });
  if(!items.length){ toast("Aucune recette avec des ingrédients cette semaine."); return; }
  pick={title:'Menus — '+weekLabel(week.start).toLowerCase(), servings:null, multi:true, items};
  renderShopPicker();
}

/* ---------- Connexion et comptes ---------- */
const EYE='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>';
const EYE_OFF='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3l18 18"/><path d="M10.6 5.1A10.6 10.6 0 0 1 12 5c6.4 0 10 7 10 7a17 17 0 0 1-3.2 4.1M6.6 6.6A17 17 0 0 0 2 12s3.6 7 10 7a9.7 9.7 0 0 0 5.4-1.6"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>';
/* Ajoute un bouton « œil » à chaque champ mot de passe pour vérifier ce qu'on a tapé */
function addEyes(root=document){
  root.querySelectorAll('input[type=password]:not([data-eyed])').forEach(inp=>{
    inp.dataset.eyed='1';
    const wrap=document.createElement('div'); wrap.className='pw-wrap';
    inp.parentNode.insertBefore(wrap, inp); wrap.appendChild(inp);
    const b=document.createElement('button'); b.type='button'; b.className='pw-eye';
    b.setAttribute('aria-label','Afficher le mot de passe'); b.innerHTML=EYE;
    b.addEventListener('click', ()=>{ const show=inp.type==='password'; inp.type=show?'text':'password';
      b.innerHTML=show?EYE_OFF:EYE; b.setAttribute('aria-label', show?'Masquer le mot de passe':'Afficher le mot de passe'); inp.focus(); });
    wrap.appendChild(b);
  });
}
addEyes();
let loginMode='in';
function setLoginMode(m){
  loginMode=m;
  document.querySelectorAll('[data-login-tab]').forEach(b=>b.setAttribute('aria-pressed', b.dataset.loginTab===m));
  const first=cfg.firstAccount;
  $('#code').hidden = m!=='up' || first;
  $('#pwd').autocomplete = m==='up' ? 'new-password' : 'current-password';
  $('#pwd').placeholder = m==='up' ? 'Mot de passe (6 caractères minimum)' : 'Mot de passe';
  $('#login-btn').textContent = m==='up' ? 'Créer mon compte' : 'Se connecter';
  $('#login-hint').textContent = m==='up'
    ? (first ? "Premier compte de l'appli : il en sera l'administrateur." : "Demande le code d'invitation à la personne qui utilise déjà l'appli.")
    : '';
  $('#login-err').hidden=true;
}
function showLogin(){ $('#login').hidden=false; setLoginMode(cfg.firstAccount?'up':loginMode); setTimeout(()=>$('#email').focus(),50); }
$('#login-form').addEventListener('submit', async e=>{
  e.preventDefault();
  const btn=$('#login-btn'), err=$('#login-err'), label=btn.textContent;
  const body={email:$('#email').value.trim(), password:$('#pwd').value, code:$('#code').value.trim()};
  if(!body.email || !body.password){ err.textContent='Remplis ton e-mail et ton mot de passe.'; err.hidden=false; return; }
  btn.disabled=true; btn.textContent= loginMode==='up' ? 'Création…' : 'Vérification…'; err.hidden=true;
  try{
    await api(loginMode==='up' ? '/api/signup' : '/api/login', jsonOpts('POST', body));
    location.reload();          // repart proprement avec les données du compte
  }catch(ex){ err.textContent=ex.message||'Connexion impossible.'; err.hidden=false; btn.disabled=false; btn.textContent=label; }
});

async function openAccount(){
  openDialog(`<h3>Mon compte</h3><p>Chargement…</p>`);
  let acc;
  try{ acc=await api('/api/account'); }catch(e){ closeDialog(); toast(e.message); return; }
  openDialog(`<h3>Mon compte</h3>
    <div class="acc-email">${esc(acc.email)}${acc.isAdmin?' <span class="pill" style="--c:var(--accent)">Administrateur</span>':''}</div>
    ${acc.isAdmin?`<div class="acc-box">
      <h4>Inviter quelqu'un</h4>
      <p style="margin:0;font-size:.9rem">Donne ce code à la personne. Dans l'appli, elle choisit « Créer un compte » et le saisit.</p>
      <div class="invite-code" id="acc-code">${esc(acc.inviteCode||'')}</div>
      <div class="acc-row"><button class="btn" type="button" data-act="acc-share">Envoyer le code</button><button class="btn" type="button" data-act="acc-newcode">Nouveau code</button></div>
      <h4>Comptes (${acc.users.length})</h4>
      <ul class="acc-users">${acc.users.map(u=>`<li>${esc(u)}</li>`).join('')}</ul>
    </div>`:''}
    <div class="acc-box">
      <h4>Changer de mot de passe</h4>
      <form id="acc-pw-form" novalidate>
        <label for="acc-cur" style="position:absolute;left:-9999px">Mot de passe actuel</label>
        <input class="input" id="acc-cur" type="password" autocomplete="current-password" placeholder="Mot de passe actuel">
        <label for="acc-new" style="position:absolute;left:-9999px">Nouveau mot de passe</label>
        <input class="input" id="acc-new" type="password" autocomplete="new-password" placeholder="Nouveau mot de passe">
        <button class="btn" type="submit">Enregistrer le mot de passe</button>
        <p id="acc-pw-msg" class="hint" hidden></p>
      </form>
    </div>
    <div class="formbar"><button class="btn" type="button" data-act="close-dlg">Fermer</button><button class="btn danger" type="button" data-act="acc-logout">Se déconnecter</button></div>`);
  $('#dlg-box').classList.add('wide');
  addEyes($('#dlg-box'));
}

/* ---------- Liste ---------- */
const ui={season:'all', cat:'all', q:'', fav:false};
function inFilter(r, k){ const ss=r.seasons||[]; if(k==='all') return true; if(k==='annee') return ss.length===0||ss.length===4; return ss.includes(k); }
function filtered(){
  const q=ui.q.trim().toLowerCase();
  return recipes.filter(r=>{
    if(!inFilter(r, ui.season)) return false;
    if(ui.cat!=='all' && r.category!==ui.cat) return false;
    if(ui.fav && !r.favorite) return false;
    if(q){
      const hay=[r.title,r.description,(r.tags||[]).join(' '),(r.ingredients||[]).map(i=>i.name).join(' ')].join(' ').toLowerCase();
      if(!hay.includes(q)) return false;
    }
    return true;
  }).sort((a,b)=>(b.createdAt||0)-(a.createdAt||0));
}
function render(){
  const n=recipes.length;
  const seasonTxt={ete:"de l'été", automne:"de l'automne", hiver:"de l'hiver", printemps:'du printemps'}[NOW_SEASON];
  $('#subtitle').innerHTML = `${loaded? n+' recette'+(n>1?'s':'')+' · ' : ''}<b>${MONTHS[new Date().getMonth()]}</b>, c'est la saison ${seasonTxt}`;
  const segs=[{k:'all',label:'Toutes'}, ...SEASONS, {k:'annee',label:"Toute l'année", c:'var(--year)'}];
  $('#seasons').innerHTML = segs.map(s=>`<button type="button" data-season="${s.k}" aria-pressed="${ui.season===s.k}" style="--c:${s.c||'var(--muted)'}">${s.c?'<span class="dot"></span>':''}${esc(s.label)}${s.k===NOW_SEASON?'<span class="now">maintenant</span>':''}<span class="count">${loaded?recipes.filter(r=>inFilter(r,s.k)).length:''}</span></button>`).join('');
  const present=CATEGORIES.filter(c=>recipes.some(r=>r.category===c));
  $('#cats').innerHTML = ['all',...present].map(c=>`<button type="button" class="chip" data-cat="${esc(c)}" aria-pressed="${ui.cat===c}">${c==='all'?'Tout':esc(c)}</button>`).join('');
  $('#cats').hidden = present.length<2;
  $('#btn-fav').setAttribute('aria-pressed', ui.fav);
  $('#banner').innerHTML = offline ? `<div class="notice">Hors connexion : tu vois la dernière version enregistrée sur ce téléphone. Les ajouts reviendront avec le réseau.</div>` : '';
  const g=$('#grid');
  if(!loaded){ g.innerHTML='<div class="skel"></div>'.repeat(6); return; }
  const list=filtered();
  if(!n){
    g.innerHTML=`<div class="empty" style="grid-column:1/-1"><h2>Ton carnet est vide</h2><p>Partage une vidéo TikTok vers l'appli, ou ajoute ta première recette à la main.</p><div class="actions"><button class="btn primary" type="button" data-act="import">${ICON.spark} Importer depuis une vidéo</button><button class="btn" type="button" data-act="manual">${ICON.pen} Saisir à la main</button></div></div>`;
    return;
  }
  if(!list.length){
    g.innerHTML=`<div class="empty" style="grid-column:1/-1"><h2>Rien ici pour l'instant</h2><p>Aucune recette ne correspond à ces filtres.</p><div class="actions"><button class="btn" type="button" data-act="reset">Afficher toutes les recettes</button></div></div>`;
    return;
  }
  g.innerHTML=list.map(cardHTML).join('');
}
function seasonLine(r){
  const ss=r.seasons||[];
  if(!ss.length||ss.length===4) return `<span class="dot" style="--c:var(--year)"></span><span class="lbl">Toute l'année</span>`;
  return ss.map(k=>`<span class="dot" style="--c:${SEASON_BY_K[k]?.c}"></span>`).join('') + `<span class="lbl">${ss.map(k=>SEASON_BY_K[k]?.label).join(', ')}</span>`;
}
function cardHTML(r){
  const src=photoSrc(r), plat=platformOf(r.sourceUrl);
  const meta=[totalTime(r), r.category].filter(Boolean).join(' · ');
  return `<article class="card" data-open="${esc(r.id)}" tabindex="0" aria-label="${esc(r.title)}">
    <div class="card-media">${src?`<img src="${esc(src)}" alt="" loading="lazy">`:placeholder(r)}
      <button class="fav" type="button" data-fav="${esc(r.id)}" aria-pressed="${!!r.favorite}" aria-label="Favori">${r.favorite?ICON.heart:ICON.heartO}</button>
      ${plat?`<span class="src-badge">${esc(plat)}</span>`:''}
    </div>
    <div class="card-body"><h3>${esc(r.title)}</h3>${meta?`<p class="meta">${esc(meta)}</p>`:''}<div class="seasonline">${seasonLine(r)}</div></div>
  </article>`;
}

/* ---------- Fiche recette ---------- */
let det={id:null, servings:null, ing:new Set(), steps:new Set()};
let wakeLock=null;
async function keepAwake(on){
  try{
    if(on && 'wakeLock' in navigator && !wakeLock){ wakeLock=await navigator.wakeLock.request('screen'); wakeLock.addEventListener('release',()=>{ wakeLock=null; }); }
    if(!on && wakeLock){ await wakeLock.release(); wakeLock=null; }
  }catch{}
}
function openDetail(id, push=true){
  const r=recipes.find(x=>x.id===id); if(!r) return;
  if(det.id!==id) det={id, servings:+r.servings||null, ing:new Set(), steps:new Set()};
  renderDetail();
  const s=$('#detail'); s.hidden=false; s.scrollTop=0; lockScroll();
  keepAwake(true); // l'écran reste allumé pendant qu'on cuisine
  if(push && location.hash!=='#r-'+id) history.pushState(null,'','#r-'+id);
}
function closeDetail(fromHistory=false){
  $('#detail').hidden=true; det.id=null; lockScroll(); keepAwake(false);
  if(!fromHistory && location.hash.startsWith('#r-')) history.back();
}
function renderDetail(){
  const r=recipes.find(x=>x.id===det.id); const s=$('#detail');
  if(!r){ if(!s.hidden) closeDetail(); return; }
  const src=photoSrc(r), base=+r.servings||0, cur=det.servings||base, factor= base&&cur? cur/base : 1;
  const ss=r.seasons||[];
  const pills=[...(ss.length&&ss.length<4? ss.map(k=>`<span class="pill" style="--c:${SEASON_BY_K[k].c}"><span class="dot"></span>${SEASON_BY_K[k].label}</span>`) : [`<span class="pill" style="--c:var(--year)"><span class="dot"></span>Toute l'année</span>`]), r.category?`<span class="pill">${esc(r.category)}</span>`:''].join('');
  const url=safeUrl(r.sourceUrl), plat=platformOf(r.sourceUrl);
  s.innerHTML=`<div class="sheet-bar">
      <button class="btn ghost" type="button" data-act="close-detail">${ICON.back} Carnet</button>
      <span class="ttl"></span>
      <button class="iconbtn" type="button" data-fav="${esc(r.id)}" aria-pressed="${!!r.favorite}" aria-label="Favori" style="color:${r.favorite?'#e0245e':'inherit'}">${r.favorite?ICON.heart:ICON.heartO}</button>
    </div>
    <div class="sheet-inner">
      <div class="hero">${src?`<img src="${esc(src)}" alt="${esc(r.title)}">`:placeholder(r)}</div>
      <div class="r-head">
        <div class="pills">${pills}</div>
        <h2>${esc(r.title)}</h2>
        ${r.description?`<p class="lede">${esc(r.description)}</p>`:''}
      </div>
      <div class="facts">
        <div class="fact"><div class="k">Préparation</div><div class="v">${r.prepMin? esc(r.prepMin)+' min':'—'}</div></div>
        <div class="fact"><div class="k">Cuisson</div><div class="v">${r.cookMin? esc(r.cookMin)+' min':'—'}</div></div>
        <div class="fact"><div class="k">Personnes</div>${base?`<div class="stepper v"><button type="button" data-act="serv-" aria-label="Moins">−</button><span class="v">${cur}</span><button type="button" data-act="serv+" aria-label="Plus">+</button></div>`:'<div class="v">—</div>'}</div>
      </div>
      <div class="r-cols">
        <section><h3>Ingrédients</h3>
          ${(r.ingredients||[]).length? `<ul class="ing-list">${r.ingredients.map((i,k)=>{const d=ingDisplay(i,factor); return `<li data-ing="${k}" class="${det.ing.has(k)?'done':''}"><span class="check"></span><span class="txt">${d.q?`<span class="q">${esc(d.q)}</span> `:''}${esc(d.t)}</span></li>`;}).join('')}</ul>
          <button class="btn primary shop-cta" type="button" data-act="add-shop"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 8H6"/><circle cx="10" cy="20.5" r="1.3"/><circle cx="17" cy="20.5" r="1.3"/></svg> Ajouter à la liste de courses</button>`:'<p class="hint" style="color:var(--muted)">Aucun ingrédient saisi.</p>'}
        </section>
        <section><h3>Préparation</h3>
          ${(r.steps||[]).length? `<ol class="step-list">${r.steps.map((st,k)=>`<li data-step="${k}" class="${det.steps.has(k)?'done':''}"><span class="n">${k+1}</span><span class="txt">${esc(st)}</span></li>`).join('')}</ol>`:'<p class="hint" style="color:var(--muted)">Aucune étape saisie.</p>'}
        </section>
      </div>
      ${r.tips?`<div class="tips" style="--c:${seasonColor(r)}"><b>Astuce</b>${esc(r.tips)}</div>`:''}
      ${(r.tags||[]).length?`<div class="tags">${r.tags.map(t=>`<span class="tag">#${esc(t)}</span>`).join('')}</div>`:''}
      ${url?`<p class="source">${ICON.link} Recette vue sur ${esc(plat)} : <a href="${esc(url)}" target="_blank" rel="noopener noreferrer">voir la vidéo d'origine</a></p>`:''}
      <div class="r-actions">
        <button class="btn" type="button" data-act="add-plan"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/></svg> Ajouter au menu</button>
        <button class="btn" type="button" data-act="edit">${ICON.pen} Modifier</button>
        <button class="btn danger" type="button" data-act="delete">${ICON.trash} Supprimer</button>
      </div>
    </div>`;
  s.querySelector('.ttl').textContent=r.title;
}

/* ---------- Éditeur ---------- */
let ed=null; // {id, draft, photoFile, previewUrl, removePhoto, notice, saving}
function blankDraft(){ return {title:'',description:'',category:'Plat',seasons:[NOW_SEASON],prepMin:'',cookMin:'',servings:4,ingredients:[],steps:[],tips:'',tags:[],sourceUrl:'',favorite:false,photo:null}; }
function openEditor(draft, opts={}){
  if(ed?.previewUrl) URL.revokeObjectURL(ed.previewUrl);
  ed={id:opts.id||null, draft:structuredClone(draft), photoFile:opts.photoFile||null, previewUrl:opts.photoFile?URL.createObjectURL(opts.photoFile):null, removePhoto:false, notice:opts.notice||'', saving:false};
  renderEditor(); const s=$('#editor'); s.hidden=false; s.scrollTop=0; lockScroll();
  if(opts.stepsText) $('#f-steps').value=opts.stepsText;
}
function closeEditor(){ if(ed?.previewUrl) URL.revokeObjectURL(ed.previewUrl); ed=null; $('#editor').hidden=true; lockScroll(); }
function renderEditor(){
  const d=ed.draft; const s=$('#editor');
  const existing = !ed.removePhoto && !ed.photoFile ? photoSrc(d) : '';
  const thumb = ed.previewUrl ? `<img src="${esc(ed.previewUrl)}" alt="">` : existing ? `<img src="${esc(existing)}" alt="">` : placeholder(d);
  const hasPhoto = !!(ed.previewUrl||existing);
  s.innerHTML=`<div class="sheet-bar">
      <button class="btn ghost" type="button" data-act="close-editor">Annuler</button>
      <span class="ttl">${ed.id?'Modifier la recette':'Nouvelle recette'}</span>
      <button class="btn primary" type="submit" form="recipe-form" id="f-save">Enregistrer</button>
    </div>
    <div class="sheet-inner">
    <form class="f" id="recipe-form" novalidate>
      ${ed.notice?`<div class="callout">${esc(ed.notice)}</div>`:''}
      <div class="field"><span class="lab">Photo</span>
        <div class="photo-edit"><div class="thumb">${thumb}</div>
          <div style="display:grid;gap:8px;justify-items:start">
            <span class="btn filebtn">${ICON.img} ${hasPhoto?'Changer la photo':'Ajouter une photo'}<input type="file" accept="image/*" id="f-photo" aria-label="Choisir une photo"></span>
            ${hasPhoto?`<button class="btn ghost danger" type="button" data-act="remove-photo">Retirer la photo</button>`:''}
          </div></div>
      </div>
      <div class="field"><label for="f-title">Nom de la recette <span class="req">*</span></label><input class="input" id="f-title" required value="${esc(d.title)}" placeholder="Ex. Velouté de potimarron"></div>
      <div class="field"><label for="f-desc">En une phrase</label><input class="input" id="f-desc" value="${esc(d.description)}" placeholder="Ce qui rend ce plat bon"></div>
      <div class="field"><span class="lab">Saisons</span>
        <div class="seasonpick" id="f-seasons">${SEASONS.map(s=>`<button type="button" data-pick="${s.k}" aria-pressed="${(d.seasons||[]).includes(s.k)}" style="--c:${s.c}"><span class="dot"></span>${s.label}</button>`).join('')}</div>
        <p class="hint">Aucune saison cochée = recette de toute l'année.</p>
      </div>
      <div class="row2">
        <div class="field"><label for="f-cat">Catégorie</label><select class="input" id="f-cat">${CATEGORIES.map(c=>`<option ${d.category===c?'selected':''}>${c}</option>`).join('')}</select></div>
        <div class="field"><label for="f-src">Lien d'origine</label><input class="input" id="f-src" type="url" value="${esc(d.sourceUrl)}" placeholder="https://www.tiktok.com/…"></div>
      </div>
      <div class="row3">
        <div class="field"><label for="f-prep">Prépa (min)</label><input class="input" id="f-prep" type="number" min="0" inputmode="numeric" value="${esc(d.prepMin)}"></div>
        <div class="field"><label for="f-cook">Cuisson (min)</label><input class="input" id="f-cook" type="number" min="0" inputmode="numeric" value="${esc(d.cookMin)}"></div>
        <div class="field"><label for="f-serv">Personnes</label><input class="input" id="f-serv" type="number" min="1" inputmode="numeric" value="${esc(d.servings)}"></div>
      </div>
      <div class="field"><label for="f-ing">Ingrédients</label><textarea class="input" id="f-ing" rows="8" placeholder="Une ligne par ingrédient&#10;200 g de farine&#10;3 œufs&#10;1 c. à s. d'huile d'olive">${esc((d.ingredients||[]).map(ingToLine).join('\n'))}</textarea>
        <p class="hint">Mets la quantité en début de ligne pour pouvoir ajuster le nombre de personnes.</p></div>
      <div class="field"><label for="f-steps">Étapes</label><textarea class="input" id="f-steps" rows="8" placeholder="Une ligne par étape">${esc((d.steps||[]).join('\n'))}</textarea></div>
      <div class="field"><label for="f-tips">Astuce</label><textarea class="input" id="f-tips" rows="3" style="min-height:70px">${esc(d.tips)}</textarea></div>
      <div class="field"><label for="f-tags">Mots-clés</label><input class="input" id="f-tags" value="${esc((d.tags||[]).join(', '))}" placeholder="rapide, végétarien, batch cooking"></div>
      <p id="f-err" class="hint" style="color:var(--danger)" hidden></p>
    </form></div>`;
  s.querySelector('.ttl').textContent = ed.id?'Modifier la recette':'Nouvelle recette';
}
function readEditor(){
  const d=ed.draft;
  d.title=$('#f-title').value.trim();
  d.description=$('#f-desc').value.trim();
  d.category=$('#f-cat').value;
  d.sourceUrl=$('#f-src').value.trim();
  const num=v=>{ const n=parseInt(v,10); return isNaN(n)||n<0? null : n; };
  d.prepMin=num($('#f-prep').value); d.cookMin=num($('#f-cook').value); d.servings=num($('#f-serv').value);
  d.ingredients=$('#f-ing').value.split('\n').map(parseIng).filter(Boolean);
  d.steps=$('#f-steps').value.split('\n').map(cleanStep).filter(Boolean);
  d.tips=$('#f-tips').value.trim();
  d.tags=$('#f-tags').value.split(',').map(t=>t.trim().replace(/^#/,'')).filter(Boolean);
  d.seasons=[...document.querySelectorAll('#f-seasons [aria-pressed="true"]')].map(b=>b.dataset.pick);
}
async function submitEditor(){
  if(!ed || ed.saving) return;
  readEditor();
  const err=$('#f-err');
  if(!ed.draft.title){ err.textContent='Donne un nom à la recette.'; err.hidden=false; $('#f-title').focus(); return; }
  ed.saving=true; const btn=$('#f-save'); btn.disabled=true; btn.textContent='Enregistrement…';
  try{
    const d=ed.draft;
    let photo = ed.removePhoto ? null : (d.photo||null);
    if(ed.photoFile){
      const fd=new FormData(); fd.append('file', await resizeImage(ed.photoFile), 'photo.jpg');
      photo = await api('/api/photos',{method:'POST', body:fd});
    }
    const body={...d, photo, sourceUrl:safeUrl(d.sourceUrl)?d.sourceUrl:''};
    const wasEdit=!!ed.id;
    const rec = wasEdit ? await api('/api/recipes/'+encodeURIComponent(ed.id), jsonOpts('PUT',body)) : await api('/api/recipes', jsonOpts('POST',body));
    upsertLocal(rec);
    closeEditor(); closeImporter(); render();
    det.id=null;
    if(wasEdit && !$('#detail').hidden){ openDetail(rec.id,false); } else { openDetail(rec.id); }
    toast(wasEdit?'Recette mise à jour':'Recette ajoutée au carnet');
  }catch(e){
    if(!ed) return;
    ed.saving=false; btn.disabled=false; btn.textContent='Enregistrer';
    err.textContent = e.message || "L'enregistrement a échoué."; err.hidden=false;
  }
}

/* ---------- Import ---------- */
let imp=null; // {tab, files, urls, busy, ctl, error, url, caption, started}
function openImporter(prefill={}){
  closeImporter();
  imp={tab:prefill.tab||'link', files:[], urls:[], busy:false, ctl:null, error:'', url:prefill.url||'', caption:prefill.caption||''};
  renderImporter(); const s=$('#importer'); s.hidden=false; s.scrollTop=0; lockScroll();
  if(prefill.autoStart && imp.url) runImport();
}
function closeImporter(){ if(imp){ imp.ctl?.abort(); clearInterval(imp.tick); imp.urls.forEach(u=>URL.revokeObjectURL(u)); } imp=null; $('#importer').hidden=true; lockScroll(); }
function renderImporter(){
  const s=$('#importer'), link=imp.tab==='link', dis=imp.busy?'disabled':'';
  const tabs=`<div class="seg" role="tablist" aria-label="Type d'import" style="margin-top:18px">
      <button type="button" role="tab" data-tab="link" aria-pressed="${link}" ${dis}>${ICON.link} Lien / vidéo</button>
      <button type="button" role="tab" data-tab="shots" aria-pressed="${!link}" ${dis}>${ICON.img.replace('<svg','<svg width="16" height="16"')} Captures / texte</button>
    </div>`;
  const linkPane=`
      <div class="field"><label for="i-url">Lien de la vidéo ou de la page</label>
        <input class="input" id="i-url" type="url" inputmode="url" placeholder="https://vm.tiktok.com/…" value="${esc(imp.url)}" ${dis}>
        <p class="hint">TikTok, YouTube, Instagram ou un site de cuisine. ${cfg.provider==='gemini'?"Gemini regarde la vidéo, écoute ce qui est dit et rédige la fiche.":cfg.ai?"L'appli lit la description et la miniature, puis Claude rédige la fiche.":"L'appli lit la description et la miniature de la vidéo et range les ingrédients et les étapes."}</p></div>`;
  const shotsPane=`
      <div class="field"><span class="lab">Captures d'écran (${imp.files.length}/${MAX_SHOTS})</span>
        <div class="drop" id="i-drop">
          ${imp.files.length?`<div class="shots">${imp.urls.map((u,k)=>`<div class="shot"><img src="${esc(u)}" alt="Capture ${k+1}"><button type="button" data-rmshot="${k}" aria-label="Retirer la capture ${k+1}" ${dis}>✕</button></div>`).join('')}</div>`:''}
          ${imp.files.length<MAX_SHOTS && !imp.busy?`<span class="btn ${imp.files.length?'':'primary'} filebtn">${ICON.img} ${imp.files.length?'Ajouter une capture':'Choisir des captures'}<input type="file" accept="image/*" multiple id="i-shots" aria-label="Choisir des captures"></span>`:''}
          <p class="hint">Dans TikTok, ouvre la description de la vidéo et fais une capture de la liste des ingrédients et des étapes (plusieurs captures si c'est long). L'appli lit le texte ; la dernière capture sert de photo.</p>
        </div></div>
      <div class="field"><label for="i-cap">Ou colle le texte de la recette</label><textarea class="input" id="i-cap" rows="5" placeholder="Copie la description de la vidéo et colle-la ici…" ${dis}>${esc(imp.caption)}</textarea></div>
      <div class="field"><label for="i-src">Lien de la vidéo (facultatif, pour la retrouver)</label><input class="input" id="i-src" type="url" inputmode="url" placeholder="https://vm.tiktok.com/…" value="${esc(imp.url)}" ${dis}></div>`;
  const who = cfg.provider==='gemini' ? 'Gemini' : 'Claude';
  const busyLabel = link ? (cfg.provider==='gemini' ? 'Gemini regarde la vidéo…' : cfg.ai ? 'Lecture de la vidéo…' : 'Lecture de la vidéo…')
                         : (cfg.ai ? `${who} lit ${imp.files.length?'les captures':'le texte'}…` : (imp.files.length? 'Lecture des captures…' : 'Analyse du texte…'));
  s.innerHTML=`<div class="sheet-bar">
      <button class="btn ghost" type="button" data-act="close-importer">Annuler</button>
      <span class="ttl">Importer une recette</span><span style="width:70px"></span>
    </div>
    <div class="sheet-inner">
      ${tabs}
      <form class="f" id="import-form" novalidate>
        ${link?linkPane:shotsPane}
        ${imp.error?`<div class="callout warn">${esc(imp.error)}</div>`:''}
        ${imp.busy?`<div class="working"><span class="spinner"></span><span style="flex:1">${busyLabel} <span id="i-elapsed" style="color:var(--muted);font-variant-numeric:tabular-nums"></span></span><button class="btn" type="button" data-act="stop-import">Arrêter</button></div>`:
        `<div class="formbar">
          <button class="btn" type="button" data-act="import-manual">Saisir moi-même</button>
          <button class="btn primary" type="submit">${ICON.spark} Créer la fiche</button>
        </div>`}
      </form>
    </div>`;
}
function syncImportFields(){ if(!imp) return; const u=$('#i-url')||$('#i-src'), c=$('#i-cap'); if(u) imp.url=u.value; if(c) imp.caption=c.value; }
function addShots(list){
  if(!imp||imp.busy) return; syncImportFields();
  let skipped=0;
  for(const f of list){
    if(!f.type.startsWith('image/')){ skipped++; continue; }
    if(imp.files.length>=MAX_SHOTS){ skipped++; continue; }
    imp.files.push(f); imp.urls.push(URL.createObjectURL(f));
  }
  imp.tab='shots';
  imp.error = skipped? `${skipped} fichier${skipped>1?'s':''} ignoré${skipped>1?'s':''} (pas une image, ou limite de ${MAX_SHOTS} captures).` : '';
  renderImporter();
}
async function runImport(){
  if(!imp||imp.busy) return;
  syncImportFields();
  const link=imp.tab==='link';
  const url=imp.url.trim(), caption=imp.caption.trim();
  if(url && !safeUrl(url)){ imp.error="Ce lien ne semble pas valide : il doit commencer par https://"; renderImporter(); return; }
  if(link && !url){ imp.error="Colle le lien de la vidéo (dans TikTok : Partager → Copier le lien)."; renderImporter(); return; }
  if(!link && !caption && !imp.files.length){ imp.error="Ajoute au moins une capture d'écran ou colle le texte de la recette."; renderImporter(); return; }
  const ctl=new AbortController();
  imp.busy=true; imp.error=''; imp.timedOut=false; imp.ctl=ctl; imp.started=Date.now(); renderImporter();
  clearInterval(imp.tick);
  imp.tick=setInterval(()=>{ const el=$('#i-elapsed'); if(el && imp) el.textContent=Math.round((Date.now()-imp.started)/1000)+' s'; },1000);
  const limit = cfg.ai ? 150000 : (link ? 45000 : 90000);
  const timer=setTimeout(()=>{ if(imp && imp.ctl===ctl){ imp.timedOut=true; ctl.abort(); } }, limit);
  try{
    const fd=new FormData();
    if(link){ fd.append('url',url); }
    else{
      fd.append('caption',caption); fd.append('source',url);
      for(const f of imp.files){ fd.append('images', await resizeImage(f,2400,.9), 'capture.jpg'); }
    }
    if(ctl.signal.aborted) return;
    const res=await api('/api/import',{method:'POST', body:fd, signal:ctl.signal});
    if(!imp || imp.ctl!==ctl) return;
    clearInterval(imp.tick);
    const notice = res.ai===false ? (res.notes || "Fiche pré-remplie : relis-la avant d'enregistrer.") : `Fiche rédigée par ${res.provider==='gemini'?'Gemini':'Claude'}${res.video?" à partir de la vidéo":''} : relis-la avant d'enregistrer.` + (res.notes? ' '+res.notes : '');
    imp.busy=false;
    const draft={...blankDraft(), ...res.draft};
    closeImporter();                 // l'éditeur ne doit pas s'ouvrir derrière l'écran d'import
    openEditor(draft, {notice});
  }catch(e){
    if(!imp || imp.ctl!==ctl) return;
    clearInterval(imp.tick);
    imp.busy=false;
    if(e.name==='AbortError'){
      if(imp.timedOut){
        if(link){ imp.tab='shots'; imp.error="La vidéo ne répond pas. Fais des captures de sa description et ajoute-les ici, ou colle le texte."; }
        else imp.error="La lecture prend trop de temps. Essaie avec moins de captures, ou colle le texte de la recette.";
      } else imp.error='';
    } else if(link && (e.status===422 || e.status===0)){
      imp.tab='shots';
      imp.error = e.status===0 ? e.message : "Je n'ai pas pu lire cette vidéo. Fais des captures de sa description et ajoute-les ici, ou colle le texte.";
    } else {
      imp.error = e.message || "L'import a échoué. Réessaie.";
    }
    renderImporter();
  }finally{ clearTimeout(timer); }
}

/* ---------- Partage depuis une autre appli (menu « Partager ») ---------- */
function handleShare(){
  if(location.pathname!=='/share') return;
  const p=new URLSearchParams(location.search);
  const all=[p.get('url'),p.get('text'),p.get('title')].filter(Boolean).join(' ');
  const m=all.match(/https?:\/\/[^\s"'<>]+/);
  history.replaceState(null,'','/');
  if(!m){ if(all.trim()) openImporter({tab:'shots', caption:all.trim()}); return; }
  openImporter({url:m[0], autoStart:true});
}

/* ---------- Dialogues ---------- */
function openDialog(html){ $('#dlg-box').innerHTML=html; $('#dlg').hidden=false; $('#dlg-box').querySelector('button')?.focus(); }
function closeDialog(){ $('#dlg').hidden=true; $('#dlg-box').innerHTML=''; $('#dlg-box').classList.remove('wide'); }
function openAddMenu(){
  openDialog(`<h3>Ajouter une recette</h3>
    <button class="menu-opt" type="button" data-act="import">${ICON.spark}<div><b>Depuis une vidéo ou un lien</b><span>TikTok, Instagram, YouTube, site de cuisine : la fiche se pré-remplit toute seule.</span></div></button>
    <button class="menu-opt" type="button" data-act="manual">${ICON.pen}<div><b>À la main</b><span>Tu saisis toi-même les ingrédients et les étapes.</span></div></button>
    <div class="formbar"><button class="btn" type="button" data-act="close-dlg">Fermer</button></div>`);
}

/* ---------- Événements ---------- */
document.addEventListener('click', async ev=>{
  const lt=ev.target.closest('[data-login-tab]'); if(lt){ setLoginMode(lt.dataset.loginTab); return; }
  const t=ev.target.closest('[data-act],[data-season],[data-cat],[data-fav],[data-open],[data-ing],[data-step],[data-pick],[data-rmshot],[data-tab],[data-pick-ing],[data-shop],[data-shop-rm],[data-slot],[data-slot-tab],[data-slot-recipe],[data-menu-rm],[data-menu-open],[data-plan-day],[data-plan-meal]');
  if(!t){ if(ev.target.id==='dlg') closeDialog(); return; }
  if(t.dataset.fav!==undefined){
    ev.stopPropagation();
    const r=recipes.find(x=>x.id===t.dataset.fav); if(!r) return;
    const val=!r.favorite; r.favorite=val; render(); if(det.id===r.id) renderDetail();
    try{ upsertLocal(await api('/api/recipes/'+encodeURIComponent(r.id), jsonOpts('PATCH',{favorite:val}))); }
    catch(e){ r.favorite=!val; render(); if(det.id===r.id) renderDetail(); toast(e.message); }
    return;
  }
  if(t.dataset.menuRm){ ev.stopPropagation(); const id=t.dataset.menuRm; week.entries=week.entries.filter(e=>e.id!==id); renderMenu();
    try{ await api('/api/menu/'+encodeURIComponent(id),{method:'DELETE'}); }catch(e){ toast(e.message); loadWeek(); } return; }
  if(t.dataset.menuOpen){ const id=t.dataset.menuOpen, sv=+t.dataset.menuServ||null; closeMenu(); openDetail(id); if(sv){ det.servings=sv; renderDetail(); } return; }
  if(t.dataset.slot){ const [d,m]=t.dataset.slot.split('|'); openSlotPicker(d,m); return; }
  if(t.dataset.slotTab){ slotPick.tab=t.dataset.slotTab; renderSlotPicker(); return; }
  if(t.dataset.slotRecipe){ const r=recipes.find(x=>x.id===t.dataset.slotRecipe);
    if(await addMenuEntry({day:slotPick.day, meal:slotPick.meal, recipeId:r.id, servings:+r.servings||null})){ closeDialog(); toast(`${r.title} ajouté au menu`); } return; }
  if(t.dataset.planDay){ planPick.day=t.dataset.planDay; renderPlanPicker(); return; }
  if(t.dataset.planMeal){ planPick.meal=t.dataset.planMeal; renderPlanPicker(); return; }
  if(t.dataset.pickIng!==undefined){ const it=pick.items[+t.dataset.pickIng]; it.on=!it.on; renderShopPicker(); return; }
  if(t.dataset.shopRm){ ev.stopPropagation(); const id=t.dataset.shopRm; setShop(shop.filter(i=>i.id!==id));
    try{ setShop(await api('/api/shopping/'+encodeURIComponent(id),{method:'DELETE'})); }catch(e){ toast(e.message); loadShop(); } return; }
  if(t.dataset.shop){ const it=shop.find(i=>i.id===t.dataset.shop); if(!it) return; it.checked=!it.checked; setShop([...shop]);
    try{ setShop(await api('/api/shopping/'+encodeURIComponent(it.id), jsonOpts('PATCH',{checked:it.checked}))); }catch(e){ toast(e.message); loadShop(); } return; }
  if(t.dataset.tab){ if(imp && !imp.busy){ syncImportFields(); imp.tab=t.dataset.tab; imp.error=''; renderImporter(); } return; }
  if(t.dataset.season){ ui.season=t.dataset.season; render(); return; }
  if(t.dataset.cat){ ui.cat=t.dataset.cat; render(); return; }
  if(t.dataset.open){ openDetail(t.dataset.open); return; }
  if(t.dataset.ing!==undefined){ const k=+t.dataset.ing; det.ing.has(k)?det.ing.delete(k):det.ing.add(k); t.classList.toggle('done'); return; }
  if(t.dataset.step!==undefined){ const k=+t.dataset.step; det.steps.has(k)?det.steps.delete(k):det.steps.add(k); t.classList.toggle('done'); return; }
  if(t.dataset.pick){ t.setAttribute('aria-pressed', t.getAttribute('aria-pressed')!=='true'); return; }
  if(t.dataset.rmshot!==undefined){ syncImportFields(); const k=+t.dataset.rmshot; URL.revokeObjectURL(imp.urls[k]); imp.files.splice(k,1); imp.urls.splice(k,1); imp.error=''; renderImporter(); return; }
  const a=t.dataset.act;
  if(a==='import'){ closeDialog(); openImporter(); }
  else if(a==='manual'){ closeDialog(); openEditor(blankDraft()); setTimeout(()=>$('#f-title')?.focus(),60); }
  else if(a==='close-dlg'){ closeDialog(); }
  else if(a==='acc-logout'){ try{ await api('/api/logout',{method:'POST'}); }catch{} try{ localStorage.removeItem(CACHE_KEY); localStorage.removeItem(SHOP_KEY); }catch{} location.reload(); }
  else if(a==='acc-newcode'){ try{ const r=await api('/api/account/invite',{method:'POST'}); $('#acc-code').textContent=r.inviteCode; toast("Nouveau code créé : l'ancien ne marche plus"); }catch(e){ toast(e.message); } }
  else if(a==='acc-share'){ const code=$('#acc-code').textContent, text=`Je t'invite sur mon carnet de recettes : ${location.origin}\nTouche « Créer un compte » et saisis le code d'invitation : ${code}`;
    if(navigator.share){ try{ await navigator.share({title:'Carnet de recettes', text}); return; }catch(e){ if(e.name==='AbortError') return; } }
    try{ await navigator.clipboard.writeText(text); toast('Invitation copiée : colle-la dans un SMS'); }catch{ toast('Copie impossible : note le code affiché.'); } }
  else if(a==='add-shop'){ openShopPicker(); }
  else if(a==='add-plan'){ openPlanPicker(); }
  else if(a==='plan-prev'||a==='plan-next'){ planPick.start=addDays(planPick.start, a==='plan-next'?7:-7); const wd=(new Date(planPick.day+'T12:00:00').getDay()+6)%7; planPick.day=isoDay(addDays(planPick.start, wd)); renderPlanPicker(); }
  else if(a==='plan-serv-'||a==='plan-serv+'){ planPick.servings=Math.max(1, planPick.servings+(a==='plan-serv+'?1:-1)); renderPlanPicker(); }
  else if(a==='plan-confirm'){ const p=planPick, wk=mondayOf(new Date(p.day+'T12:00:00'));
    const ok=await (async()=>{ try{ await api('/api/menu', jsonOpts('POST',{day:p.day, meal:p.meal, recipeId:p.recipeId, servings:p.servings})); return true; }catch(e){ toast(e.message); return false; } })();
    if(ok){ closeDialog(); const d=new Date(p.day+'T12:00:00'); toast(`Ajouté au menu : ${DAYS[(d.getDay()+6)%7].toLowerCase()} ${d.getDate()}, ${MEAL_LABEL[p.meal].toLowerCase()}`); if(isoDay(wk)===isoDay(week.start)) loadWeek(); } }
  else if(a==='close-menu'){ closeMenu(); }
  else if(a==='week-prev'||a==='week-next'){ week.start=addDays(week.start, a==='week-next'?7:-7); week.entries=[]; renderMenu(); loadWeek(); }
  else if(a==='week-now'){ week.start=mondayOf(new Date()); week.entries=[]; renderMenu(); loadWeek(); }
  else if(a==='week-shop'){ openWeekShopPicker(); }
  else if(a==='pick-all'||a==='pick-none'){ pick.items.forEach(i=>i.on=a==='pick-all'); renderShopPicker(); }
  else if(a==='pick-confirm'){ confirmShopPicker(); }
  else if(a==='close-shopping'){ closeShopping(); }
  else if(a==='shop-clear-done'){ try{ setShop(await api('/api/shopping/clear', jsonOpts('POST',{mode:'checked'}))); }catch(e){ toast(e.message); } }
  else if(a==='shop-clear-all'){ openDialog(`<h3>Effacer toute la liste ?</h3><p>Tous les articles seront retirés, même ceux pas encore pris.</p><div class="formbar"><button class="btn" type="button" data-act="close-dlg">Annuler</button><button class="btn primary" style="background:var(--danger);border-color:var(--danger);color:#fff" type="button" data-act="shop-clear-all-ok">Tout effacer</button></div>`); }
  else if(a==='shop-clear-all-ok'){ closeDialog(); try{ setShop(await api('/api/shopping/clear', jsonOpts('POST',{mode:'all'}))); toast('Liste effacée'); }catch(e){ toast(e.message); } }
  else if(a==='shop-share'){ const text=shopText();
    if(navigator.share){ try{ await navigator.share({title:'Liste de courses', text}); return; }catch(e){ if(e.name==='AbortError') return; } }
    try{ await navigator.clipboard.writeText(text); toast('Liste copiée : colle-la dans un SMS ou une note'); }catch{ toast("Impossible de copier la liste sur cet appareil."); } }
  else if(a==='reset'){ ui.season='all'; ui.cat='all'; ui.fav=false; ui.q=''; $('#q').value=''; render(); }
  else if(a==='close-detail'){ closeDetail(); }
  else if(a==='serv-'||a==='serv+'){ const r=recipes.find(x=>x.id===det.id); const base=+r.servings||1; det.servings=Math.max(1,(det.servings||base)+(a==='serv+'?1:-1)); renderDetail(); }
  else if(a==='edit'){ const r=recipes.find(x=>x.id===det.id); if(r) openEditor(r,{id:r.id}); }
  else if(a==='delete'){ const r=recipes.find(x=>x.id===det.id); if(!r) return;
    openDialog(`<h3>Supprimer « ${esc(r.title)} » ?</h3><p>La recette et sa photo seront retirées du carnet. Cette action est définitive.</p><div class="formbar"><button class="btn" type="button" data-act="close-dlg">Annuler</button><button class="btn primary" style="background:var(--danger);border-color:var(--danger);color:#fff" type="button" data-act="confirm-delete">Supprimer</button></div>`); }
  else if(a==='confirm-delete'){ const id=det.id; closeDialog();
    try{ await api('/api/recipes/'+encodeURIComponent(id),{method:'DELETE'}); recipes=recipes.filter(r=>r.id!==id); try{ localStorage.setItem(CACHE_KEY, JSON.stringify(recipes)); }catch{} closeDetail(); render(); toast('Recette supprimée'); }
    catch(e){ toast(e.message); } }
  else if(a==='close-editor'){ closeEditor(); }
  else if(a==='remove-photo'){ readEditor(); if(ed.previewUrl) URL.revokeObjectURL(ed.previewUrl); ed.photoFile=null; ed.previewUrl=null; ed.removePhoto=true; renderEditor(); }
  else if(a==='close-importer'){ closeImporter(); }
  else if(a==='stop-import'){ if(imp){ const c=imp.ctl; imp.ctl=null; clearInterval(imp.tick); imp.busy=false; imp.error=''; c?.abort(); renderImporter(); } }
  else if(a==='import-manual'){ syncImportFields(); const cap=imp.caption.trim(); const cover=imp.files.at(-1)||null; const d={...blankDraft(), sourceUrl:imp.url.trim()};
    closeImporter(); openEditor(d,{photoFile:cover, notice: cap? 'Ton texte est dans les étapes : répartis-le entre ingrédients et étapes.':'', stepsText:cap}); }
});
$('#btn-add').addEventListener('click', openAddMenu);
$('#btn-shop').addEventListener('click', openShopping);
$('#btn-menu').addEventListener('click', openMenu);
$('#btn-account').addEventListener('click', openAccount);
$('#btn-fav').addEventListener('click', ()=>{ ui.fav=!ui.fav; render(); });
$('#q').addEventListener('input', e=>{ ui.q=e.target.value; render(); });
document.addEventListener('input', e=>{ if(e.target.id==='slot-q'){ slotPick.q=e.target.value; renderSlotPicker(); } });
document.addEventListener('keydown', e=>{
  if(e.key==='Escape'){ if(!$('#dlg').hidden) closeDialog(); else if(!$('#editor').hidden) closeEditor(); else if(!$('#importer').hidden) closeImporter(); else if(!$('#shopping').hidden) closeShopping(); else if(!$('#menu').hidden) closeMenu(); else if(!$('#detail').hidden) closeDetail(); }
  if(e.key==='Enter' && e.target.matches?.('.card')) openDetail(e.target.dataset.open);
});
document.addEventListener('submit', e=>{
  if(e.target.id==='recipe-form'){ e.preventDefault(); submitEditor(); }
  if(e.target.id==='import-form'){ e.preventDefault(); runImport(); }
  if(e.target.id==='slot-free-form'){ e.preventDefault(); const v=$('#slot-free').value.trim(); if(!v) return;
    addMenuEntry({day:slotPick.day, meal:slotPick.meal, text:v}).then(ok=>{ if(ok) closeDialog(); }); }
  if(e.target.id==='acc-pw-form'){ e.preventDefault(); const msg=$('#acc-pw-msg');
    api('/api/account/password', jsonOpts('POST',{current:$('#acc-cur').value, new:$('#acc-new').value}))
      .then(()=>{ msg.style.color='var(--accent)'; msg.textContent='Mot de passe modifié.'; msg.hidden=false; $('#acc-cur').value=''; $('#acc-new').value=''; })
      .catch(err=>{ msg.style.color='var(--danger)'; msg.textContent=err.message; msg.hidden=false; }); }
  if(e.target.id==='shop-add-form'){ e.preventDefault(); const v=$('#shop-new').value.trim(); if(!v) return;
    api('/api/shopping/item', jsonOpts('POST',{text:v})).then(l=>{ setShop(l); setTimeout(()=>$('#shop-new')?.focus(),30); }).catch(err=>toast(err.message)); }
});
document.addEventListener('change', e=>{
  if(e.target.id==='f-photo' && e.target.files?.[0]){ readEditor(); if(ed.previewUrl) URL.revokeObjectURL(ed.previewUrl); ed.photoFile=e.target.files[0]; ed.previewUrl=URL.createObjectURL(ed.photoFile); ed.removePhoto=false; renderEditor(); }
  if(e.target.id==='i-shots' && e.target.files?.length){ addShots([...e.target.files]); }
});
document.addEventListener('dragover', e=>{ const d=e.target.closest?.('#i-drop'); if(d){ e.preventDefault(); d.classList.add('over'); } });
document.addEventListener('dragleave', e=>{ const d=e.target.closest?.('#i-drop'); if(d) d.classList.remove('over'); });
document.addEventListener('drop', e=>{ const d=e.target.closest?.('#i-drop'); if(d){ e.preventDefault(); d.classList.remove('over'); addShots([...e.dataTransfer.files]); } });
document.addEventListener('paste', e=>{
  if($('#importer').hidden) return;
  const files=[...(e.clipboardData?.files||[])].filter(f=>f.type.startsWith('image/'));
  if(files.length){ e.preventDefault(); addShots(files); }
});
window.addEventListener('popstate', ()=>{
  const h=location.hash;
  if(h.startsWith('#r-')){ const id=h.slice(3); if(recipes.find(r=>r.id===id)) openDetail(id,false); }
  else if(!$('#detail').hidden) closeDetail(true);
});
document.addEventListener('visibilitychange', ()=>{
  if(document.visibilityState==='visible'){ if(det.id) keepAwake(true); if(loaded && $('#editor').hidden) loadRecipes(); if(loaded) loadShop(); }
});
window.addEventListener('online', ()=>{ if(offline) loadRecipes(); });

/* ---------- Installation ---------- */
let installEvt=null;
window.addEventListener('beforeinstallprompt', e=>{ e.preventDefault(); installEvt=e; $('#btn-install').hidden=false; });
$('#btn-install').addEventListener('click', async ()=>{ if(!installEvt) return; installEvt.prompt(); await installEvt.userChoice; installEvt=null; $('#btn-install').hidden=true; });
if('serviceWorker' in navigator){ window.addEventListener('load', ()=>navigator.serviceWorker.register('/sw.js').catch(()=>{})); }

/* ---------- Démarrage ---------- */
render();
(async()=>{
  try{ cfg=await api('/api/config'); }catch{ cfg={ai:false, auth:false, loggedIn:true}; }
  try{ localStorage.removeItem('carnet-cache-v1'); localStorage.removeItem('carnet-courses-v1'); }catch{}   // anciens caches communs
  if(cfg.auth && !cfg.loggedIn){ showLogin(); return; }
  if(cfg.email){ CACHE_KEY+=':'+cfg.email; SHOP_KEY+=':'+cfg.email;
    $('#acc-initial').textContent=cfg.email.charAt(0); $('#btn-account').hidden=false; $('#btn-account').title=cfg.email; }
  await loadRecipes(); loadShop();
  handleShare();
  const h=location.hash; if(h.startsWith('#r-')){ const id=h.slice(3); if(recipes.find(r=>r.id===id)){ history.replaceState(null,'',location.pathname); openDetail(id); } }
})();
