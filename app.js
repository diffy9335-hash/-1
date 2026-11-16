/* VELTON Mini App: all career state is verified and persisted on the server. */
(() => {
  'use strict';
  const app = document.getElementById('app');
  const telegram = window.Telegram?.WebApp;
  if (telegram) {
    telegram.ready();
    telegram.expand();
    try { telegram.setHeaderColor('#f1f8ff'); telegram.setBackgroundColor('#f1f8ff'); } catch (_) {}
  }
  const ui = {data: null, page:'home', career:null, createSlot:null, createRole:null,
              result:null, busy:false, demo:false, table:null, worldBrowser:null, availableLeagues:[], clubChoices:[], selectedLeague:null, market:null, squad:null, marketPlayer:null, calendar:null, archive:null};
  const ic = (name) => {
    const p = {
      home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M9 21v-8h6v8"/>',
      layers:'<rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/>',
      user:'<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3-7 8-7s8 3 8 7"/>',
      right:'<path d="m9 18 6-6-6-6"/>', left:'<path d="m15 18-6-6 6-6"/>',
      close:'<path d="M18 6 6 18M6 6l12 12"/>',
      plus:'<path d="M12 5v14M5 12h14"/>',
      check:'<path d="m5 12 4 4L19 6"/>'
    }[name] || '';
    return `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;
  };
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const bySlot = n => ui.data.careers.find(c => c.slot === n);
  const cap = value => value > 9999 ? (value / 1000).toFixed(1)+'k' : String(value);
  const euros = amount => Number(amount)>=1e9?'€'+(Number(amount)/1e9).toFixed(2)+' млрд': '€'+(Number(amount)/1e6).toFixed(1)+' млн';
  const initials = name => name.trim().split(/\s+/).slice(0,2).map(t => t[0] || '').join('').toUpperCase();
  const positionRU = pos => ({GK:'Вратарь',G:'Вратарь',DF:'Защитник',DEF:'Защитник',MF:'Полузащитник',MID:'Полузащитник',FW:'Нападающий',ATT:'Нападающий'}[pos] || pos || 'Игрок');
  let toastTimer;
  function toast(message) {
    document.querySelector('.toast')?.remove();
    const node=document.createElement('div');node.className='toast';node.textContent=message;
    document.body.append(node);
    clearTimeout(toastTimer);toastTimer=setTimeout(() => node.remove(), 3900);
  }
  async function request(path, method='GET', body) {
    const options={method, headers:{'X-Telegram-Init-Data': telegram?.initData || ''}};
    if (body !== undefined) {
      options.headers['Content-Type']='application/json';
      options.body=JSON.stringify(body);
    }
    let resp;
    try {resp=await fetch(path,options)} catch (_) {throw new Error('Нет связи с сервером. Проверь интернет.')}
    const json = await resp.json().catch(()=>({}));
    if (!resp.ok) throw new Error(typeof json.detail==='string' ? json.detail : 'Ошибка запроса');
    return json;
  }
  async function load() {
    try {
      const cfg = await request('/api/config');
      ui.demo=cfg.demo;
      ui.data=await request('/api/state');
      render();
    } catch(e) {
      app.innerHTML=`<div class="error-state"><div class="brand">VELTON</div><h2>Не удалось войти</h2><p>${esc(e.message)}</p><button id="retry">Попробовать снова</button></div>`;
      document.getElementById('retry').onclick=load;
    }
  }
  const header = () => `<div class="header"><span class="brand">VELTON</span><div class="header-right"><span class="level-chip">LVL ${ui.data.profile.level}</span><div class="avatar" aria-label="Профиль">${esc(initials(ui.data.profile.name))}</div></div></div>`;
  const nav = () => `<nav class="bottom-nav" aria-label="Главные разделы">${[
    ['home','Обзор','home'],['careers','Карьеры','layers'],['profile','Профиль','user']].map(([page,label,icon])=>
    `<button class="nav-btn ${ui.page===page?'active':''}" data-action="page" data-page="${page}" aria-current="${ui.page===page?'page':'false'}">${ic(icon)}<span>${label}</span></button>`).join('')}</nav>`;
  function careerList(limit=5) {
    const slots = Array.from({length:limit},(_,i)=>i+1);
    return `<div class="slot-list">${slots.map(n=>{
      const c=bySlot(n);
      return `<button class="slot-card" data-action="${c?'open':'create'}" data-slot="${n}">
        <span class="slot-index">${String(n).padStart(2,'0')}</span>
        <span class="slot-identity ${c?'':'empty'}">${c?esc(ui.data.roles[c.role].short):ic('plus')}</span>
        <span class="slot-content"><strong>${c?esc(c.name):'Свободный слот'}</strong>
        <span>${c?`${esc(ui.data.roles[c.role].name)} · ${esc(c.place)} · Сезон ${c.season}`:'Выбрать футбольную карьеру'}</span></span>
        <span class="chev">${ic('right')}</span></button>`
    }).join('')}</div>`;
  }
  function homePage() {
    const p=ui.data.profile, occupied=ui.data.careers.length;
    return `<div class="main">${header()}
      ${ui.demo?'<div class="notice">Демонстрационный режим. Прогресс сохраняется локально на этом сервере.</div>':''}
      <p class="greet">Добро пожаловать, ${esc(p.name)}</p><h1 class="headline">Твоя футбольная история</h1><p class="subhead">Пять карьер. Сотни будущих решений. Один профиль.</p>
      <section class="hero" aria-label="Начало карьеры"><div class="hero-tag">CAREER SIMULATOR</div><div class="hero-title">Твой футбол.<br>Твои правила.</div>
      <div class="hero-copy">Создай собственную историю футбола с любой стороны поля.</div><div class="hero-field" aria-hidden="true"><div class="penalty"></div><div class="dot"></div></div></section>
      <div class="world-mini">Футбольный мир · ${ui.data.world_catalog.countries} стран · ${ui.data.world_catalog.leagues} лиг<br>
      <strong>Офлайн-база: ${ui.data.world_catalog.imported_clubs} клубов · ${ui.data.world_catalog.rosters?.available_players ?? ui.data.world_catalog.imported_players} известных футболистов</strong>
      <span class="world-mini-sub">${ui.data.world_catalog.imported_leagues} из 80 лиг содержат клубы · ${ui.data.world_catalog.rosters?.clubs_20_plus ?? 0} клубов с 20+ игроками</span>
      <button class="quiet-action" data-action="world-browser">Открыть каталог</button></div>
      <section class="stat-grid" aria-label="Статистика профиля">
        <div class="mini-stat"><strong>${occupied}/5</strong><small>Карьер</small></div>
        <div class="mini-stat"><strong>${cap(p.decisions)}</strong><small>Решений</small></div>
        <div class="mini-stat"><strong>${p.level}</strong><small>Уровень</small></div>
      </section>
      <div class="section-bar"><div><h2 class="section-title">Мои карьеры</h2><div class="section-sub">5 независимых сохранений</div></div><button class="quiet-action" data-action="page" data-page="careers">Все слоты</button></div>
      ${careerList()}<p class="note">Каждая карьера развивается отдельно. Достижения и опыт сохраняются в общем профиле.</p>
    </div>`;
  }
  function careersPage() {
    return `<div class="main">${header()}<div class="eyebrow">Карьера</div><h1 class="page-title">Выбери свой путь</h1>
      <p class="page-intro">Стань игроком, тренером, судьёй, агентом или возглавь собственный клуб. Все пять слотов доступны сразу.</p>
      ${careerList()}<p class="note">Удаление карьеры освобождает слот. Награды и общий опыт останутся в профиле.</p></div>`;
  }
  function tableHTML(c) {
    const w=ui.table?.slot===c.slot ? ui.table.data : c.world;
    if(!w)return '';
    if(!w.leagues.length)return `<div class="card empty-world">Реальные составы и клубы пока не импортированы. Администратор может добавить их из офлайн JSON-пакета. Без этого турнирные таблицы не будут выдуманы.</div>`;
    const options=w.leagues.map(l=>`<option value="${esc(l.id)}" ${l.id===w.selected?'selected':''}>${esc(l.name)} (${l.clubs})</option>`).join('');
    const renderRows=rows=>`<div class="table-viewport"><table class="league-table"><thead><tr><th>№</th><th>Клуб</th><th>И</th><th>РМ</th><th>О</th></tr></thead><tbody>
      ${rows.map(r=>`<tr><td>${r.rank}</td><td><strong>${esc(r.name)}</strong><small>${euros(r.budget_eur)} · трансферы ${euros(r.transfer_eur)}</small></td><td>${r.played}</td><td>${r.goal_difference>0?'+':''}${r.goal_difference}</td><td><b>${r.points}</b></td></tr>`).join('')}
      </tbody></table></div>`;
    const grouped=Array.isArray(w.groups)&&w.groups.length>1;
    const tables=grouped?w.groups.map(g=>`<h3 class="section-title">Группа ${g.number}</h3>${renderRows(g.rows)}`).join(''):renderRows(w.rows);
    return `<div class="section-bar"><div><h2 class="section-title">Турнирная таблица</h2><div class="section-sub">Сезон ${c.season} · ${c.phase==='review'?'Итоговая':'Текущая'}</div></div></div>
      <select id="league-select" data-slot="${c.slot}" class="form-input league-picker" aria-label="Выбрать лигу">${options}</select>
      ${tables}<p class="mini-disclaimer">${grouped?'Составы групп распределены движком VELTON, не повторяют официальную географию. ':''}Финансы — игровые оценки, не официальные бюджеты. Правила повышения/вылета упрощены.</p>`;
  }
  function seasonReview(c) {
    const r=c.season_report;
    if(!r)return '<div class="card">Отчёт сезона пока не найден.</div>';
    const stats=Object.entries(r.changes||{}).map(([k,v])=>{
      const label=ui.data.roles[c.role].stats.find(a=>a[0]===k)?.[1]||k;
      return `<div class="delta-line"><span>${esc(label)}</span><strong class="${v<0?'negative':''}">${v>0?'+':''}${v}</strong></div>`;
    }).join('')||'<div class="delta-line">Значимые показатели не изменились</div>';
    const moves=r.movements||[];
    const fg=r.football||{top_scorers:[],transfers:[],matches_played:0};
    return `<section class="season-report"><div class="end-mark">СЕЗОН ${c.season} ЗАВЕРШЁН</div>
      <h2>Итоги ${esc(r.period)}</h2><p>Результаты сохранены в истории этого слота.</p>
      <div class="report-grid"><div><strong>${r.decisions}</strong><small>Решений</small></div><div><strong>${r.successful}</strong><small>Успешных</small></div><div><strong>${r.simulated_leagues}</strong><small>Чемпионатов</small></div></div>
      <h3>Симулированные матчи</h3>
      <div class="card"><div class="delta-line"><span>Матчей в футбольном мире</span><strong>${fg.matches_played}</strong></div>
      ${fg.own_club?`<div class="delta-line"><span>Ваша команда — побед / ничьих / поражений</span><strong>${fg.own_club.wins} / ${fg.own_club.draws} / ${fg.own_club.losses}</strong></div>`:''}</div>
      <h3>Лучшие бомбардиры</h3><div class="card">${fg.top_scorers.length?fg.top_scorers.slice(0,5).map((p,i)=>`<div class="delta-line"><span>${i+1}. ${esc(p.name)} · ${esc(p.club)}</span><strong>${p.goals} гол.</strong></div>`).join(''):'Пока нет голевых событий с подтверждёнными игроками'}</div>
      <h3>Трансферы сезона</h3><div class="card">${fg.transfers.length?fg.transfers.map(t=>`<div class="delta-line"><span>${esc(t.player_name)} · ${esc(t.from_name)} → ${esc(t.to_name)}</span><strong>${euros(t.fee_eur)}</strong></div>`).join(''):'В этом сезоне сделок не было'}</div>
      ${r.my_finance?.closing_balance!=null?`<h3>Финансовый отчёт клуба</h3><div class="card">
        <div class="delta-line"><span>Баланс до закрытия</span><strong>${euros(r.my_finance.opening_balance)}</strong></div>
        <div class="delta-line"><span>Призовые</span><strong>${euros(r.my_finance.prize_eur)}</strong></div>
        <div class="delta-line"><span>Доход с матчей</span><strong>${euros(r.my_finance.match_income_eur)}</strong></div>
        <div class="delta-line"><span>Зарплаты за сезон (игровые)</span><strong>−${euros(r.my_finance.wages_eur)}</strong></div>
        <div class="delta-line"><span>Итоговый баланс</span><strong>${euros(r.my_finance.closing_balance)}</strong></div></div>`:''}
      <h3>Развитие за сезон</h3><div class="card">${stats}</div>
      <h3>Чемпионы</h3><div class="card">${r.league_summaries.length?r.league_summaries.slice(0,16).map(x=>`<div class="delta-line"><span>${esc(x.league)}</span><strong>${esc(x.champion)}</strong></div>`).join(''):'Для статистики чемпионатов необходимо импортировать реальные клубы.'}</div>
      <h3>Повышения и вылеты</h3><div class="card">${moves.length?moves.slice(0,40).map(m=>`<div class="delta-line"><span>${esc(m.club)}</span><strong>${m.type==='promotion'?'Повышение':'Вылет'} · ${esc(m.to)}</strong></div>`).join(''):'В этом сезоне переходов не было (не импортированы нужные дивизионы или правила не позволяют переходы).'}</div>
      <button class="primary-btn" data-action="advance-season" data-slot="${c.slot}">Перейти в новый сезон</button>
      <button class="retire-btn" data-action="retire" data-slot="${c.slot}">Завершить карьеру и удалить слот</button>
      <p class="mini-disclaimer">Удаление слота необратимо. Общие награды и опыт аккаунта останутся.</p>
    </section>`;
  }
  function careerPage(c) {
    const r=ui.data.roles[c.role];
    const stats = r.stats.map(([key,label])=>`<div class="metric-box"><div class="value">${cap(c.metrics[key] ?? 0)}</div><div class="label">${esc(label)}</div></div>`).join('');
    let center='';
    if(c.phase==='playing') center=`<div class="section-bar"><div><h2 class="section-title">Твоя история</h2><div class="section-sub">Каждое решение влияет на карьеру</div></div></div>
      <div class="event-card"><div class="event-tag">СОБЫТИЕ · НЕДЕЛЯ ${c.week}</div><h2>${esc(c.event.title)}</h2><p>${esc(c.event.text)}</p></div>
      <div class="choice-label">Как поступишь?</div>${c.event.choices.map(choice=>`<button class="choice" data-action="decide" data-slot="${c.slot}" data-choice="${choice.id}" ${ui.busy?'disabled':''}>
        <span><small class="choice-risk">${esc(choice.risk)}</small><strong>${esc(choice.title)}</strong><small>${esc(choice.detail)}</small></span>${ic('right')}</button>`).join('')}`;
    else if(c.phase==='ready')center=`<section class="season-ready"><div class="end-mark">12 ИЗ 12 НЕДЕЛЬ</div><h2>Сезон пройден</h2><p>Все решения приняты. Можно подвести итоги, определить чемпионов, повышения и вылеты.</p><button class="primary-btn" data-action="finish-season" data-slot="${c.slot}">Завершить сезон</button></section>`;
    else center=seasonReview(c);
    return `<div class="main">${header()}<button class="back" data-action="back">${ic('left')} К моим карьерам</button>
      <section class="career-head"><span class="small-tag">${esc(r.name.toUpperCase())} · СЛОТ ${c.slot}</span>
      <h1>${esc(c.name)}</h1><p>${esc(c.place)}</p><div class="career-meta">Сезон ${c.season} &nbsp;·&nbsp; ${c.phase==='playing'?`Неделя ${c.week} / 12`:c.phase==='ready'?'Ожидает завершения':'Итоги сезона'}</div></section>
      <div class="section-bar"><h2 class="section-title">Развитие</h2><span class="section-sub">${c.turns} решений</span></div>
      <div class="metric-grid">${stats}</div>
      ${c.my_club?`<div class="budget-bar"><strong>Финансы клуба ${esc(c.my_club.name)}</strong><div><span>Баланс: ${euros(c.my_club.budget_eur)}</span><span>Трансферы: ${euros(c.my_club.transfer_eur)}</span></div></div>`:''}
      ${c.my_club?`<section class="match-panel"><div class="section-bar"><h2 class="section-title">Матчи клуба</h2><span class="section-sub">${esc(c.my_club.name)}</span></div>
      ${c.my_fixtures?.length?c.my_fixtures.map(f=>`<div class="fixture-row"><span class="fixture-round">Тур ${f.round}</span><span class="fixture-match"><strong>${esc(f.home)}</strong> — <strong>${esc(f.away)}</strong></span><b class="fixture-score">${f.home_goals===null?'—':f.home_goals+' : '+f.away_goals}</b></div>`).join(''):'Календарь формируется после выбора реального клуба.'}
      <div class="career-tools"><button class="tool-btn" data-action="open-calendar" data-slot="${c.slot}">Календарь</button><button class="tool-btn" data-action="open-squad" data-slot="${c.slot}">Состав (${c.my_club.players||0})</button>
      ${['coach','club'].includes(c.role)&&c.phase==='playing'?`<button class="tool-btn" data-action="open-market" data-slot="${c.slot}">Трансферы</button>`:''}</div>
      ${['coach','club'].includes(c.role)&&c.phase==='playing'?`<div class="tactic-bar"><span>Тактика:</span>${[['balanced','Баланс'],['attack','Атака'],['defend','Оборона']].map(([id,name])=>`<button class="tactic-btn ${c.my_club.tactic===id?'active':''}" data-action="tactic" data-tactic="${id}" data-slot="${c.slot}">${name}</button>`).join('')}</div>`:''}
      </section>`:''}
      ${c.role==='agent'&&c.phase==='playing'?`<div class="career-tools"><button class="tool-btn" data-action="open-market" data-slot="${c.slot}">Открыть трансферный рынок</button></div>`:''}
      <div class="career-tools"><button class="tool-btn" data-action="open-archive" data-slot="${c.slot}">Архив сезонов</button></div>
      ${center}
      ${tableHTML(c)}
      ${c.phase==='playing'?`<div class="danger-line"><button class="danger-btn" data-action="delete" data-slot="${c.slot}">Удалить эту карьеру</button></div>`:''}
    </div>`;
  }
  function worldBrowserHTML(){
    const data=ui.worldBrowser;
    if(!data)return '';
    const leagues=data.leagues;
    return `<div class="main">${header()}<button class="back" data-action="close-world">${ic('left')} Вернуться</button>
      <h1 class="page-title">Футбольный мир</h1><p class="page-intro">35 стран · 80 чемпионатов · план около 1 500 клубов. Ни один неизвестный состав не подменяется вымышленным.</p>
      <div class="coverage-bar"><div class="coverage-heading"><strong>${ui.data.world_catalog.imported_leagues}/80</strong><span>лиг с клубами · ${ui.data.world_catalog.full_leagues} заполнены до планового числа</span></div>
      <div class="coverage-track"><div style="width:${Math.min(100,ui.data.world_catalog.imported_clubs/ui.data.world_catalog.target_clubs*100).toFixed(1)}%"></div></div>
      <small>${ui.data.world_catalog.imported_clubs}/${ui.data.world_catalog.target_clubs} клубов · ${ui.data.world_catalog.rosters?.clubs_20_plus ?? 0} составов по 20+ · ${ui.data.world_catalog.rosters?.clubs_empty ?? 0} без известных футболистов</small></div>
      <p class="source-notice">Списки команд некоторых лиг взяты из сезонов 2024/25–2025/26 и могут не совпадать с составом участников сезона 2026/27. Год указан рядом с лигой.</p>
      <div class="card">${leagues.map(l=>`<div class="world-league-row"><span><strong>${esc(l.country)} — ${esc(l.name)}</strong><small>${l.imported}/${l.intended_clubs} клубов · ${l.named_players} футболистов${l.source_season?' · источник '+esc(l.source_season):''}</small></span><button data-action="browse-league" data-league="${esc(l.id)}">Состав</button></div>`).join('')}</div>
      ${data.active?`<div class="section-bar"><h2 class="section-title">${esc(data.active.league)}</h2></div><div class="card">${data.active.clubs.length?data.active.clubs.map(c=>`<div class="world-club-row"><span><strong>${esc(c.name)}</strong><small>${c.players} известных игроков · ${euros(c.base_budget_eur)}</small></span><button data-action="browse-club" data-club="${esc(c.id)}">Состав</button></div>`).join(''):'Клубы пока не импортированы'}</div>`:''}
      ${data.club?`<div class="section-bar"><h2 class="section-title">${esc(data.club.club.name)}</h2></div>
       <div class="card"><p class="mini-disclaimer">Бюджет: ${euros(data.club.club.base_budget_eur)} · На трансферы: ${euros(data.club.club.base_transfer_eur)}. Суммы игровые, не официальные.</p><p class="mini-disclaimer">Состав: ${({'official_2026_27':'подтверждённая заявка 2026/27','historical_2026_07':'исторический снимок июля 2026, НЕ заявка 2026/27','partial_dated':'частичный исторический состав','no_named_players':'футболисты пока не подтверждены'})[data.club.roster_basis] || 'частично подтвержден'}. Источник клуба: ${esc(data.club.club.source)}.</p>
       ${data.club.players.length?data.club.players.map((p,i)=>`<div class="delta-line"><span>${i+1}. ${esc(p.name)}</span><small>${esc(positionRU(p.position))}</small></div>`).join(''):'Подтверждённые имена игроков пока не загружены.'}</div>`:''}
      </div>`;
  }
  function profilePage() {
    const p=ui.data.profile, achieved=ui.data.achievements.filter(a=>a.unlocked).length;
    const hist=ui.data.history.length?ui.data.history.map(h=>`<div class="timeline-item"><div class="timeline-dot"></div><div>
       <strong>${esc(h.title)}</strong><span>${esc(ui.data.roles[h.role]?.name||h.role)} · ${esc(h.choice)} · ${h.success?'Успешно':'Опыт'}</span>
       </div></div>`).join(''):'<p class="empty-history">Здесь появятся важные моменты твоих карьер после первых решений.</p>';
    return `<div class="main">${header()}<div class="eyebrow">Игровой аккаунт</div><h1 class="page-title">Мой профиль</h1><p class="page-intro">Единая история и награды за все карьеры VELTON.</p>
      <div class="profile-card"><div class="profile-identity"><div class="profile-avatar">${esc(initials(p.name))}</div>
      <div><div class="profile-name">${esc(p.name)}</div><div class="profile-handle">${p.username?'@'+esc(p.username):'Участник VELTON'}</div></div></div>
      <div class="level-progress"><span><b>Уровень ${p.level}</b><b>${p.current_level_xp} / 100 XP</b></span><div class="progress-track"><div class="progress-fill" style="width:${p.current_level_xp}%"></div></div></div></div>
      <section class="stat-grid"><div class="mini-stat"><strong>${ui.data.careers.length}</strong><small>Карьер</small></div><div class="mini-stat"><strong>${cap(p.decisions)}</strong><small>Решений</small></div><div class="mini-stat"><strong>${achieved}</strong><small>Наград</small></div></section>
      <p class="profile-sum">Завершено сезонов: <strong>${p.seasons_completed}</strong> · Завершено карьер: <strong>${p.retired_careers}</strong></p>
      <div class="section-bar"><div><h2 class="section-title">Достижения</h2><div class="section-sub">${achieved} из ${ui.data.achievements.length} открыто</div></div></div>
      <div class="achievements">${ui.data.achievements.map(a=>`<div class="award ${a.unlocked?'':'locked'}"><div class="award-mark">${esc(a.kind)}</div>
      <strong>${esc(a.name)}</strong><small>${esc(a.desc)}</small></div>`).join('')}</div>
      <div class="section-bar"><div><h2 class="section-title">Последние решения</h2><div class="section-sub">История твоего пути</div></div></div><div class="card timeline">${hist}</div>
    </div>`;
  }
  function roleModal() {
    if (ui.createSlot == null) return '';
    const selected=ui.createRole, info=selected?ui.data.roles[selected]:null;
    let content;
    if (!info) {
      content=`<div class="modal-head"><h2>Новая карьера</h2><button class="close" data-action="dismiss" aria-label="Закрыть">${ic('close')}</button></div>
        <p class="modal-intro">Слот ${ui.createSlot} из 5. Выбери, кем хочешь стать. Каждая роль — отдельный игровой путь.</p>
        ${Object.entries(ui.data.roles).map(([id,r])=>`<button class="role-option" data-action="choose-role" data-role="${id}">
        <span class="role-icon">${esc(r.short)}</span><span class="role-txt"><strong>${esc(r.name)}</strong><small>${esc(r.subtitle)}</small></span>${ic('right')}</button>`).join('')}`;
    } else {
      const pickClub=['player','coach','club'].includes(selected)&&ui.clubChoices.length>0;
      const locationField=pickClub?`<label class="form-label" for="career-league">Чемпионат</label>
        <select id="career-league" class="form-input">${ui.availableLeagues.map(x=>`<option value="${esc(x.id)}" ${x.id===ui.selectedLeague?'selected':''}>${esc(x.country)} · ${esc(x.name)}</option>`).join('')}</select>
        <label class="form-label" for="career-club">Первый клуб</label>
        <select id="career-club" class="form-input" name="club_id">${ui.clubChoices.map(x=>`<option value="${esc(x.id)}">${esc(x.name)}</option>`).join('')}</select>`:
        `<label class="form-label" for="character-place">${esc(info.place_label)}</label>
         <input id="character-place" class="form-input" name="place" maxlength="32" minlength="2" required value="${esc(info.default_place)}" />`;
      content=`<div class="modal-head"><h2>${esc(info.name)}</h2><button class="close" data-action="dismiss" aria-label="Закрыть">${ic('close')}</button></div>
        <p class="modal-intro">${esc(info.subtitle)}. Настрой историю и начни первую неделю.</p>
        <form id="new-career"><label class="form-label" for="character-name">${esc(info.name_label)}</label>
          <input id="character-name" class="form-input" name="name" maxlength="32" minlength="2" required placeholder="Например, Алексей Миронов" autocomplete="off" />
          ${locationField}
          <p class="form-caption">${pickClub?'Клуб выбран из реального каталога. Бюджеты — игровые оценки.':'Клубы и футболисты загружаются из каталога. Карьера строится на решениях и событиях.'}</p>
          <button class="primary-btn" type="submit" ${ui.busy?'disabled':''}>Начать карьеру</button>
          <button class="secondary-btn" type="button" data-action="choose-other">Выбрать другую роль</button></form>`;
    }
    return `<div class="modal-layer" role="dialog" aria-modal="true" aria-label="Новая карьера"><div class="modal"><div class="modal-handle"></div>${content}</div></div>`;
  }
  function resultModal() {
    if (!ui.result) return '';
    const r=ui.result.result;
    const changes = r.changes.length ? r.changes.map(c=>`<div class="delta-line"><span>${esc(c.label)}</span><strong class="${c.amount<0?'negative':''}">${c.amount>0?'+':''}${c.amount}</strong></div>`).join('') : '<p class="empty-history">Показатели остались прежними.</p>';
    const fresh = ui.result.new_awards.map(id=>ui.data.achievements.find(a=>a.id===id)?.name).filter(Boolean);
    return `<div class="modal-layer" role="dialog" aria-modal="true" aria-label="Итог решения"><div class="modal"><div class="modal-handle"></div>
      <div class="result-medal ${r.success?'':'missed'}">${ic(r.success?'check':'layers')}</div>
      <h2 class="result-title">${esc(r.title)}</h2><p class="result-copy">${esc(r.text)}</p>
      <div class="section-bar"><h3 class="section-title">Изменения</h3><span class="section-sub">+${r.xp_gain} XP</span></div>
      <div class="card">${changes}</div>${fresh.length?`<div class="award-new">Новая награда: ${esc(fresh.join(', '))}</div>`:''}
      <button class="primary-btn" data-action="dismiss-result">${bySlot(ui.career)?.phase==='ready'?'К завершению сезона':'Следующая неделя'}</button></div></div>`;
  }
  function marketModal(){
    if(!ui.market)return '';
    const m=ui.market,slot=m.slot,chosen=m.players.find(p=>p.player_id===ui.marketPlayer);
    const target= m.my_club||m.clubs[0]?.id;
    const targetSelector=m.my_club?`<div class="subtle-note">Покупатель: ${esc(m.clubs.find(c=>c.id===m.my_club)?.name||'ваш клуб')}</div>`:
        `<label class="form-label" for="offer-target">Клуб-покупатель</label><select id="offer-target" class="form-input">${m.clubs.map(c=>`<option value="${esc(c.id)}">${esc(c.name)} · бюджет ${euros(c.transfer_eur)}</option>`).join('')}</select>`;
    return `<div class="modal-layer" role="dialog" aria-modal="true" aria-label="Трансферный рынок"><div class="modal market-dialog"><div class="modal-handle"></div>
     <div class="modal-head"><h2>Трансферный рынок</h2><button class="close" data-action="close-market" aria-label="Закрыть">${ic('close')}</button></div>
     <p class="modal-intro">Реальные футболисты из каталога, игровой рынок. Стоимости и зарплаты условные; переходы влияют на состав и результаты матчей.</p>
     <form id="market-search-form" class="market-search"><input id="market-search" class="form-input" placeholder="Найти футболиста по имени" maxlength="60"/><button class="tool-btn" type="submit">Найти</button></form>
     <div class="market-results">${m.players.length?m.players.map(p=>`<button class="market-player ${ui.marketPlayer===p.player_id?'chosen':''}" data-action="pick-player" data-player="${esc(p.player_id)}"><span><strong>${esc(p.name)}</strong><small>${esc(p.club)} · ${esc(p.position||'Позиция не указана')} · OVR ${p.rating}</small></span><b>${euros(p.value_eur)}</b></button>`).join(''):'Футболисты не найдены. Попробуй другой запрос.'}</div>
     ${chosen?`<div class="offer-form"><h3>Предложение за ${esc(chosen.name)}</h3>${targetSelector}
       <label class="form-label" for="offer-eur">Сумма трансфера (€)</label>
       <input id="offer-eur" class="form-input" type="number" min="100000" max="2000000000" step="100000" value="${Math.ceil(chosen.value_eur*1.15/100000)*100000}"/>
       <p class="form-caption">Клуб согласится на предложение от 115% игровой стоимости. У покупателя должны быть деньги в балансе и трансферном бюджете.</p>
       <button class="primary-btn" data-action="offer-transfer" data-slot="${slot}">Отправить предложение</button></div>`:''}
     </div></div>`;
  }
  function squadModal(){
    if(!ui.squad)return '';
    const squad=ui.squad;
    return `<div class="modal-layer" role="dialog" aria-modal="true" aria-label="Состав клуба"><div class="modal market-dialog"><div class="modal-handle"></div>
     <div class="modal-head"><h2>${esc(squad.club)}</h2><button class="close" data-action="close-squad" aria-label="Закрыть">${ic('close')}</button></div>
     <p class="modal-intro">${esc(squad.disclaimer)}</p>
     <div class="squad-list">${squad.players.length?squad.players.map(p=>`<div class="squad-player"><div><strong>${esc(p.name)}</strong><small>${esc(positionRU(p.position))} · ${p.appearances} матчей · ${p.goals} голов · контракт до сезона ${p.contract_until_season||'—'}</small></div><div><b>${p.rating} OVR</b><small>${euros(p.value_eur)}</small></div></div>`).join(''):'Подтверждённые футболисты пока не загружены. Добавьте состав через импортёр.'}</div>
     </div></div>`;
  }
  function calendarModal(){
    if(!ui.calendar)return '';
    const cal=ui.calendar;
    return `<div class="modal-layer" role="dialog" aria-modal="true" aria-label="Календарь сезона"><div class="modal market-dialog"><div class="modal-handle"></div>
      <div class="modal-head"><h2>Календарь сезона ${cal.season}</h2><button class="close" data-action="close-calendar" aria-label="Закрыть">${ic('close')}</button></div>
      <p class="modal-intro">Встречи рассчитаны игровым движком VELTON. Реальные даты матчей и реальные результаты не используются.</p>
      <div class="calendar-list">${cal.fixtures.length?cal.fixtures.map(f=>`<div class="calendar-game"><small>Тур ${f.round}</small><span>${esc(f.home)} — ${esc(f.away)}</span><strong>${f.home_goals===null?'Ещё не сыгран':f.home_goals+' : '+f.away_goals}</strong></div>`).join(''):'Матчи выбранной лиги ещё не созданы.'}</div>
      </div></div>`;
  }
  function archiveModal(){
    if(!ui.archive)return '';
    const ar=ui.archive,report=ar.report;
    return `<div class="modal-layer" role="dialog" aria-modal="true" aria-label="Архив сезонов"><div class="modal market-dialog"><div class="modal-handle"></div>
      <div class="modal-head"><h2>Архив сезонов</h2><button class="close" data-action="close-archive" aria-label="Закрыть">${ic('close')}</button></div>
      ${ar.seasons.length?ar.seasons.map(s=>`<button class="archive-row" data-action="archived-report" data-slot="${ar.slot}" data-season="${s.season}"><span><strong>${esc(s.period)}</strong><small>Сезон ${s.season} · решений ${s.decisions} · матчей ${s.matches}</small></span>${ic('right')}</button>`).join(''):'Завершённых сезонов ещё нет.'}
      ${report?`<div class="archive-report"><h3>Итоги ${esc(report.period)}</h3>
        <p>Успешных решений: <b>${report.successful}</b> из ${report.decisions}; сыграно матчей: <b>${report.football?.matches_played||0}</b></p>
        ${report.my_finance?.closing_balance!=null?`<p>Клубный бюджет после сезона: <b>${euros(report.my_finance.closing_balance)}</b></p>`:''}
        <h4>Чемпионы лиг</h4>${(report.league_summaries||[]).map(g=>`<div class="delta-line"><span>${esc(g.league)}</span><strong>${esc(g.champion)}</strong></div>`).join('')}
        <h4>Трансферы</h4>${report.football?.transfers?.length?report.football.transfers.map(t=>`<div class="delta-line"><span>${esc(t.player_name)}</span><strong>${euros(t.fee_eur)}</strong></div>`).join(''):'<p>Не было сделок</p>'}
        <h4>Повышения и вылеты</h4>${report.movements?.length?report.movements.map(m=>`<div class="delta-line"><span>${esc(m.club)}</span><strong>${m.type==='promotion'?'Повышение':'Вылет'}</strong></div>`).join(''):'<p>Без изменений</p>'}
        </div>`:''}
      </div></div>`;
  }
  function render() {
    if (!ui.data) return;
    const career=ui.career!=null?bySlot(ui.career):null;
    if (ui.career!=null&&!career) ui.career=null;
    const content=ui.worldBrowser?worldBrowserHTML():career?careerPage(career):ui.page==='profile'?profilePage():ui.page==='careers'?careersPage():homePage();
    app.innerHTML=content+nav()+roleModal()+resultModal()+marketModal()+squadModal()+calendarModal()+archiveModal();
  }
  async function execute(fn) {
    if (ui.busy) return;
    ui.busy=true;
    try {await fn();} catch(e) {toast(e.message);} finally {ui.busy=false;render();}
  }
  async function deleteSlot(slot) {
    const message='Удалить карьеру из слота '+slot+'? Прогресс этой карьеры пропадёт. Общий уровень и достижения сохранятся.';
    const confirmed=telegram?.showConfirm ? await new Promise(resolve=>telegram.showConfirm(message,resolve)) : confirm(message);
    if (!confirmed) return;
    await execute(async()=>{const response=await request(`/api/careers/${slot}`,'DELETE');ui.data=response.state;ui.career=null;ui.page='careers';toast('Слот освобождён');});
  }
  app.addEventListener('click', async e=>{
    const btn=e.target.closest('[data-action]');
    if (!btn || ui.busy) return;
    const action=btn.dataset.action, slot=Number(btn.dataset.slot);
    if (action==='page') {ui.page=btn.dataset.page;ui.career=null;ui.createSlot=null;ui.result=null;render();window.scrollTo(0,0);}
    else if (action==='open'){ui.table=null;ui.career=slot;ui.page='careers';render();window.scrollTo(0,0);}
    else if (action==='back'){ui.career=null;ui.page='careers';render();window.scrollTo(0,0);}
    else if (action==='create'){ui.createSlot=slot;ui.createRole=null;ui.clubChoices=[];render();}
    else if (action==='choose-role'){
      ui.createRole=btn.dataset.role;render();
      if(['player','coach','club'].includes(ui.createRole)){
        await execute(async()=>{
          const resp=await request('/api/world/leagues');
          ui.availableLeagues=resp.leagues.filter(x=>x.imported>0);
          ui.selectedLeague=ui.availableLeagues[0]?.id||null;
          ui.clubChoices=ui.selectedLeague?(await request('/api/world/clubs?league='+encodeURIComponent(ui.selectedLeague))).clubs:[];
        });
      }
    }
    else if (action==='choose-other'){ui.createRole=null;render();}
    else if (action==='dismiss'){ui.createSlot=null;ui.createRole=null;render();}
    else if (action==='dismiss-result'){ui.result=null;render();}
    else if (action==='world-browser'){
      await execute(async()=>{const r=await request('/api/world/leagues');ui.worldBrowser={leagues:r.leagues,active:null};ui.career=null;});
    }
    else if (action==='close-world'){ui.worldBrowser=null;render();}
    else if (action==='browse-league'){
      await execute(async()=>{const r=await request('/api/world/clubs?league='+encodeURIComponent(btn.dataset.league));ui.worldBrowser.active=r;ui.worldBrowser.club=null;});
    }
    else if (action==='browse-club'){
      await execute(async()=>{const data=await request('/api/world/clubs/'+encodeURIComponent(btn.dataset.club));ui.worldBrowser.club=data;});
    }
    else if (action==='finish-season'){
      await execute(async()=>{const r=await request(`/api/careers/${slot}/season/finish`,'POST');ui.data=r.state;ui.table=null;toast('Сезон завершён. Итоги готовы.'+(r.new_awards?.length?' Открыта награда!':''));});
    }
    else if (action==='advance-season'){
      await execute(async()=>{const r=await request(`/api/careers/${slot}/season/advance`,'POST');ui.data=r.state;ui.table=null;toast('Новый сезон: таблицы обнулены, сделок ИИ: '+(r.offseason?.length||0)+'.');});
    }
    else if (action==='retire'){
      const message='Завершить карьеру и НАВСЕГДА удалить слот '+slot+'? Продолжить эту карьеру будет невозможно.';
      const confirmed=telegram?.showConfirm?await new Promise(resolve=>telegram.showConfirm(message,resolve)):confirm(message);
      if(!confirmed)return;
      await execute(async()=>{const r=await request(`/api/careers/${slot}/season/retire`,'POST',{confirmation:'DELETE'});ui.data=r.state;ui.career=null;ui.page='careers';ui.table=null;toast('Карьера завершена. Слот освобождён.');});
    }
    else if (action==='delete'){await deleteSlot(slot);}
    else if (action==='open-calendar'){
      const c=bySlot(slot);
      const league=ui.table?.slot===slot?ui.table.data.selected:c?.world?.selected;
      const query=league?'?league='+encodeURIComponent(league):'';
      await execute(async()=>{ui.calendar=await request(`/api/careers/${slot}/fixtures`+query);});
    }
    else if (action==='close-calendar'){ui.calendar=null;render();}
    else if (action==='open-archive'){
      await execute(async()=>{const r=await request(`/api/careers/${slot}/archive`);ui.archive={...r,slot,report:null};});
    }
    else if (action==='archived-report'){
      await execute(async()=>{const r=await request(`/api/careers/${slot}/archive/${Number(btn.dataset.season)}`);ui.archive.report=r.report;});
    }
    else if (action==='close-archive'){ui.archive=null;render();}
    else if (action==='tactic'){
      await execute(async()=>{const r=await request(`/api/careers/${slot}/tactic`,'POST',{tactic:btn.dataset.tactic});ui.data=r.state;toast('Тактика обновлена. Применится к следующим матчам.');});
    }
    else if (action==='open-squad'){
      await execute(async()=>{ui.squad=await request(`/api/careers/${slot}/squad`);});
    }
    else if (action==='close-squad'){ui.squad=null;render();}
    else if (action==='open-market'){
      await execute(async()=>{const m=await request(`/api/careers/${slot}/market`);ui.market={...m,slot};ui.marketPlayer=null;});
    }
    else if (action==='close-market'){ui.market=null;ui.marketPlayer=null;render();}
    else if (action==='pick-player'){ui.marketPlayer=btn.dataset.player;render();}
    else if (action==='offer-transfer'){
      const player=ui.marketPlayer;
      const offer=Number(document.getElementById('offer-eur')?.value);
      const target=document.getElementById('offer-target')?.value||ui.market?.my_club;
      if(!player||!target||!Number.isInteger(offer)){toast('Выбери футболиста, клуб и сумму');return;}
      await execute(async()=>{const r=await request(`/api/careers/${slot}/transfer`,'POST',{player_id:player,target_club_id:target,offer_eur:offer});ui.data=r.state;
      const m=await request(`/api/careers/${slot}/market`);ui.market={...m,slot};ui.marketPlayer=null;toast('Трансфер оформлен: '+r.deal.player+' · '+euros(r.deal.fee_eur));});
    }
    else if (action==='decide') {
      const c=bySlot(slot);
      await execute(async()=>{
        const response=await request(`/api/careers/${slot}/decide`,'POST',{event_id:c.event.id,choice_id:Number(btn.dataset.choice),expected_turn:c.turns});
        ui.data=response.state;ui.result=response;telegram?.HapticFeedback?.notificationOccurred(response.result.success?'success':'warning');
      });
    }
  });
  app.addEventListener('change', async e=>{
    if(e.target.id==='career-league'){
      const league=e.target.value;
      await execute(async()=>{const r=await request('/api/world/clubs?league='+encodeURIComponent(league));ui.selectedLeague=league;ui.clubChoices=r.clubs;});
    }
    if(e.target.id==='league-select'){
      const slot=Number(e.target.dataset.slot);
      await execute(async()=>{const data=await request(`/api/careers/${slot}/table?league=`+encodeURIComponent(e.target.value));ui.table={slot,data};});
    }
  });
  app.addEventListener('submit', async e=>{
    if(e.target.id==='market-search-form'){
      e.preventDefault();const query=document.getElementById('market-search')?.value.trim()||'';
      const slot=ui.market?.slot;
      if(slot)await execute(async()=>{const m=await request(`/api/careers/${slot}/market?search=`+encodeURIComponent(query));ui.market={...m,slot};ui.marketPlayer=null;});
      return;
    }
    if(e.target.id!=='new-career') return;
    e.preventDefault();
    const form=e.target;
    const name=form.elements.name.value.trim();
    const chosenId=form.elements.club_id?.value || null;
    const chosenClub=ui.clubChoices.find(x=>x.id===chosenId);
    const place=chosenClub?.name || form.elements.place?.value?.trim() || '';
    if(name.length<2||place.length<2){toast('Заполни оба поля');return;}
    const slot=ui.createSlot,role=ui.createRole;
    await execute(async()=>{
      const response=await request(`/api/careers/${slot}/create`,'POST',{role,name,place,club_id:chosenId});
      ui.data=response.state;ui.table=null;ui.createSlot=null;ui.createRole=null;ui.career=slot;ui.page='careers';
      toast('Карьера создана');window.scrollTo(0,0);
    });
  });
  load();
})();
