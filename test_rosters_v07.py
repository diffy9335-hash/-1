"""Regression for VELTON v0.7 curated real-player pack and local snapshot importer."""
import csv
import json
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import server
from engine import goal_scoring_weight
from offline_catalog import parse_pack
from test_api import TOKEN, auth
from tools.convert_roster_snapshot import convert, age_as_of, lookup_club, catalog

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB_PATH',tmp_path/'veltonv07.sqlite3')
    monkeypatch.setattr(server,'BOT_TOKEN',TOKEN)
    monkeypatch.setattr(server,'DEMO_MODE',False)
    with TestClient(server.app) as c:yield c

def test_97_added_player_entries_are_real_verified_and_licensed(client):
    world=client.get('/api/state',headers=auth()).json()['world_catalog']
    assert world['countries']==35
    assert world['leagues']==80
    assert world['imported_clubs']==1453
    assert world['imported_players']==1070
    assert client.get('/api/config').json()['version']=='0.9'
    with server.connection() as c:
        for league,club,player in [
            ('ENG_1','Brentford','Igor Thiago'),
            ('ESP_1','CA Osasuna','Ante Budimir'),
            ('GER_1','FC Augsburg','Michael Gregoritsch'),
            ('ITA_1','Napoli','Kevin De Bruyne'),
            ('FRA_1','Olympique Lyonnais','Nicolas Tagliafico'),
        ]:
            row=c.execute('''SELECT pc.id,pc.position,pc.source FROM player_catalog pc
                      JOIN club_catalog cc ON cc.id=pc.club_id
                      WHERE cc.league_id=? AND cc.name=? AND pc.name=?''',
                      (league,club,player)).fetchone()
            assert row is not None,(league,club,player)
            assert 'fifa-wc2026-players' in row['source'] or 'verified first-team 2026/27' in row['source']
            assert row['position'] in ('GK','DF','MF','FW')
    result=client.get('/api/world/leagues',headers=auth()).json()['leagues']
    assert sum(x['named_players'] for x in result)==1009

def test_score_weight_respects_real_snapshot_positions():
    assert goal_scoring_weight('GK')<goal_scoring_weight('DF')
    assert goal_scoring_weight('DF')<goal_scoring_weight('MF')
    assert goal_scoring_weight('MF')<goal_scoring_weight('FW')
    assert goal_scoring_weight('ATT')==goal_scoring_weight('FW')
    assert goal_scoring_weight('')>0

def test_local_tsv_import_no_network_and_no_duplicate_snapshot(tmp_path):
    # Deliberately fictional input names only in isolated test fixture; not shipped in catalog.
    source=tmp_path/'local_fixture.tsv'
    with source.open('w',encoding='utf-8',newline='') as out:
        w=csv.DictWriter(out,fieldnames=['PLAYER NAME','FIRST NAME(S)','LAST NAME(S)','POS','DOB','CLUB'],delimiter='\t')
        w.writeheader()
        w.writerow({'PLAYER NAME':'EXAMPLE Newplayer','FIRST NAME(S)':'Newplayer','LAST NAME(S)':'Example',
            'POS':'MF','DOB':'15/01/2003','CLUB':'Valencia CF (ESP)'})
        w.writerow({'PLAYER NAME':'EXAMPLE Newplayer','FIRST NAME(S)':'Newplayer','LAST NAME(S)':'Example',
            'POS':'MF','DOB':'15/01/2003','CLUB':'Valencia CF (ESP)'})
        w.writerow({'PLAYER NAME':'EXAMPLE Unmatched','FIRST NAME(S)':'Unmatched','LAST NAME(S)':'Example',
            'POS':'DF','DOB':'15/01/2003','CLUB':'Absolutely Not A Football Club (ESP)'})
    target=tmp_path/'out.json'
    stats=convert(source,'fifa26','https://example.com/fixture.tsv',target)
    assert stats['new_players']==1
    assert stats['matched_clubs']==1
    assert stats['unmatched_source_club_counts']
    clubs=parse_pack(target)
    assert len(clubs)==1 and len(clubs[0][-1])==1
    assert clubs[0][-1][0][2]=='Newplayer Example'
    assert clubs[0][-1][0][4]==23
    assert target.with_suffix('.audit.json').exists()

def test_beyondelo_snapshot_resolves_english_club_only(tmp_path):
    source=tmp_path/'ranking.csv'
    with source.open('w',encoding='utf-8',newline='') as out:
        w=csv.DictWriter(out,fieldnames=['rank','slug','name','country_code','club','position','elo','as_of'])
        w.writeheader()
        w.writerow({'rank':1,'slug':'fake-alpha','name':'Sample Sampleman','country_code':'ESP',
                    'club':'Brentford','position':'CF','elo':2000,'as_of':'2026-11-01'})
    target=tmp_path/'ranking_pack.json'
    stats=convert(source,'beyondelo','https://example.com/rankings.csv',target)
    assert stats['new_players']==1
    assert parse_pack(target)[0][1]=='ENG_1'

def test_pack_is_idempotent_and_old_save_not_mutated(client):
    teams=client.get('/api/world/clubs',params={'league':'ENG_1'},headers=auth()).json()['clubs']
    club=next(x for x in teams if x['name']=='Brentford')
    p=client.post('/api/careers/1/create',headers=auth(),json={
        'role':'coach','name':'Coach Demo','place':'Brentford','club_id':club['id']})
    assert p.status_code==200
    with server.connection() as c:
        n=c.execute('SELECT count(*) FROM world_players WHERE user_id=? AND slot=?',(41,1)).fetchone()[0]
        real=c.execute('''SELECT count(*) FROM world_players wp JOIN player_catalog pc on pc.id=wp.player_id
              WHERE wp.user_id=41 AND wp.slot=1 AND pc.name='Igor Thiago' ''').fetchone()[0]
        assert n==1009 and real==1
        from offline_catalog import apply_pack
        pack=Path(__file__).resolve().parents[1]/'world_data/packs/velton_verified_players_v07.json'
        info=apply_pack(c,pack)
        assert info['added_players']==0 and info['added_clubs']==0
        later=c.execute('SELECT count(*) FROM world_players WHERE user_id=41 AND slot=1').fetchone()[0]
        assert n==later
