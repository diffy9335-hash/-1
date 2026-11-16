"""Tests for intentionally offline full-roster pipeline and honest coverage audit."""
from __future__ import annotations
import csv
import json
import sqlite3
from pathlib import Path
import pytest
from tools.install_real_rosters_v09 import (make_pack, plain_club, years_old,
    fetch_static_file, determine_club, club_lookup, baseline_catalog)
from tools.audit_squads_v09 import audit
from offline_catalog import parse_pack, seed_local_catalog
from verified_rosters import update_verified_catalog
from world import init_world_db


def fixture_sources(tmp_path, count=25):
    clubs=tmp_path/'clubs.csv'
    players=tmp_path/'players.csv'
    with clubs.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['club_id','name','domestic_competition_id']);w.writeheader()
        w.writerows([
            {'club_id':'123','name':'Atalanta','domestic_competition_id':'IT1'},
            {'club_id':'124','name':'Arsenal','domestic_competition_id':'GB1'},
            {'club_id':'125','name':'Not Real FC','domestic_competition_id':'IT1'},
        ])
    fields=['player_id','name','current_club_id','position','last_season','date_of_birth','country_of_citizenship']
    rows=[{'player_id':str(i+1),'name':f'Test Athlete {i} Realname',
           'current_club_id':'123','position':('Defender','Midfield','Attack','Goalkeeper')[i%4],
           'last_season':'2025','date_of_birth':'1998-06-16','country_of_citizenship':'Italy'} for i in range(count)]
    rows += [{'player_id':'991','name':'Verified Arsenal Factual','current_club_id':'124',
              'position':'Attack','last_season':'2025','date_of_birth':'2002-10-12'},
             {'player_id':'992','name':'Unmapped Existing','current_club_id':'125',
              'position':'Attack','last_season':'2025','date_of_birth':'2002-10-12'},
             {'player_id':'993','name':'Old Player','current_club_id':'123',
              'position':'Attack','last_season':'2022','date_of_birth':'2002-10-12'}]
    with players.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    return players,clubs


def test_match_only_explicit_known_clubs():
    clubs,_,_=baseline_catalog()
    ix,cid=club_lookup(clubs)
    assert determine_club({'club_id':'1','name':'Atalanta','domestic_competition_id':'IT1'},ix,cid,{})[0] == 'verified:ITA_1:00'
    assert determine_club({'club_id':'1','name':'Arsenal','domestic_competition_id':'AR1'},ix,cid,{})[0] is None
    assert determine_club({'club_id':'1','name':'Not Real Club','domestic_competition_id':'GB1'},ix,cid,{})[0] is None
    assert plain_club('AS Roma') == 'roma'


def test_bulk_25_real_names_import_no_fakes(tmp_path):
    players,clubs=fixture_sources(tmp_path)
    pack,audit_data=make_pack(players,clubs,limit_per_club=30)
    assert len(pack['clubs']) == 1
    assert pack['clubs'][0]['name']=='Atalanta'
    assert len(pack['clubs'][0]['players'])==25
    assert audit_data['clubs_20_plus']==1
    assert audit_data['exclusions']['more_recent_official_roster']==1
    assert audit_data['exclusions']['not_in_2025_26']==1
    assert audit_data['exclusions']['unmatched_club']==1
    f=tmp_path/'result.json';f.write_text(json.dumps(pack))
    parsed=parse_pack(f)
    assert len(parsed)==1
    assert parsed[0][-1][0][3] in {'DF','GK','MF','FW'}
    # Inject into a freshly built in-memory offline catalogue.
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    init_world_db(c);seed_local_catalog(c);update_verified_catalog(c)
    before=c.execute('SELECT COUNT(*) FROM player_catalog').fetchone()[0]
    from offline_catalog import apply_pack
    stats=apply_pack(c,f)
    assert stats['added_players']==25 and stats['added_clubs']==0
    assert c.execute('SELECT COUNT(*) FROM player_catalog').fetchone()[0]==before+25
    assert apply_pack(c,f)['added_players']==0
    c.close()


def test_bulk_caps_roster_and_prevents_id_collision(tmp_path):
    players,clubs=fixture_sources(tmp_path, count=40)
    pack,audit_data=make_pack(players,clubs,limit_per_club=30)
    assert len(pack['clubs'][0]['players'])==30
    assert audit_data['exclusions']['exceeds_roster_cap']==10
    assert len({p['id'] for p in pack['clubs'][0]['players']})==30


def test_age_and_no_implicit_download(monkeypatch,tmp_path):
    assert years_old('2000-10-21')==25
    assert years_old('bad date') is None
    def fail_network(*a,**kw):
        raise AssertionError('No internet connection should be needed for local pack creation')
    monkeypatch.setattr('urllib.request.urlopen',fail_network)
    players,clubs=fixture_sources(tmp_path)
    pack,_=make_pack(players,clubs)
    assert pack['clubs']


def test_audit_truthful_zero_players():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    init_world_db(c);seed_local_catalog(c);update_verified_catalog(c)
    rows,s=audit(c)
    assert s['clubs']==1453 and s['leagues']==80
    assert s['players_available_in_new_saves']==1009
    assert s['clubs_empty']>1000
    assert s['confirmed_official_2026_27_clubs']==29
    c.close()


def test_old_slot_preserved_and_new_slot_receives_imported_real_names(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    import server
    from offline_catalog import apply_pack
    from test_api import TOKEN, auth
    monkeypatch.setattr(server,'DB_PATH',tmp_path/'v09.sqlite3')
    monkeypatch.setattr(server,'BOT_TOKEN',TOKEN)
    monkeypatch.setattr(server,'DEMO_MODE',False)
    players,clubs=fixture_sources(tmp_path,count=25)
    pack,_=make_pack(players,clubs)
    path=tmp_path/'safe_snapshot.json';path.write_text(json.dumps(pack),encoding='utf-8')
    # Test fixtures mimic a properly reviewed static source. No external network needed.
    with TestClient(server.app) as client:
        club_id='verified:ITA_1:00'
        old=client.post('/api/careers/1/create',headers=auth(),json={
            'role':'coach','name':'Legacy Coach','place':'Bergamo','club_id':club_id})
        assert old.status_code==200,old.text
        with server.connection() as conn:
            prev=conn.execute('SELECT COUNT(*) FROM world_players WHERE user_id=41 AND slot=1').fetchone()[0]
            assert apply_pack(conn,path)['added_players']==25
        new=client.post('/api/careers/2/create',headers=auth(),json={
            'role':'coach','name':'New Coach','place':'Bergamo','club_id':club_id})
        assert new.status_code==200,new.text
        with server.connection() as conn:
            old_now=conn.execute('SELECT COUNT(*) FROM world_players WHERE user_id=41 AND slot=1').fetchone()[0]
            new_now=conn.execute('SELECT COUNT(*) FROM world_players WHERE user_id=41 AND slot=2').fetchone()[0]
            assert old_now==prev
            assert new_now==prev+25
            names=[r[0] for r in conn.execute('SELECT pc.name FROM world_players w JOIN player_catalog pc ON pc.id=w.player_id WHERE w.user_id=41 AND w.slot=2 AND w.club_id=?',(club_id,))]
            assert 'Test Athlete 0 Realname' in names
            assert 'Test Athlete 24 Realname' in names
        detail=client.get('/api/world/clubs/'+club_id,headers=auth())
        assert detail.status_code==200
        assert detail.json()['roster_basis']=='historical_2026_07'
        assert detail.json()['historical_bulk_players']==25
