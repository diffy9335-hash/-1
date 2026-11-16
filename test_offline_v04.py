"""Offline-only source, independent save worlds, AI transitions and pack validation."""
import json
import pytest
from fastapi.testclient import TestClient
from test_api import TOKEN, auth
from offline_catalog import apply_pack, parse_pack, PackError
import server

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB_PATH',tmp_path/'v04.sqlite3')
    monkeypatch.setattr(server,'DEMO_MODE',False)
    monkeypatch.setattr(server,'BOT_TOKEN',TOKEN)
    with TestClient(server.app) as c:yield c

def create_coach(client, slot):
    arsenal=next(x for x in client.get('/api/world/clubs?league=ENG_1',headers=auth()).json()['clubs'] if x['name']=='Arsenal')
    r=client.post(f'/api/careers/{slot}/create',headers=auth(),json={
       'role':'coach','name':f'Коуч {slot}','place':'Лондон','club_id':arsenal['id']})
    assert r.status_code==200,r.text
    return arsenal['id']

def test_offline_snapshot_and_pack_updates_only_new_saves(client,tmp_path):
    assert client.get('/api/config').json()['version']=='0.9'
    create_coach(client,1)
    with server.connection() as c:
        old_clubs=c.execute('SELECT COUNT(*) FROM world_clubs WHERE user_id=41 AND slot=1').fetchone()[0]
        old_players=c.execute('SELECT COUNT(*) FROM world_players WHERE user_id=41 AND slot=1').fetchone()[0]
    pack={'format':'velton-offline-1','clubs':[
      {'league_id':'ENG_1','name':'Arsenal','source':'test sourced data','players':[{'name':'A Future Verified Player'}]},
      {'league_id':'ENG_3','name':'Test Sample FC','source':'test source','players':[]}
    ]}
    path=tmp_path/'extra.json';path.write_text(json.dumps(pack),encoding='utf-8')
    with server.connection() as c:
        stats=apply_pack(c,path)
        assert stats['added_clubs']==1
        assert stats['added_players']==1
        assert apply_pack(c,path)['added_clubs']==0
        assert apply_pack(c,path)['added_players']==0
    create_coach(client,2)
    with server.connection() as c:
        assert c.execute('SELECT COUNT(*) FROM world_clubs WHERE user_id=41 AND slot=1').fetchone()[0]==old_clubs
        assert c.execute('SELECT COUNT(*) FROM world_players WHERE user_id=41 AND slot=1').fetchone()[0]==old_players
        assert c.execute('SELECT COUNT(*) FROM world_clubs WHERE user_id=41 AND slot=2').fetchone()[0]==old_clubs+1
        # New Arsenal names not in official squad are intentionally excluded from new saves.
        assert c.execute('SELECT COUNT(*) FROM world_players WHERE user_id=41 AND slot=2').fetchone()[0]==old_players
        assert c.execute("SELECT COUNT(*) FROM world_players wp JOIN player_catalog pc ON pc.id=wp.player_id WHERE wp.user_id=41 AND wp.slot=2 AND pc.name='A Future Verified Player'").fetchone()[0]==0

def test_offline_pack_rejects_unsourced_and_duplicates(tmp_path):
    source=tmp_path/'bad.json'
    source.write_text(json.dumps({'format':'velton-offline-1','clubs':[{'league_id':'ENG_1','name':'Club Without Source','players':[]}]}))
    with pytest.raises(PackError):parse_pack(source)
    source.write_text(json.dumps({'format':'velton-offline-1','clubs':[{'league_id':'ENG_1','name':'Duplicated','source':'A','players':[]},{'league_id':'ENG_1','name':'Duplicated','source':'B','players':[]}]}))
    with pytest.raises(PackError):parse_pack(source)

def test_ai_offseason_transfer_and_replay_protection(client):
    own=create_coach(client,1)
    create_coach(client,2)
    for _ in range(12):
        c=next(x for x in client.get('/api/state',headers=auth()).json()['careers'] if x['slot']==1)
        resp=client.post('/api/careers/1/decide',headers=auth(),json={'event_id':c['event']['id'],'choice_id':1,'expected_turn':c['turns']})
        assert resp.status_code==200,resp.text
    done=client.post('/api/careers/1/season/finish',headers=auth())
    assert done.status_code==200,done.text
    before=client.get('/api/careers/1/table?league=ENG_1',headers=auth()).json()['rows']
    assert sum(x['played'] for x in before)>0
    advance=client.post('/api/careers/1/season/advance',headers=auth())
    assert advance.status_code==200,advance.text
    moves=advance.json()['offseason']
    with server.connection() as conn:
        saved=conn.execute("SELECT COUNT(*) FROM game_transfers WHERE user_id=41 AND slot=1 AND season=2 AND kind='ai'").fetchone()[0]
        assert saved==len(moves)
        assert all(x['from']!=own and x['to']!=own for x in moves)
        # No transfer in slot 2; no carryover of another world's finance/rosters.
        assert conn.execute('SELECT COUNT(*) FROM game_transfers WHERE user_id=41 AND slot=2').fetchone()[0]==0
    assert client.post('/api/careers/1/season/advance',headers=auth()).status_code==409
    table=client.get('/api/careers/1/table?league=ENG_1',headers=auth()).json()['rows']
    assert all(x['played']==0 and x['points']==0 for x in table)
    assert client.get('/api/careers/1/archive/1',headers=auth()).status_code==200
