"""Verified senior rosters / dated, offline player-snapshot regression checks."""
import pytest
from fastapi.testclient import TestClient
import server
from test_api import TOKEN, auth
from verified_rosters import update_verified_catalog, official_first_team, featured_clubs

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'DB_PATH', tmp_path/'v08.sqlite3')
    monkeypatch.setattr(server, 'BOT_TOKEN', TOKEN)
    monkeypatch.setattr(server, 'DEMO_MODE', False)
    with TestClient(server.app) as c:
        yield c


def test_29_official_club_rosters_and_692_listed_players(client):
    assert len(official_first_team()) == 20
    assert len(featured_clubs()) == 9
    with server.connection() as db:
        assert db.execute('SELECT COUNT(*) FROM player_catalog').fetchone()[0] == 1070
        assert db.execute('SELECT COUNT(*) FROM roster_verified_clubs').fetchone()[0] == 29
        assert db.execute('SELECT COUNT(*) FROM player_catalog WHERE confirmed_2627=1').fetchone()[0] == 692
        active=db.execute('''SELECT COUNT(*) FROM player_catalog p WHERE NOT EXISTS (
            SELECT 1 FROM roster_verified_clubs v WHERE v.club_id=p.club_id) OR confirmed_2627=1''').fetchone()[0]
        assert active == 1009
        errors=db.execute('''SELECT v.club_id,v.verified_players,count(p.id) as ct
              FROM roster_verified_clubs v LEFT JOIN player_catalog p ON p.club_id=v.club_id AND p.confirmed_2627=1
              GROUP BY v.club_id HAVING ct<>v.verified_players''').fetchall()
        assert not errors, [dict(e) for e in errors]
        before=active
        result=update_verified_catalog(db)
        assert result['added']==result['moved']==0
        assert result['ambiguous']==[]
        after=db.execute('SELECT COUNT(*) FROM player_catalog').fetchone()[0]
        assert after==1070 and before==active


def test_api_only_shows_verified_for_clubs_with_official_roster(client):
    all_leagues=client.get('/api/world/leagues',headers=auth()).json()['leagues']
    assert sum(x['named_players'] for x in all_leagues)==1009
    for lid,name in [('ENG_1','Arsenal'),('ESP_1','Real Madrid'),('ITA_1','Napoli'),('FRA_1','Paris Saint-Germain FC')]:
        ls=client.get('/api/world/clubs',params={'league':lid},headers=auth()).json()['clubs']
        target=next(x for x in ls if x['name']==name)
        res=client.get('/api/world/clubs/'+target['id'],headers=auth()).json()
        assert res['verified_first_team']['season']=='2026/27'
        assert 18<=len(res['players'])<=30
        assert target['players']==len(res['players'])
        assert res['verified_first_team']['verified_players']==len(res['players'])


def test_new_slots_do_not_create_historical_duplicate_footballers(client):
    c=client.get('/api/world/clubs',params={'league':'ENG_1'},headers=auth()).json()['clubs']
    club=next(x for x in c if x['name']=='Arsenal')
    r=client.post('/api/careers/1/create',headers=auth(),json={'role':'coach','name':'Manager','place':'London','club_id':club['id']})
    assert r.status_code==200,r.text
    with server.connection() as db:
        assert db.execute('SELECT COUNT(*) FROM world_players WHERE user_id=41 AND slot=1').fetchone()[0]==1009
        for row in db.execute('SELECT club_id,verified_players FROM roster_verified_clubs'):
            count=db.execute('SELECT COUNT(*) FROM world_players WHERE user_id=41 AND slot=1 AND club_id=?',(row['club_id'],)).fetchone()[0]
            assert count==row['verified_players']
        old_memberships=db.execute('''SELECT wp.player_id,wp.club_id FROM world_players wp
            WHERE wp.user_id=41 AND wp.slot=1 ORDER BY wp.player_id''').fetchall()
        old_snapshot=[tuple(r) for r in old_memberships]
        again=server.init_db()
        assert again is None
        new_snapshot=[tuple(r) for r in db.execute('''SELECT wp.player_id,wp.club_id FROM world_players wp
            WHERE wp.user_id=41 AND wp.slot=1 ORDER BY wp.player_id''')]
        assert old_snapshot==new_snapshot


def test_v07_career_upgrade_preserves_world_and_new_career_gets_v08_players(tmp_path, monkeypatch):
    """Simulate a saved v0.7 world BEFORE applying the v0.8 starting-roster overlay."""
    monkeypatch.setattr(server, 'DB_PATH', tmp_path/'upgraded.sqlite3')
    monkeypatch.setattr(server, 'BOT_TOKEN', TOKEN)
    monkeypatch.setattr(server, 'DEMO_MODE', False)
    clubs=None

    def old_schema_only(conn):
        conn.execute('ALTER TABLE player_catalog ADD COLUMN confirmed_2627 INTEGER NOT NULL DEFAULT 0')
        conn.execute('''CREATE TABLE IF NOT EXISTS roster_verified_clubs(
              club_id TEXT PRIMARY KEY, source_url TEXT NOT NULL, season TEXT NOT NULL,
              verified_players INTEGER NOT NULL)''')

    with monkeypatch.context() as m:
        m.setattr(server, 'update_verified_catalog', old_schema_only)
        with TestClient(server.app) as old:
            assert old.get('/api/state',headers=auth()).json()['world_catalog']['imported_players']==761
            leagues=old.get('/api/world/clubs',params={'league':'ENG_1'},headers=auth()).json()['clubs']
            cid=next(c['id'] for c in leagues if c['name']=='Arsenal')
            r=old.post('/api/careers/1/create',headers=auth(),json={
                'role':'coach','name':'Old season','place':'London','club_id':cid})
            assert r.status_code==200,r.text
            with server.connection() as db:
                original=[tuple(x) for x in db.execute('SELECT player_id,club_id FROM world_players WHERE user_id=41 AND slot=1 ORDER BY player_id')]
                assert len(original)==761
    with TestClient(server.app) as new:
        assert new.get('/api/state',headers=auth()).json()['world_catalog']['imported_players']==1070
        with server.connection() as db:
            untouched=[tuple(x) for x in db.execute('SELECT player_id,club_id FROM world_players WHERE user_id=41 AND slot=1 ORDER BY player_id')]
        assert original==untouched
        r=new.post('/api/careers/2/create',headers=auth(),json={
            'role':'coach','name':'New season','place':'London','club_id':cid})
        assert r.status_code==200,r.text
        with server.connection() as db:
            assert db.execute('SELECT count(*) FROM world_players WHERE user_id=41 AND slot=2').fetchone()[0]==1009
            assert db.execute('SELECT count(*) FROM world_players WHERE user_id=41 AND slot=1').fetchone()[0]==761
