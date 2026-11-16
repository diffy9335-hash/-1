#!/usr/bin/env python3
"""VELTON static real-player squad builder, no API keys and no server-side network.

Input: transfermarkt-datasets 2026-07 static files players.csv(.gz), clubs.csv(.gz).
The optional --download operation is an explicit ONE-TIME request by the operator.
The running Telegram bot and mini-app never download football data.

Import rules:
- 2026/27 verified club squad overrides 2026-07 historical snapshot.
- Any ambiguous club or globally conflicting existing player is skipped, never guessed.
- Only athletes with last_season >= 2025 and explicit current_club_id are eligible.
- Inferred values and unverified official 2026/27 claims are never written.
- Output is deterministic, indexed by source IDs. Game economics stays synthetic.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import io
import json
import re
import shutil
import sys
import unicodedata
import urllib.request
from collections import defaultdict, Counter
from datetime import date
from difflib import get_close_matches
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from offline_catalog import parse_pack, seed_local_catalog
from world import init_world_db, LEAGUES
from verified_rosters import update_verified_catalog
import sqlite3

SOURCE_BASE = 'https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/'
SOURCE_INFO = 'https://github.com/dcaribou/transfermarkt-datasets'
SOURCE_SNAPSHOT = '2026-07-06'
ALIAS_PATH = ROOT / 'tools' / 'club_aliases_v09.json'
DATA_PATH = ROOT / 'world_data' / 'snapshots_v09'
OUTPUT_NAME = 'velton_real_2026_07_bulk.json'
POSITION = {'Goalkeeper': 'GK', 'Defender': 'DF', 'Midfield': 'MF', 'Attack': 'FW',
            'GK':'GK', 'DF':'DF', 'MF':'MF', 'FW':'FW'}
# Source identifiers are Transfermarkt competition codes, NOT FIFA country codes.
# Validate carefully: KR1 is Croatian HNL; Korean K League 1 is RSK1.
# See: https://github.com/dcaribou/transfermarkt-datasets/blob/master/data/competitions.json
COMP_COUNTRY = {
    'GB1': 'ENG', 'ES1': 'ESP', 'L1': 'GER', 'IT1': 'ITA', 'FR1': 'FRA',
    'PO1': 'POR', 'NL1': 'NED', 'BE1': 'BEL', 'TR1': 'TUR', 'RU1': 'RUS',
    'SC1': 'SCO', 'A1': 'AUT', 'C1': 'SUI', 'GR1': 'GRE', 'DK1': 'DEN',
    'NO1': 'NOR', 'SE1': 'SWE', 'PL1': 'POL', 'TS1': 'CZE', 'KR1': 'CRO',
    'UKR1': 'UKR', 'SER1': 'SRB', 'BRA1': 'BRA', 'ARG1': 'ARG',
    'URU1': 'URU', 'COLP': 'COL', 'CLPD': 'CHI', 'MLS1': 'USA',
    'MEX1': 'MEX', 'JAP1': 'JPN', 'RSK1': 'KOR', 'SA1': 'KSA',
    'CSL': 'CHN', 'EG1': 'EGY', 'MA1': 'MAR',
}



def basic_key(value: str) -> str:
    value = ''.join(c for c in unicodedata.normalize('NFKD', str(value).casefold())
                    if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '', value)


def plain_club(value: str) -> str:
    """Conservative decoration removal: no broad fuzzy auto matches."""
    s = unicodedata.normalize('NFKD', str(value).casefold())
    s = ''.join(x for x in s if not unicodedata.combining(x))
    parts = re.findall(r'[a-z0-9]+', s)
    # Remove only well-known club-type prefix/suffix, preserving core identity.
    while len(parts) > 1 and parts[0] in ('fc', 'cf', 'sc', 'ac', 'afc', 'sv', 'as', 'fk', 'club'):
        parts.pop(0)
    while len(parts) > 1 and parts[-1] in ('fc', 'cf', 'sc', 'afc', 'fk'):
        parts.pop()
    return ''.join(parts)


def open_csv(path: Path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8-sig', newline='') as handle:
        yield from csv.DictReader(handle)


def fetch_static_file(name: str, target: Path, *, fetcher=None):
    if name not in ('players.csv.gz','clubs.csv.gz'):
        raise ValueError('Only two fixed public source files may be downloaded')
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + '.tmp')
    request = urllib.request.Request(SOURCE_BASE+name, headers={'User-Agent':'VELTON-OfflineSnapshot-Importer/0.9'})
    fetcher = fetcher or urllib.request.urlopen
    size = 0
    try:
        with fetcher(request, timeout=50) as response, temp.open('wb') as dest:
            while True:
                chunk = response.read(262144)
                if not chunk: break
                size += len(chunk)
                if size > 80_000_000:
                    raise ValueError('Source exceeded safe 80 MB compressed limit')
                dest.write(chunk)
        if not size: raise ValueError('Downloaded empty source file')
        with gzip.open(temp,'rb') as check:
            if not check.read(100): raise ValueError('Source gzip is empty')
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)
    return size


def baseline_catalog():
    """Read pristine global catalog to anchor IDs and avoid overwriting verified 2026/27 rosters."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    init_world_db(conn)
    seed_local_catalog(conn)
    update_verified_catalog(conn)
    clubs = [dict(r) for r in conn.execute('SELECT id,league_id,name FROM club_catalog')]
    players = [dict(r) for r in conn.execute('SELECT id,name,club_id FROM player_catalog')]
    verified = {r[0] for r in conn.execute('SELECT club_id FROM roster_verified_clubs')}
    conn.close()
    return clubs, players, verified


def club_lookup(catalog_clubs):
    idx = defaultdict(set)
    by_id = {}
    for c in catalog_clubs:
        by_id[c['id']] = c
        for func in (basic_key,plain_club):
            token = func(c['name'])
            if token: idx[token].add(c['id'])
    return idx, by_id


def determine_club(row, idx, by_id, aliases):
    external_id = str(row.get('club_id') or '').strip()
    comp_id = str(row.get('domestic_competition_id') or '').strip().upper()
    association = COMP_COUNTRY.get(comp_id)
    # Unknown source competitions must be manually checked. An exact-looking
    # club name alone is not adequate to assign a source country.
    if comp_id and association is None:
        return None, 'unknown-competition'
    if external_id in aliases:
        cid = aliases[external_id]
        if cid not in by_id:
            raise ValueError(f'Bad club alias {external_id} => {cid}')
        if association and LEAGUES[by_id[cid]['league_id']]['association_code'] != association:
            raise ValueError(f'Club alias {external_id} crosses countries: {comp_id} -> {cid}')
        return cid, 'manual-id'
    source_name = str(row.get('name') or '').strip()
    if not source_name:
        return None, 'missing-name'
    candidates = set()
    for key in (basic_key(source_name), plain_club(source_name)):
        candidates.update(idx.get(key, set()))
    if association:
        candidates = {cid for cid in candidates
            if LEAGUES[by_id[cid]['league_id']]['association_code'] == association}
    if len(candidates) == 1:
        return next(iter(candidates)), 'exact'
    if len(candidates) > 1:
        return None, 'ambiguous'
    return None, 'unmatched'



def years_old(dob, as_of=date(2026,7,6)):
    if not dob: return None
    try:
        d=date.fromisoformat(dob[:10]); age=as_of.year-d.year - ((as_of.month,as_of.day)<(d.month,d.day))
        return age if 14<=age<=55 else None
    except ValueError: return None


def make_pack(players_csv, clubs_csv, *, aliases_json=None, limit_per_club=35, min_last_season=2025):
    if not players_csv.exists() or not clubs_csv.exists():
        raise FileNotFoundError('Requires players.csv.gz and clubs.csv.gz; use --download or copy local files first')
    catalog_clubs, catalog_players, verified = baseline_catalog()
    idx,by_id = club_lookup(catalog_clubs)
    aliases = json.loads(Path(aliases_json).read_text(encoding='utf-8')) if aliases_json else {}
    if not isinstance(aliases,dict): raise ValueError('Aliases must be an object mapping source club IDs to VELTON IDs')
    historical_names = defaultdict(set)
    for p in catalog_players:
        historical_names[basic_key(p['name'])].add(p['club_id'])
    tm_clubs = {}
    unresolved = []
    reason_counts=Counter()
    ambiguous = set()
    for row in open_csv(clubs_csv):
        ext_id=str(row.get('club_id','')).strip()
        if not ext_id: continue
        assigned,reason=determine_club(row,idx,by_id,aliases)
        tm_clubs[ext_id]=assigned
        reason_counts[reason]+=1
        if not assigned:
            # Human review suggestions only; NEVER silently auto-match fuzzy names.
            near=get_close_matches(plain_club(row.get('name','')),
                [plain_club(c['name']) for c in catalog_clubs],n=3,cutoff=.87)
            unresolved.append({'external_id':ext_id, 'external_name':row.get('name',''),
                'competition_id':row.get('domestic_competition_id',''), 'reason':reason,
                'review_name_hints':near})
        if assigned: ambiguous.add(assigned)
    source_clubs = defaultdict(list)
    candidates=Counter()
    excluded = Counter()
    seen_player_ids=set()
    seen_global_names=defaultdict(set)
    for p in open_csv(players_csv):
        external_player = str(p.get('player_id','')).strip()
        if not external_player or not external_player.isdigit() or external_player in seen_player_ids:
            excluded['missing_or_duplicate_player_id']+=1;continue
        seen_player_ids.add(external_player)
        season = p.get('last_season') or ''
        try: yr=int(str(season).strip()[:4])
        except ValueError: yr=0
        if yr < min_last_season:
            excluded['not_in_2025_26']+=1;continue
        external_club = str(p.get('current_club_id','')).strip()
        if not external_club or external_club not in tm_clubs or not tm_clubs[external_club]:
            excluded['unmatched_club']+=1;continue
        cid=tm_clubs[external_club]
        if cid in verified:
            excluded['more_recent_official_roster']+=1;continue
        name=str(p.get('name','')).strip()
        if len(name)<3 or len(name)>130 or any(ord(c)<32 for c in name):
            excluded['invalid_name']+=1;continue
        pos=POSITION.get(p.get('position',''))
        if not pos:
            excluded['invalid_position']+=1;continue
        token=basic_key(name)
        if not token:
            excluded['invalid_name']+=1;continue
        prior=historical_names.get(token,set())
        if prior and cid not in prior:
            excluded['prior_conflicting_club']+=1;continue
        if seen_global_names[token] and cid not in seen_global_names[token]:
            excluded['snapshot_conflicting_club']+=1;continue
        if len(source_clubs[cid])>=limit_per_club:
            excluded['exceeds_roster_cap']+=1;continue
        if token in {basic_key(q['name']) for q in source_clubs[cid]}:
            excluded['same_name_duplicate']+=1;continue
        seen_global_names[token].add(cid)
        playerspec={'id':'tm2026:'+external_player,'name':name,'position':pos,
                    'source':f'{SOURCE_INFO}; player snapshot {SOURCE_SNAPSHOT} (historical; NOT 2026/27 verified roster)'}
        age=years_old(p.get('date_of_birth'))
        if age is not None:playerspec['age']=age
        nationality=str(p.get('country_of_citizenship') or '').strip()
        if nationality and len(nationality)<=70:playerspec['nationality']=nationality
        source_clubs[cid].append(playerspec)
        candidates[cid]+=1
    catalog_by_id={c['id']:c for c in catalog_clubs}
    result={'format':'velton-offline-1','season':'2025/26 historical snapshot (6 July 2026)',
        'description': 'Historical club/athlete facts, NOT verified current 2026/27 squads; synthetic in-game ratings and values.',
        'clubs': []}
    for cid in sorted(source_clubs):
        c=catalog_by_id[cid]
        result['clubs'].append({'id':cid,'name':c['name'],'league_id':c['league_id'],
            'source':f'{SOURCE_INFO}; 2026-07 snapshot; club membership not verified for 2026/27',
            'players':sorted(source_clubs[cid],key=lambda r:r['id'])})
    audit={
        'source':SOURCE_INFO,'snapshot':SOURCE_SNAPSHOT,
        'warning':'Historical July 2026; no claim that players remain at these clubs in season 2026/27',
        'clubs_in_project':len(catalog_clubs),'official_2026_27_protected':len(verified),
        'matched_external_clubs':sum(1 for v in tm_clubs.values() if v),
        'unmatched_external_clubs':len(unresolved), 'club_matching':dict(reason_counts),
        'players_in_export':sum(len(c['players']) for c in result['clubs']),
        'clubs_with_players':len(result['clubs']),
        'clubs_20_plus':sum(len(c['players'])>=20 for c in result['clubs']),
        'exclusions':dict(excluded),'unmatched_clubs':unresolved,
        'roster_counts': [{'id':c['id'],'club':c['name'],'league_id':c['league_id'],
                           'players':len(c['players'])} for c in result['clubs']]
    }
    return result,audit


def main():
    parser=argparse.ArgumentParser(description='Bulk real-squad importer for VELTON from historic 2026 static CSV data')
    parser.add_argument('--players',type=Path,default=DATA_PATH/'players.csv.gz')
    parser.add_argument('--clubs',type=Path,default=DATA_PATH/'clubs.csv.gz')
    parser.add_argument('--download',action='store_true',help='Explicit one-time HTTPS download of public compressed static CSV files')
    parser.add_argument('--aliases',type=Path,default=ALIAS_PATH,help='Manual mapping source club_id -> VELTON club id')
    parser.add_argument('--output',type=Path,default=DATA_PATH/OUTPUT_NAME)
    parser.add_argument('--install',action='store_true',help='Install verified generated pack into world_data/packs/ for NEW saves')
    parser.add_argument('--max-per-club',type=int,default=35)
    parser.add_argument('--min-last-season',type=int,default=2025)
    args=parser.parse_args()
    if not 20<=args.max_per_club<=100:parser.error('--max-per-club must be 20..100')
    if not 2020<=args.min_last_season<=2026:parser.error('--min-last-season must be 2020..2026')
    if args.download:
        for name, target in [('players.csv.gz',args.players),('clubs.csv.gz',args.clubs)]:
            if target.exists():
                print('Already downloaded:',target)
            else:
                print('Downloading static snapshot:',name)
                print('Downloaded bytes:', fetch_static_file(name,target))
    pack,audit=make_pack(args.players,args.clubs,aliases_json=args.aliases,
        limit_per_club=args.max_per_club,min_last_season=args.min_last_season)
    parse_pack_content=args.output
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(pack,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Validate generated pack against VELTON official schema BEFORE installation.
    parse_pack(args.output)
    audit_path=args.output.with_suffix('.audit.json')
    audit_path.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in audit.items() if k not in ('unmatched_clubs','roster_counts')},
        ensure_ascii=False,indent=2))
    print('Pack:',args.output)
    print('Audit:',audit_path)
    if args.install:
        target=ROOT/'world_data'/'packs'/OUTPUT_NAME
        if target.exists():parser.error('Pack already exists; manually review/rename it before replacing')
        shutil.copy2(args.output,target)
        print('Installed for NEW career slots only:',target)

if __name__=='__main__':
    try:main()
    except (ValueError,FileNotFoundError,urllib.error.URLError,OSError,csv.Error) as e:
        print('Import failed:',str(e),file=sys.stderr)
        sys.exit(1)
