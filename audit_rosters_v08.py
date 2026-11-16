"""Rebuild a disposable offline catalog and audit first-team coverage (no football API)."""
import csv
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
from world import init_world_db
from offline_catalog import seed_local_catalog
from verified_rosters import update_verified_catalog


def audit():
    db=sqlite3.connect(':memory:')
    db.row_factory=sqlite3.Row
    init_world_db(db)
    seed_local_catalog(db)
    delta=update_verified_catalog(db)
    leagues=[]
    for lid,country,name in [('ENG_1','Англия','АПЛ'),('ESP_1','Испания','Ла Лига'),
                             ('GER_1','Германия','Бундеслига'),('ITA_1','Италия','Серия А'),
                             ('FRA_1','Франция','Лига 1')]:
        all_clubs=db.execute('SELECT id FROM club_catalog WHERE league_id=?',(lid,)).fetchall()
        official=db.execute('''SELECT count(*) ct, coalesce(sum(verified_players),0) total
               FROM roster_verified_clubs WHERE club_id IN (SELECT id FROM club_catalog WHERE league_id=?)''',(lid,)).fetchone()
        source_players=db.execute('''SELECT count(*) FROM player_catalog p
                JOIN club_catalog c on c.id=p.club_id WHERE c.league_id=? AND
                (NOT EXISTS(SELECT 1 FROM roster_verified_clubs v WHERE v.club_id=p.club_id)
                 OR p.confirmed_2627=1)''',(lid,)).fetchone()[0]
        leagues.append({'league_id':lid,'country':country,'league':name,'clubs':len(all_clubs),
                        'official_first_teams':official['ct'], 'official_first_team_players':official['total'],
                        'all_named_players_available_new_slots':source_players})
    all_clubs=db.execute('SELECT COUNT(*) FROM club_catalog').fetchone()[0]
    players=db.execute('SELECT COUNT(*) FROM player_catalog').fetchone()[0]
    active=db.execute('''SELECT COUNT(*) FROM player_catalog p WHERE NOT EXISTS (
         SELECT 1 FROM roster_verified_clubs vr WHERE vr.club_id=p.club_id) OR p.confirmed_2627=1''').fetchone()[0]
    dupes=db.execute('''SELECT club_id, count(*) ct FROM player_catalog WHERE confirmed_2627=1
        GROUP BY club_id HAVING ct<> (SELECT verified_players FROM roster_verified_clubs WHERE club_id=player_catalog.club_id)''').fetchall()
    if dupes or delta['ambiguous'] or len(leagues)!=5 or all_clubs!=1453:
        raise RuntimeError(f'Bad roster audit: {dupes}, {delta["ambiguous"]}, {all_clubs}')
    summary={'clubs_total':all_clubs,'players_stored':players,'players_eligible_in_new_slots':active,
             'official_verified_clubs':delta['clubs'],'official_verified_entries':delta['published'],
             'new_player_records_vs_v07':delta['added'],'reassigned_existing_players':delta['moved'],
             'source_date':'2026-11-15 build (2026/27 club squad snapshots)'}
    db.close()
    return summary,leagues


def write_docs(summary,leagues):
    docs=ROOT/'docs';docs.mkdir(exist_ok=True)
    with (docs/'coverage_v08.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(leagues[0]));writer.writeheader();writer.writerows(leagues)
    header='''# VELTON v0.8 — проверка реальных составов\n\nДата сборки: **15 ноября 2026**. В Mini App полностью автономная футбольная симуляция: **данные один раз включены в приложение, запросов к футбольным API нет**.\n\n## Фактический охват\n\n'''
    points=(f'- **{summary["clubs_total"]} настоящих клубов** во всех 80 лигах — без изменений относительно v0.7.\n'
            f'- **{summary["players_stored"]}** именованных записей в мастер-каталоге (бывшие снимки + новые).\n'
            f'- **{summary["players_eligible_in_new_slots"]}** футболистов доступны при создании нового слота. Исторические игроки, отсутствующие в подтверждённой первой команде клуба, оставлены в БД для старых сохранений, но исключены из новых.\n'
            f'- **{summary["official_verified_clubs"]} клубов** с датированными составами 2026/27, **{summary["official_verified_entries"]}** футболистов, распределённых по этим клубам.\n'
            f'- **{summary["new_player_records_vs_v07"]}** уникальных записей добавлено к v0.7, **{summary["reassigned_existing_players"]}** существующих игрока уточнили клубную принадлежность в стартовом каталоге.\n'
            '- Клубные бюджеты, зарплаты, трансферные суммы и рейтинги — **игровые**, а не официальные финансовые данные.\n\n')
    lines=['| Страна | Чемпионат | Клубов | Подтверждённые составы | Игроки из подтверждённых составов | Все доступные имена* |',
           '|---|---|---:|---:|---:|---:|']
    for l in leagues:
        lines.append(f'| {l["country"]} | {l["league"]} | {l["clubs"]} | {l["official_first_teams"]}/{l["clubs"]} | {l["official_first_team_players"]} | {l["all_named_players_available_new_slots"]} |')
    lines.append('')
    notes='''*Всё ещё встречаются неполные составы, собранные по историческим источникам. Для остальных **67 из 96** клубов пяти ведущих лиг НЕ заявляем о полноте. Официальный список АПЛ содержит зарегистрированных взрослых футболистов и НЕ гарантирует всех игроков академий/U21. Для остальных 9 клубов используются публичные страницы клубов/номера футболистов; это датированные снимки, а не синхронизация в реальном времени.*

## Как предотвращаем дубли и порчу старых слотов

- Проверка по нормализованному имени в глобальной базе. Неоднозначные совпадения не переназначаются автоматически.
- `roster_verified_clubs` хранит ссылку на источник, сезон и объём заявки.
- `confirmed_2627` отмечает, кого допустимо включить в **новый** игровой мир клуба с подтверждённым составом. Остальные исторические записи в этой команде не удаляются.
- `world_players` копируется при создании карьеры. Новые данные изменяют только стартовую базу; трансферы, участники и результаты существующих карьер не переносятся в другие слоты.
- Повторная загрузка того же каталога не создаёт новых футболистов.

## Источники

- Англия, зарегистрированные составы 2026/27: https://www.premierleague.com/en/news/4706139/see-all-the-202627-premier-league-squad-lists
- Испания: https://www.realmadrid.com/en-US/news/football/first-team/latest-news/dorsales-del-real-madrid-para-la-temporada-2026-27-10-08-2026 ; https://www.fcbarcelona.com/en/football/first-team/news/4570894/202627-first-team-jersey-numbers-confirmed ; https://en.atleticodemadrid.com/jugadores-primer-equipo/
- Германия: https://fcbayern.com/en/teams/first-team ; https://www.bvb.de/de/en/news/news-overview/news.html/2026/8/20/These-are-the-jersey-numbers-for-the-2026/27-season.html
- Италия: https://www.juventus.com/en/teams/first-team-men/squad/ ; https://sscnapoli.it/en/stagione/rosa
- Франция: https://www.psg.fr/en/mens-football/squad/season/2026-2027 ; https://www.om.fr/en/team/men

Все имена в собственных списках проекта — выборочно зафиксированные факты; копии страниц, эмблемы и фотографии не поставляются. Для публичной коммерческой игры требуется отдельно проверить применимость прав к названиям, символике и поставляемым данным. Лицензии и прочие источники v0.5–v0.7 описаны в `THIRD_PARTY_NOTICES.md`.
'''
    (docs/'COVERAGE_v08_RU.md').write_text(header+points+'\n'.join(lines)+'\n'+notes,encoding='utf-8')

if __name__=='__main__':
    s,leagues=audit()
    print('VELTON v0.8 offline audit:',s)
    for item in leagues: print(item)
    if '--write' in sys.argv:
        write_docs(s,leagues)
