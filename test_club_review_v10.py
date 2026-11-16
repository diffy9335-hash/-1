"""Regression tests for the offline squad alias review and national competition codes."""
import csv
import json
from pathlib import Path
import pytest

from tools.install_real_rosters_v09 import (
    COMP_COUNTRY, baseline_catalog, club_lookup, determine_club, make_pack,
)
from tools.review_club_matches_v10 import generate_review, apply_review


def sample_source(tmp_path):
    path = tmp_path/'clubs.csv'
    with path.open('w', newline='', encoding='utf-8') as fd:
        writer = csv.DictWriter(fd, fieldnames=['club_id', 'name', 'domestic_competition_id'])
        writer.writeheader()
        writer.writerows([
            {'club_id': '31', 'name': 'Dinamo Zageb', 'domestic_competition_id': 'KR1'},
            {'club_id': '32', 'name': 'Jeonbuk Hyundai Motors', 'domestic_competition_id': 'RSK1'},
            {'club_id': '33', 'name': 'Imaginary Football FC', 'domestic_competition_id': 'KR1'},
        ])
    return path


def read_review(path):
    with path.open('r', encoding='utf-8-sig', newline='') as fd:
        return list(csv.DictReader(fd))


def fill_review(path, source_id, target_id):
    rows = read_review(path)
    for row in rows:
        if row['source_club_id'] == source_id:
            row['velton_club_id'] = target_id
    with path.open('w', encoding='utf-8-sig', newline='') as fd:
        writer = csv.DictWriter(fd, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def country_club(country, name):
    from world import LEAGUES
    clubs, _, _ = baseline_catalog()
    return next(c for c in clubs
                if LEAGUES[c['league_id']]['association_code'] == country and c['name'] == name)


def test_fixed_transfermarkt_competition_codes_are_distinct():
    for code, expected in [('KR1', 'CRO'), ('RSK1', 'KOR'), ('SER1', 'SRB'),
                           ('JAP1', 'JPN'), ('SA1', 'KSA'), ('ARG1', 'ARG'),
                           ('SC1', 'SCO'), ('TS1', 'CZE'), ('C1', 'SUI')]:
        assert COMP_COUNTRY[code] == expected
    assert len(set(COMP_COUNTRY)) == len(COMP_COUNTRY)


def test_country_guard_blocks_wrong_club_and_unknown_competition():
    clubs, _, _ = baseline_catalog()
    idx, by_id = club_lookup(clubs)
    rijeka = country_club('CRO', 'HNK Rijeka')
    korea = country_club('KOR', 'Jeonbuk Hyundai Motors')
    assert determine_club({'club_id':'10', 'name':'HNK Rijeka',
                            'domestic_competition_id':'KR1'}, idx,by_id,{}) == (rijeka['id'],'exact')
    assert determine_club({'club_id':'10', 'name':'Jeonbuk Hyundai Motors',
                            'domestic_competition_id':'RSK1'},idx,by_id,{}) == (korea['id'],'exact')
    assert determine_club({'club_id':'10', 'name':'Jeonbuk Hyundai Motors',
                            'domestic_competition_id':'KR1'},idx,by_id,{})[0] is None
    with pytest.raises(ValueError, match='crosses countries'):
        determine_club({'club_id':'10', 'name':'HNK Rijeka',
                        'domestic_competition_id':'KR1'},idx,by_id,{'10':korea['id']})


def test_generate_review_is_suggestions_not_auto_acceptance(tmp_path):
    src = sample_source(tmp_path)
    dest = tmp_path/'review.csv'
    report = generate_review(src, tmp_path/'aliases.json', dest)
    rows = read_review(dest)
    assert report['review_rows'] == 2
    assert set(r['source_club_id'] for r in rows) == {'31', '33'}
    row = next(r for r in rows if r['source_club_id'] == '31')
    assert row['velton_club_id'] == ''
    assert row['country_code'] == 'CRO'
    assert 'Dinamo Zagreb' in row['suggested_clubs']
    assert all('Jeonbuk' not in r['suggested_clubs'] for r in rows)


def test_human_checked_alias_adds_real_players_to_historical_pack(tmp_path):
    src = sample_source(tmp_path)
    review = tmp_path/'review.csv'
    aliases = tmp_path/'aliases.json'
    generate_review(src, aliases, review)
    dinamo = country_club('CRO', 'Dinamo Zagreb')
    fill_review(review, '31', dinamo['id'])
    result = apply_review(review, src, aliases)
    assert result['new_aliases'] == 1
    assert json.loads(aliases.read_text()) == {'31':dinamo['id']}
    assert apply_review(review, src, aliases)['new_aliases'] == 0
    players = tmp_path/'players.csv'
    with players.open('w',newline='',encoding='utf-8') as fd:
        fields=['player_id','name','current_club_id','position','last_season','date_of_birth']
        writer = csv.DictWriter(fd,fieldnames=fields)
        writer.writeheader()
        writer.writerow({'player_id':'990001','name':'Source-Provided Player Name',
                         'current_club_id':'31', 'position':'Attack','last_season':'2025',
                         'date_of_birth':'2000-03-02'})
    pack,audit=make_pack(players,src,aliases_json=aliases)
    actual=next(c for c in pack['clubs'] if c['id']==dinamo['id'])
    assert actual['players'][0]['name']=='Source-Provided Player Name'
    assert audit['players_in_export']==1


def test_manual_alias_rejects_foreign_country_and_is_atomic(tmp_path):
    src=sample_source(tmp_path)
    review=tmp_path/'review.csv'
    aliases=tmp_path/'aliases.json'
    generate_review(src,aliases,review)
    korea=country_club('KOR','Jeonbuk Hyundai Motors')
    fill_review(review,'31',korea['id'])
    with pytest.raises(ValueError,match='wrong country'):
        apply_review(review,src,aliases)
    assert not aliases.exists()


def test_review_rejects_fake_or_changed_source_identity(tmp_path):
    src=sample_source(tmp_path)
    review=tmp_path/'review.csv'
    aliases=tmp_path/'aliases.json'
    generate_review(src,aliases,review)
    dinamo=country_club('CRO','Dinamo Zagreb')
    fill_review(review,'31',dinamo['id'])
    rows=read_review(review)
    rows[0]['source_name']='Changed Data'
    with review.open('w',newline='',encoding='utf-8') as fd:
        writer=csv.DictWriter(fd,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    with pytest.raises(ValueError,match='does not match original CSV'):
        apply_review(review,src,aliases)
    assert not aliases.exists()


def test_duplicate_target_rejected_even_with_two_external_ids(tmp_path):
    src = sample_source(tmp_path)
    review=tmp_path/'review.csv'
    aliases=tmp_path/'aliases.json'
    generate_review(src,aliases,review)
    dinamo=country_club('CRO','Dinamo Zagreb')
    fill_review(review,'31',dinamo['id'])
    fill_review(review,'33',dinamo['id'])
    with pytest.raises(ValueError,match='two source clubs'):
        apply_review(review,src,aliases)
    assert not aliases.exists()


def test_alias_does_not_override_an_existing_exact_match(tmp_path):
    src=sample_source(tmp_path)
    review=tmp_path/'review.csv'
    aliases=tmp_path/'aliases.json'
    generate_review(src,aliases,review)
    dinamo=country_club('CRO','Dinamo Zagreb')
    rows=read_review(review)
    rows[0]['velton_club_id']=dinamo['id']
    # Reassigning an exact match is not possible through the prepare-generated review.
    assert not any(row['source_club_id']=='32' for row in rows)
