"""Regression tests: true match progression, in-save transfers, budgets and reports."""
import pytest
from fastapi.testclient import TestClient
import server
from test_api import auth, create, TOKEN

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB_PATH',tmp_path/'state.sqlite3')
    monkeypatch.setattr(server,'DEMO_MODE',False)
    monkeypatch.setattr(server,'BOT_TOKEN',TOKEN)
    with TestClient(server.app) as c:
        yield c


def club(client,league,name):
    rows=client.get('/api/world/clubs?league='+league,headers=auth()).json()['clubs']
    return next(x for x in rows if x['name']==name)


def make_coach(client,slot=1,uid=41):
    arsenal=club(client,'ENG_1','Arsenal')
    r=client.post(f'/api/careers/{slot}/create',headers=auth(uid),json={
        'role':'coach','name':'Тренер','place':'Лондон','club_id':arsenal['id']})
    assert r.status_code==200,r.text
    return arsenal


def play(client,slot,steps=12,uid=41):
    for _ in range(steps):
        current=client.get('/api/state',headers=auth(uid)).json()
        career=next(c for c in current['careers'] if c['slot']==slot)
        r=client.post(f'/api/careers/{slot}/decide',headers=auth(uid),json={
            'event_id':career['event']['id'],'choice_id':1,'expected_turn':career['turns']})
        assert r.status_code==200,r.text
    return r.json()


def test_catalog_and_fixtures_progress_do_not_repeat(client):
    state=client.get('/api/state',headers=auth()).json()
    assert state['world_catalog']['imported_clubs']==1453
    assert state['world_catalog']['imported_players']==1070
    assert len(client.get('/api/world/clubs?league=ESP_1',headers=auth()).json()['clubs'])==20
    assert len(client.get('/api/world/clubs?league=GER_1',headers=auth()).json()['clubs'])==18
    assert len(client.get('/api/world/clubs?league=ITA_1',headers=auth()).json()['clubs'])==20
    own=make_coach(client)
    initial=client.get(f'/api/careers/1/fixtures?league=ENG_1',headers=auth()).json()['fixtures']
    # Club-filtered fixture listing has home/away season for each team.
    assert len(initial)==38
    assert all(x['home_goals'] is None for x in initial)
    table=client.get('/api/careers/1/table?league=ENG_1',headers=auth()).json()['rows']
    assert sum(x['played'] for x in table)==0
    play(client,1,steps=1)
    first=client.get('/api/careers/1/fixtures?league=ENG_1',headers=auth()).json()['fixtures']
    assert 0<len([x for x in first if x['home_goals'] is not None])<38
    table=client.get('/api/careers/1/table?league=ENG_1',headers=auth()).json()['rows']
    assert sum(x['played'] for x in table)>0
    with server.connection() as conn:
        before=conn.execute('SELECT COUNT(*) FROM game_fixtures WHERE user_id=41 AND slot=1 AND home_goals IS NOT NULL').fetchone()[0]
        assert before>0
        # A repeated same decision is rejected BEFORE any more fixtures could be played.
        bad=client.post('/api/careers/1/decide',headers=auth(),json={
          'event_id':0,'choice_id':1,'expected_turn':0})
        assert bad.status_code==409
        after=conn.execute('SELECT COUNT(*) FROM game_fixtures WHERE user_id=41 AND slot=1 AND home_goals IS NOT NULL').fetchone()[0]
        assert before==after
    play(client,1,11)
    table=client.get('/api/careers/1/table?league=ENG_1',headers=auth()).json()['rows']
    assert all(x['played']==38 for x in table)
    report=client.post('/api/careers/1/season/finish',headers=auth()).json()['report']
    with server.connection() as conn:
        total=conn.execute('SELECT COUNT(*) FROM game_fixtures WHERE user_id=41 AND slot=1 AND season=1 AND home_goals IS NOT NULL').fetchone()[0]
    assert report['football']['matches_played']==total and total>10000
    assert report['football']['top_scorers']
    assert report['my_finance']['prize_eur']>0
    assert report['my_finance']['wages_eur']>0
    assert report['football']['own_club']['played']==38
    current=client.get('/api/careers/1/fixtures?league=ENG_1',headers=auth()).json()['fixtures']
    assert len(current)==38
    assert all(x['home_goals'] is not None for x in current)
    advance=client.post('/api/careers/1/season/advance',headers=auth())
    assert advance.status_code==200
    new=client.get('/api/careers/1/fixtures?league=ENG_1',headers=auth()).json()['fixtures']
    assert len(new)==38
    assert all(x['home_goals'] is None for x in new)
    assert all(x['played']==0 for x in client.get('/api/careers/1/table?league=ENG_1',headers=auth()).json()['rows'])


def test_transfer_moves_player_funds_and_changes_only_own_save(client):
    own=make_coach(client,1)
    assert create(client,2,role='coach').status_code==200
    roster=client.get('/api/careers/1/squad',headers=auth()).json()
    assert roster['club_id']==own['id']
    # Pick an affordable player from a different real club.
    market=client.get('/api/careers/1/market?search=Neuer',headers=auth()).json()
    assert market['players']
    target_player=market['players'][0]
    fee=((int(target_player['value_eur']*1.15)+99_999)//100_000)*100_000
    budget=next(c for c in market['clubs'] if c['id']==own['id'])
    assert fee<=budget['transfer_eur']
    assert client.post('/api/careers/1/transfer',headers=auth(),json={
        'player_id':target_player['player_id'],'target_club_id':own['id'],'offer_eur':100_000}).status_code==409
    bad=client.post('/api/careers/1/transfer',headers=auth(),json={
        'player_id':target_player['player_id'],'target_club_id':club(client,'ITA_1','Inter')['id'],'offer_eur':fee})
    assert bad.status_code==403
    r=client.post('/api/careers/1/transfer',headers=auth(),json={
        'player_id':target_player['player_id'],'target_club_id':own['id'],'offer_eur':fee})
    assert r.status_code==200,r.text
    assert r.json()['deal']['fee_eur']==fee
    assert r.json()['state']['world_catalog']['imported_players']==1070
    assert 'first_deal' in r.json()['new_awards']
    new_roster=client.get('/api/careers/1/squad',headers=auth()).json()
    assert target_player['player_id'] in [p['player_id'] for p in new_roster['players']]
    new_budget=next(c for c in client.get('/api/careers/1/market',headers=auth()).json()['clubs'] if c['id']==own['id'])
    assert new_budget['transfer_eur']==budget['transfer_eur']-fee
    # Static catalog still has real Bayern roster, and slot 2 never receives the transfer.
    original=client.get('/api/world/clubs/'+target_player['club_id'],headers=auth()).json()
    assert any(p['name']==target_player['name'] for p in original['players'])
    with server.connection() as conn:
        location=conn.execute('SELECT club_id FROM world_players WHERE user_id=41 AND slot=2 AND player_id=?',
                              (target_player['player_id'],)).fetchone()[0]
        assert location==target_player['club_id']
    assert client.post('/api/careers/1/transfer',headers=auth(),json={
        'player_id':target_player['player_id'],'target_club_id':own['id'],'offer_eur':fee}).status_code==409


def test_agent_commission_and_player_character_starts_matches(client):
    r=client.post('/api/careers/1/create',headers=auth(),json={
        'role':'agent','name':'Иван Агент','place':'VELTON Agency'})
    assert r.status_code==200
    market=client.get('/api/careers/1/market?search=Neuer',headers=auth()).json()
    player=market['players'][0]
    buyer=club(client,'ENG_1','Arsenal')
    fee=((int(player['value_eur']*1.15)+99999)//100000)*100000
    deal=client.post('/api/careers/1/transfer',headers=auth(),json={
        'player_id':player['player_id'],'target_club_id':buyer['id'],'offer_eur':fee})
    assert deal.status_code==200,deal.text
    assert deal.json()['deal']['commission_eur']==fee//20
    agent=deal.json()['state']['careers'][0]
    assert agent['metrics']['deals']==1
    r=client.post('/api/careers/2/create',headers=auth(),json={
        'role':'player','name':'Алексей Миронов','place':'Лондон','club_id':buyer['id']})
    assert r.status_code==200
    play(client,2,steps=12)
    squad=client.get('/api/careers/2/squad',headers=auth()).json()['players']
    mine=next(p for p in squad if p['name']=='Алексей Миронов')
    assert mine['appearances']>0  # player's career participates, not only scripted story events.


def test_archive_is_readable_after_advancing_and_fixtures_are_season_scoped(client):
    own=make_coach(client)
    play(client,1,12)
    report=client.post('/api/careers/1/season/finish',headers=auth())
    assert report.status_code==200,report.text
    archival=client.get('/api/careers/1/archive',headers=auth()).json()['seasons']
    assert len(archival)==1 and archival[0]['season']==1
    with server.connection() as conn:
        expected=conn.execute('SELECT COUNT(*) FROM game_fixtures WHERE user_id=41 AND slot=1 AND season=1').fetchone()[0]
    assert archival[0]['matches']==expected and expected>10000
    r=client.post('/api/careers/1/season/advance',headers=auth())
    assert r.status_code==200
    previous=client.get('/api/careers/1/archive/1',headers=auth()).json()['report']
    assert previous['football']['matches_played']==expected
    old=client.get('/api/careers/1/fixtures?season=1',headers=auth()).json()['fixtures']
    current=client.get('/api/careers/1/fixtures?season=2',headers=auth()).json()['fixtures']
    assert len(old)==len(current)==38
    assert all(f['home_goals'] is not None for f in old)
    assert all(f['home_goals'] is None for f in current)
    assert client.get('/api/careers/1/archive/100',headers=auth()).status_code==404
    assert client.get('/api/careers/1/fixtures?season=99',headers=auth()).status_code==422


def test_owner_role_can_control_real_club_and_tactic(client):
    own=club(client,'ESP_1','FC Barcelona')
    r=client.post('/api/careers/5/create',headers=auth(),json={
        'role':'club','name':'Мой клуб','place':'Барселона','club_id':own['id']})
    assert r.status_code==200,r.text
    career=r.json()['state']['careers'][0]
    assert career['my_club']['name']=='FC Barcelona'
    assert career['my_club']['players']>=26
    r=client.post('/api/careers/5/tactic',headers=auth(),json={'tactic':'defend'})
    assert r.status_code==200,r.text
    assert r.json()['state']['careers'][0]['my_club']['tactic']=='defend'
    assert client.post('/api/careers/5/tactic',headers=auth(),json={'tactic':'cheat'}).status_code==422


def test_generated_footballer_starts_even_at_star_club(client):
    madrid=club(client,'ESP_1','Real Madrid')
    assert client.post('/api/careers/5/create',headers=auth(),json={
        'role':'player','name':'Илья Новиков','place':'Мадрид','club_id':madrid['id']}).status_code==200
    first=play(client,5,steps=1)['state']['careers'][0]
    assert first['my_club']['name']=='Real Madrid'
    assert first['metrics']['appearances']>0
    squad=client.get('/api/careers/5/squad',headers=auth()).json()['players']
    user=next(p for p in squad if p['name']=='Илья Новиков')
    assert user['appearances']>0
