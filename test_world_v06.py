"""VELTON 0.6 regression: all 80 leagues, independent group fixtures and seasons."""
from collections import Counter
from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient
import server
from test_api import TOKEN, auth

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB_PATH',tmp_path/'v06.sqlite3')
    monkeypatch.setattr(server,'BOT_TOKEN',TOKEN)
    monkeypatch.setattr(server,'DEMO_MODE',False)
    with TestClient(server.app) as c:
        yield c


def make_coach(client, league='ESP_3', slot=1):
    clubs=client.get('/api/world/clubs',params={'league':league},headers=auth()).json()['clubs']
    assert clubs
    res=client.post(f'/api/careers/{slot}/create',headers=auth(),json={
        'role':'coach','name':'Тренер группы','place':'Проверка','club_id':clubs[0]['id']})
    assert res.status_code==200,res.text
    return clubs[0]['id']


def play_season(client,slot):
    for i in range(12):
        career=next(x for x in client.get('/api/state',headers=auth()).json()['careers'] if x['slot']==slot)
        res=client.post(f'/api/careers/{slot}/decide',headers=auth(),json={
            'event_id':career['event']['id'],'choice_id':i%3,'expected_turn':career['turns']})
        assert res.status_code==200,res.text
    res=client.post(f'/api/careers/{slot}/season/finish',headers=auth())
    assert res.status_code==200,res.text
    return res.json()['report']


def test_complete_80_league_catalog_provenance_and_no_fictional_teams(client):
    st=client.get('/api/state',headers=auth()).json()['world_catalog']
    assert (st['countries'],st['leagues'],st['imported_leagues'],st['imported_clubs'])==(35,80,80,1453)
    assert st['imported_players']==1070
    rows=client.get('/api/world/leagues',headers=auth()).json()['leagues']
    assert sum(x['status']=='empty' for x in rows)==0
    assert sum(x['status']=='complete' for x in rows)==59
    assert sum(x['status']=='partial' for x in rows)==21
    for name,lid in [('AC Renate','ITA_3'),('VV Katwijk','NED_3'),('Phoenix Rising FC','USA_2')]:
        assert any(x['name']==name for x in client.get('/api/world/clubs',params={'league':lid},headers=auth()).json()['clubs'])
    with server.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM club_catalog WHERE source='' OR source IS NULL").fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM player_catalog').fetchone()[0]==1070


def test_three_groups_italy_and_two_groups_greece_do_not_play_across_groups(client):
    make_coach(client,league='ITA_3')
    italian=client.get('/api/careers/1/table',params={'league':'ITA_3'},headers=auth()).json()
    assert len(italian['groups'])==3
    assert [len(g['rows']) for g in italian['groups']]==[20,20,20]
    greek=client.get('/api/careers/1/table',params={'league':'GRE_2'},headers=auth()).json()
    assert len(greek['groups'])==2
    assert [len(g['rows']) for g in greek['groups']]==[10,10]
    with server.connection() as conn:
        for lid,expected,gsize in [('ITA_3',1140,20),('GRE_2',180,10),('ESP_3',760,20)]:
            matches=conn.execute('SELECT home_id,away_id,group_no FROM game_fixtures WHERE user_id=41 AND slot=1 AND season=1 AND league_id=?',(lid,)).fetchall()
            assert len(matches)==expected,(lid,len(matches))
            groups={r['club_id']:r['group_no'] for r in conn.execute('SELECT club_id,group_no FROM game_group_memberships WHERE user_id=41 AND slot=1 AND season=1 AND league_id=?',(lid,))}
            assert len(groups)==({ 'ITA_3':60,'GRE_2':20,'ESP_3':40}[lid])
            assert all(groups[m['home_id']]==groups[m['away_id']]==m['group_no'] for m in matches)
            games=Counter(cid for m in matches for cid in (m['home_id'],m['away_id']))
            assert all(n==2*(gsize-1) for n in games.values())


def test_end_of_season_group_promotion_and_new_season_resets_only_current_save(client):
    make_coach(client,'ESP_3',1)
    make_coach(client,'ESP_3',2)
    before2=client.get('/api/careers/2/table',params={'league':'ESP_3'},headers=auth()).json()
    assert all(r['played']==0 for r in before2['rows'])
    report=play_season(client,1)
    assert report['simulated_leagues']==80
    assert sum(x['type']=='promotion' and x['from']=='ESP_3' for x in report['movements'])==2
    review=client.get('/api/careers/1/table',params={'league':'ESP_3'},headers=auth()).json()
    assert len(review['groups'])==2
    assert all(r['played']==38 for g in review['groups'] for r in g['rows'])
    with server.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM game_fixtures WHERE user_id=41 AND slot=1 AND season=1 AND league_id=\'ESP_3\' AND home_goals IS NOT NULL').fetchone()[0]==760
    res=client.post('/api/careers/1/season/advance',headers=auth())
    assert res.status_code==200,res.text
    new=client.get('/api/careers/1/table',params={'league':'ESP_3'},headers=auth()).json()
    assert all(r['played']==0 and r['points']==0 and r['gf']==0 for r in new['rows'])
    assert len(new['groups'])==2
    archived=client.get('/api/careers/1/archive/1',headers=auth())
    assert archived.status_code==200
    later2=client.get('/api/careers/2/table',params={'league':'ESP_3'},headers=auth()).json()
    assert all(r['played']==0 for r in later2['rows'])
    assert client.post('/api/careers/1/season/advance',headers=auth()).status_code==409
