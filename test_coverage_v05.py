"""Coverage verification for real-name, snapshot-only offline VELTON v0.5."""
import json
from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server
from test_api import TOKEN, auth
from tools.build_coverage_pack import canonical

ROOT=Path(__file__).resolve().parents[1]
PACK_DIR=ROOT/'world_data'/'packs'

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server,'DB_PATH',tmp_path/'velton.sqlite3')
    monkeypatch.setattr(server,'BOT_TOKEN',TOKEN)
    monkeypatch.setattr(server,'DEMO_MODE',False)
    with TestClient(server.app) as c:
        yield c


def test_35_associations_and_80_leagues_with_1453_real_clubs(client):
    info=client.get('/api/state',headers=auth()).json()['world_catalog']
    assert info['countries']==35 and info['leagues']==80
    assert info['imported_clubs']==1453
    assert info['imported_leagues']==80
    assert info['countries_with_clubs']==35
    assert info['full_leagues']==59  # by intended number of clubs, not full player rosters
    assert info['imported_players']==1070
    assert info['clubs_with_players']>=60
    assert info['source']=='offline_static_catalog'
    details=client.get('/api/world/leagues',headers=auth()).json()['leagues']
    assert len(details)==80
    assert len([x for x in details if x['status']=='empty'])==0
    assert len([x for x in details if x['status']=='partial'])==21
    assert len([x for x in details if x['status']=='complete'])==59
    for key,num in [('URU_1',16),('CHI_1',16),('KOR_1',12),('SRB_1',14),('URU_2',14),('KOR_2',17),('CHI_2',16),('RUS_2',17)]:
        item=next(r for r in details if r['id']==key)
        assert item['imported']==num
        assert item['source_season'] in ('2026','2026-27')


def test_real_club_sources_budgets_and_no_invented_rosters(client):
    for league,club in [('URU_1','Peñarol'),('CHI_1','Colo Colo'),('KOR_1','FC Seoul'),('SRB_1','Crvena Zvezda')]:
        clubs=client.get('/api/world/clubs',headers=auth(),params={'league':league}).json()['clubs']
        target=next(c for c in clubs if c['name']==club)
        assert target['base_budget_eur']>target['base_transfer_eur']>0
        r=client.get('/api/world/clubs/'+target['id'],headers=auth()).json()
        assert r['club']['name']==club
        assert r['club']['source'].startswith('OpenFootball CC0')
    korea=client.get('/api/world/clubs',headers=auth(),params={'league':'KOR_1'}).json()['clubs']
    assert all(c['players']==0 for c in korea)  # no fictional names to fill blank squads
    real=client.get('/api/world/clubs',headers=auth(),params={'league':'KSA_1'}).json()['clubs']
    nassr=next(c for c in real if c['name']=='Al Nassr')
    names=[x['name'] for x in client.get('/api/world/clubs/'+nassr['id'],headers=auth()).json()['players']]
    assert 'Cristiano Ronaldo' in names


def test_all_names_have_provenance_and_no_cross_division_duplicates():
    packs=[json.loads(p.read_text('utf-8')) for p in sorted(PACK_DIR.glob('*.json'))]
    assert len(packs)>=3
    known=set()
    players=set()
    for pack in packs:
        assert pack['format']=='velton-offline-1'
        for team in pack['clubs']:
            assert team['source'].strip() and team['name'].strip()
            key=(team['league_id'][:3],canonical(team['name']))
            # World Cup player packs update clubs from other packs, as intended.
            if not team['players']:
                assert key not in known, key
                known.add(key)
            for player in team['players']:
                assert player['source'].strip() and player['name'].strip()
                assert player['id'] not in players
                players.add(player['id'])
    assert len(players)==761
    audit=json.loads((ROOT/'world_data/coverage_manifest.json').read_text('utf-8'))
    assert audit['league_source_count']==50
    assert audit['new_clubs']==826
    assert any(x['season']=='2024-25' for x in audit['sources'].values())
    assert audit['sources']['KOR_1']['season']=='2026'


def test_new_league_has_match_calendar_in_a_career(client):
    league=client.get('/api/world/clubs',headers=auth(),params={'league':'KOR_1'}).json()['clubs']
    seoul=next(t for t in league if t['name']=='FC Seoul')
    resp=client.post('/api/careers/1/create',headers=auth(),json={
      'role':'coach','name':'Тренер VELTON','place':'Сеул','club_id':seoul['id']})
    assert resp.status_code==200,resp.text
    table=client.get('/api/careers/1/table',headers=auth(),params={'league':'KOR_1'}).json()['rows']
    assert len(table)==12 and all(x['played']==0 for x in table)
    calendar=client.get('/api/careers/1/fixtures',headers=auth(),params={'league':'KOR_1'}).json()['fixtures']
    assert len(calendar)==22  # double round robin: 12 teams, home + away
    assert all(x['home_goals'] is None for x in calendar)
    assert client.get('/api/careers/1/squad',headers=auth()).json()['players']==[]
    # Real club exists; unknown players are not invented to make a squad.
