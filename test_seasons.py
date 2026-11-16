import json
import pytest
from fastapi.testclient import TestClient
import server
from test_api import auth, create, TOKEN

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB_PATH',tmp_path/'velton.sqlite3')
    monkeypatch.setattr(server,'DEMO_MODE',False)
    monkeypatch.setattr(server,'BOT_TOKEN',TOKEN)
    with TestClient(server.app) as c:yield c

def play_12(client,slot,uid=41):
    for i in range(12):
        state=client.get('/api/state',headers=auth(uid)).json()
        career=next(c for c in state['careers'] if c['slot']==slot)
        result=client.post(f'/api/careers/{slot}/decide',headers=auth(uid),json={
            'event_id':career['event']['id'],'choice_id':i%3,'expected_turn':career['turns']})
        assert result.status_code==200, result.text
    return result.json()

def test_registry_and_verified_clubs_players_budgets(client):
    state=client.get('/api/state',headers=auth()).json()
    assert all(state['world_catalog'][k]==v for k,v in {'countries':35,'leagues':80,'target_clubs':1504,'imported_clubs':1453,'imported_players':1070}.items())
    assert state['world_catalog']['source']=='offline_static_catalog'
    leagues=client.get('/api/world/leagues',headers=auth()).json()['leagues']
    assert len(leagues)==80
    epl=next(x for x in leagues if x['id']=='ENG_1')
    assert epl['imported']==20
    cl=client.get('/api/world/clubs?league=ENG_1',headers=auth()).json()['clubs']
    assert len(cl)==20
    arsenal=next(x for x in cl if x['name']=='Arsenal')
    assert arsenal['players']>10
    assert arsenal['base_budget_eur']>0
    assert 0<arsenal['base_transfer_eur']<arsenal['base_budget_eur']
    assert client.get('/api/world/clubs?league=not_a_league',headers=auth()).status_code==404

def test_close_report_reset_promotion_relegation_and_retire(client):
    assert create(client,1).status_code==200
    assert client.post('/api/careers/1/season/finish',headers=auth()).status_code==409
    first=client.get('/api/careers/1/table?league=ENG_1',headers=auth()).json()
    assert len(first['rows'])==20
    assert all(r['points']==r['played']==0 for r in first['rows'])
    assert len(client.get('/api/careers/1/table?league=ENG_2',headers=auth()).json()['rows'])==24
    progress=play_12(client,1)
    c=progress['state']['careers'][0]
    assert c['phase']=='ready' and c['season']==1
    assert c['event'] is None
    assert client.post('/api/careers/1/decide',headers=auth(),json={'event_id':0,'choice_id':0,'expected_turn':12}).status_code==409
    finish=client.post('/api/careers/1/season/finish',headers=auth())
    assert finish.status_code==200,finish.text
    data=finish.json()
    report=data['report']
    assert report['decisions']==12
    assert report['successful']+report['failed']==12
    assert report['simulated_leagues']==80
    assert len(report['league_summaries'])==80
    promotions=[m for m in report['movements'] if m['type']=='promotion']
    relegations=[m for m in report['movements'] if m['type']=='relegation']
    assert len(promotions)>=3 and len(promotions)==len(relegations)
    assert len([m for m in promotions if m['to']=='ENG_1'])==3
    assert len([m for m in relegations if m['to']=='ENG_2'])==3
    assert data['state']['careers'][0]['phase']=='review'
    assert any(m['via']=='playoff' for m in report['movements'] if m['type']=='promotion')
    assert data['state']['profile']['seasons_completed']==1
    assert any(a['id']=='first_season' and a['unlocked'] for a in data['state']['achievements'])
    assert client.post('/api/careers/1/season/finish',headers=auth()).status_code==409
    previous=client.get('/api/careers/1/table?league=ENG_1',headers=auth()).json()['rows']
    assert len(previous)==20 and all(x['played']==38 for x in previous)
    assert sum(x['points'] for x in previous)>0
    promoted={m['club_id'] for m in report['movements'] if m['type']=='promotion' and m['to']=='ENG_1'}
    advance=client.post('/api/careers/1/season/advance',headers=auth())
    assert advance.status_code==200,advance.text
    career=advance.json()['state']['careers'][0]
    assert (career['season'],career['week'],career['phase'])==(2,1,'playing')
    new_table=client.get('/api/careers/1/table?league=ENG_1',headers=auth()).json()['rows']
    assert len(new_table)==20
    assert all(x['points']==0 and x['played']==0 and x['gf']==0 and x['ga']==0 for x in new_table)
    assert promoted <= {x['club_id'] for x in new_table}
    assert client.post('/api/careers/1/season/advance',headers=auth()).status_code==409
    # Historic season is immutable even after league membership changes.
    with server.connection() as conn:
        archived=conn.execute("SELECT COUNT(*) n,SUM(played) gp FROM standings WHERE user_id=41 AND slot=1 AND season=1 AND league_id='ENG_1'").fetchone()
        assert archived['n']==20 and archived['gp']==20*38
    play_12(client,1)
    client.post('/api/careers/1/season/finish',headers=auth())
    assert client.post('/api/careers/1/season/retire',headers=auth(),json={'confirmation':'no'}).status_code==422
    retirement=client.post('/api/careers/1/season/retire',headers=auth(),json={'confirmation':'DELETE'})
    assert retirement.status_code==200
    assert retirement.json()['state']['careers']==[]
    assert retirement.json()['state']['profile']['decisions']==24
    with server.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM standings WHERE user_id=41 AND slot=1').fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM world_clubs WHERE user_id=41 AND slot=1').fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM season_reports WHERE user_id=41 AND slot=1').fetchone()[0]==0

def test_two_slots_have_independent_worlds(client):
    assert create(client,1).status_code==200
    assert create(client,2,role='coach').status_code==200
    play_12(client,1)
    client.post('/api/careers/1/season/finish',headers=auth())
    one=client.get('/api/careers/1/table?league=ENG_1',headers=auth()).json()['rows']
    two=client.get('/api/careers/2/table?league=ENG_1',headers=auth()).json()['rows']
    assert max(x['points'] for x in one)>0
    assert all(x['points']==0 for x in two)
    assert client.post('/api/careers/1/season/retire',headers=auth(),json={'confirmation':'DELETE'}).status_code==200
    assert len(client.get('/api/careers/2/table?league=ENG_1',headers=auth()).json()['rows'])==20

def test_real_club_selection_links_budget_and_roster(client):
    clubs=client.get('/api/world/clubs?league=ENG_1',headers=auth()).json()['clubs']
    arsenal=next(x for x in clubs if x['name']=='Arsenal')
    selection=client.post('/api/careers/4/create',headers=auth(),json={
        'role':'coach','name':'Фёдор Петров','place':'Неверное имя клуба','club_id':arsenal['id']})
    assert selection.status_code==200,selection.text
    career=next(x for x in selection.json()['state']['careers'] if x['slot']==4)
    assert career['place']=='Arsenal' and career['club_id']==arsenal['id']
    assert career['my_club']['name']=='Arsenal'
    assert career['my_club']['budget_eur']>0
    detail=client.get('/api/world/clubs/'+arsenal['id'],headers=auth()).json()
    assert detail['club']['name']=='Arsenal'
    assert len(detail['players'])>=10
    assert any(x['name']=='Bukayo Saka' for x in detail['players'])
    assert client.post('/api/careers/5/create',headers=auth(),json={
        'role':'player','name':'Алексей Миронов','place':'Проверка','club_id':'invalid'}).status_code==422
    assert client.post('/api/careers/5/create',headers=auth(),json={
        'role':'referee','name':'Алексей Миронов','place':'Проверка','club_id':arsenal['id']}).status_code==422
