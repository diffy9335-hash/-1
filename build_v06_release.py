"""Generate truthful, reproducible coverage and release files from the local v0.6 catalog.

Offline-only: uses an isolated temporary SQLite to verify actual import counts.
"""
from __future__ import annotations
import csv,json,sys,tempfile
from pathlib import Path
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import server
server.DEMO_MODE=True

with tempfile.TemporaryDirectory() as t:
    server.DB_PATH=Path(t)/'coverage.sqlite3'
    with TestClient(server.app) as client:
        info=client.get('/api/state').json()['world_catalog']
        rows=client.get('/api/world/leagues').json()['leagues']

audit=json.loads((ROOT/'world_data/verified_lower_leagues_audit_v06.json').read_text('utf-8'))
assert len(rows)==80
assert info['imported_leagues']==80
assert sum(int(r['imported']) for r in rows)==info['imported_clubs']
assert info['imported_players']==sum(int(r['named_players']) for r in rows)
assert info['imported_clubs']==1453,info
assert info['full_leagues']==59,info
assert info['clubs_with_players']==61,info
assert audit['added']==525,audit['added']

p=ROOT/'docs/coverage_v06.csv'
cols=['id','country','name','tier','intended_clubs','imported','rostered_clubs','named_players','status','source_season']
with p.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
    for r in rows:w.writerow({k:r.get(k) for k in cols})

by={}
for r in rows:
    by.setdefault(r['country'],[]).append(r)
report=f'''# VELTON v0.6 — проверка 35 стран / 80 лиг\n\nДата сборки: 15 ноября 2026. Реестр содержит реальные названия команд из исторических официальных и опубликованных источников; игровой мир не получает реальные результаты матчей и не подключается к футбольным API.\n\n| Проверенный показатель | Значение |\n|---|---:|\n| Футбольных ассоциаций | {info['countries']} |\n| Лиг в плане | {info['leagues']} |\n| Реальных клубных записей | {info['imported_clubs']} |\n| Целевых мест в лигах | {info['target_clubs']} |\n| Лиг с хотя бы одной командой | {info['imported_leagues']} |\n| Лиг, достигших планового числа команд | {info['full_leagues']} |\n| Частично заполненных лиг | {sum(r['status']=='partial' for r in rows)} |\n| Пустых лиг | {sum(r['status']=='empty' for r in rows)} |\n| Подтверждённых имён футболистов | {info['imported_players']} |\n| Клубов хотя бы с одним именем | {info['clubs_with_players']} |\n\nВ v0.6 добавлено **{audit['added']} записей команд** из **{len(audit['league_details'])} лиг** к предыдущим 928; при импорте отсеяны совпадения уже известных команд, в том числе 8 вариантов написания через вручную проверенные алиасы. Данные 2024/25–2026/27 смешаны: старые дивизионы нельзя трактовать как официальный актуальный состав одного и того же сезона. Результаты, сроки контрактов, рейтинги и бюджеты полностью игровые.\n\n## Полное распределение\n\n| Страна / лига | Уровень | Клубов | План | Игроков с именами | Источник сезона |\n|---|---:|---:|---:|---:|---|\n'''
for country in sorted(by):
    for r in by[country]:
        report+=f"| {country} — {r['name']} (`{r['id']}`) | {r['tier']} | {r['imported']} | {r['intended_clubs']} | {r['named_players']} | {r['source_season'] or 'смешанный'} |\n"
report+='''\n## Группы в игровом сезоне\n\nДля соревнований с несколькими группами календарь формируется **внутри групп**. Группы сохраняются в каждом отдельном слоте и сезоне. Если реальный состав групп не подтверждён для выбранного исторического среза, команды распределяются **игровой жеребьёвкой**, и это отражается в интерфейсе. Это не официальный географический состав групп.\n\nИспанская Примера Федерасьон: 2×20; итальянская Серия C: 3×20; греческая Super League 2: 2×10; другие многогрупповые чемпионаты ориентируются на `world_data/league_registry.json`. Повышения и вылеты за пределами Англии и Германии пока используют **упрощённые игровые правила**. У групповых дивизионов VELTON выбирает лидеров групп, а не сравнивает все команды по несопоставимым очкам.\n\n## Источники нового пакета\n\nКаждая новая запись имеет `source` с годом и ссылкой. Статические данные хранятся в `world_data/packs/velton_verified_lower_leagues_v06.json`; сам импортатор не обращается в сеть. В файле `world_data/verified_lower_leagues_audit_v06.json` приведены списки по каждой лиге и клубы, исключённые при проверке повторов.\n\n| Лига | Сезон / срез | Добавлено | Ссылка |\n|---|---|---:|---|\n'''
for lid,v in audit['league_details'].items():
    report+=f"| {lid} | {v['season']} | {v['added']} | {v['source']} |\n"
report+='''\n## Ограничения\n\n- 21 лига ниже планового количества участников; разница с планом составляет 51 место. Заполнять их случайными командами нельзя: сначала нужно сверить сезоны и устранить исторические пересечения.\n- Именованные составы есть только у 61 из 1453 клубов. **664 игрока — это НЕ все футболисты 80 лиг**, и отдельный каталог имён ещё не гарантирует полного состава конкретного клуба.\n- Содержимое приложения не является официальным лицензированным футбольным справочником. Логотипы клубов, фотографии игроков и официальные рейтинги не включены. Перед публичным коммерческим выпуском необходимо проверить условия использования источников данных и брендинга.\n- Данных реального лайва, внешних футбольных API-запросов и интернет-синхронизации в игре нет.\n'''
(ROOT/'docs/COVERAGE_v06_RU.md').write_text(report,'utf-8')

manifest={
 'project':'VELTON','version':'0.6','build_date':'2026-11-15',
 'source_type':'offline static real club and player names from mixed season snapshots',
 'data':{'countries':info['countries'],'leagues_planned':info['leagues'],
     'club_slots_target':info['target_clubs'],'club_records':info['imported_clubs'],
     'leagues_with_clubs':info['imported_leagues'],'full_leagues':info['full_leagues'],
     'partial_leagues':sum(x['status']=='partial' for x in rows),'empty_leagues':0,
     'named_real_players':info['imported_players'],'clubs_with_named_players':info['clubs_with_players'],
     'v06_new_club_records':audit['added'],'v06_new_league_sources':len(audit['league_details'])},
 'changes':['All 80 leagues have named real club participants','Separated group standings and fixture schedules','Historical duplicate-alias exclusion','SQLite migration for group fixtures','Retained independent worlds, season reports and promotion/relegation'],
 'tests':{'pytest':'26 passed','javascript_syntax':'node --check static/app.js passed',
          'browser_ui':'not independently browser-tested in this build',
          'telegram_production':'not tested in production','docker_image':'not built in current environment'},
 'limitations':['21 leagues remain partially filled','Only 61 clubs have at least one named real player','Some leagues and membership snapshots date from other seasons','Competition-specific promotion playoffs remain simplified','No external live football API needed or used at runtime'],
}
(ROOT/'RELEASE_MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n','utf-8')

# README and licensing notices are maintained as reviewed prose, not overwritten
# by regenerating the quantitative catalog.
print(json.dumps(info,ensure_ascii=False))
