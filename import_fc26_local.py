#!/usr/bin/env python3
"""Optional, LOCAL EA FC 26 Kaggle/SoFIFA-style CSV to VELTON factual names.

No copyrighted ratings, club emblems, face pictures or game data imported.
Operator supplies a lawfully acquired CSV and checks its licence.
The 2025 game snapshot is NOT represented as the 2026/27 real-world roster.
"""
from __future__ import annotations
import argparse, csv, json, re, shutil, sys
from collections import Counter, defaultdict
from pathlib import Path
from datetime import date

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from offline_catalog import parse_pack
from tools.install_real_rosters_v09 import (baseline_catalog,club_lookup,determine_club,
    basic_key,plain_club,years_old)

SOURCE = 'https://www.kaggle.com/datasets/rovnez/fc-26-fifa-26-player-data'
POSITIONS={'GK':'GK','CB':'DF','LB':'DF','RB':'DF','LWB':'DF','RWB':'DF',
            'CDM':'MF','CM':'MF','CAM':'MF','LM':'MF','RM':'MF',
            'LW':'FW','RW':'FW','ST':'FW','CF':'FW','LF':'FW','RF':'FW'}


def row_field(row,*names):
    for name in names:
        if row.get(name) not in (None,'','nan'):
            return str(row[name]).strip()
    return ''


def make_fc_pack(path:Path,*,aliases=None,max_per_club=35):
    if not path.is_file():raise FileNotFoundError(f'No CSV: {path}')
    aliases = aliases or {}
    clubs,existing,verified=baseline_catalog()
    index,by_id=club_lookup(clubs)
    prior=defaultdict(set)
    for p in existing:prior[basic_key(p['name'])].add(p['club_id'])
    players=defaultdict(list)
    seen=defaultdict(set)
    excluded=Counter()
    club_match={}
    with path.open('r',encoding='utf-8-sig',newline='') as fd:
        reader=csv.DictReader(fd)
        required={'club_name','short_name','long_name'}
        if not (set(reader.fieldnames or []) & {'club_name','club','club_team'}) or not (
                set(reader.fieldnames or []) & {'long_name','short_name','name'}):
            raise ValueError('Expected FC26-style CSV with club_name and short_name or long_name')
        for row in reader:
            gender=row_field(row,'gender','gender_name')
            if gender and ('Women' in gender or 'Female' in gender):
                excluded['different_womens_competition']+=1;continue
            club_name=row_field(row,'club_name','club','club_team')
            club_key=row_field(row,'club_team_id') or club_name
            if not club_name:
                excluded['no_club']+=1;continue
            if club_key not in club_match:
                alias_id=aliases.get(club_key) or aliases.get(club_name)
                row_club={'club_id':club_key,'name':club_name,'domestic_competition_id':''}
                # No guessing from arbitrary commercial game league names.
                found,_=determine_club(row_club,index,by_id,{club_key:alias_id} if alias_id else {})
                club_match[club_key]=found
            cid=club_match[club_key]
            if not cid:
                excluded['unmatched_club']+=1;continue
            if cid in verified:
                excluded['official_2026_27_priority']+=1;continue
            name=row_field(row,'long_name','short_name','name')
            pid=row_field(row,'sofifa_id','player_id','id')
            if not pid.isdigit() or not (2<len(name)<=130):
                excluded['incomplete_player']+=1;continue
            token=basic_key(name)
            if token in seen[cid]:
                excluded['duplicate_in_club']+=1;continue
            if token in prior and cid not in prior[token]:
                excluded['conflicting_catalog_club']+=1;continue
            if len(players[cid]) >= max_per_club:
                excluded['club_roster_cap']+=1;continue
            pos=row_field(row,'player_positions','position','primary_position').split(',')[0].strip().upper()
            if pos not in POSITIONS:
                excluded['unknown_position']+=1;continue
            birth=row_field(row,'dob','birthdate','date_of_birth')
            age=years_old(birth,as_of=date(2025,9,21))
            if not age:
                try:age=int(row_field(row,'age'))
                except ValueError:age=None
            person={'id':'fc26:'+pid,'name':name,'position':POSITIONS[pos],
                    'source':SOURCE+' (2025 game dataset; NOT official 2026/27 club roster)'}
            if age and 14<=age<=55:person['age']=age
            nat=row_field(row,'nationality_name','nationality')
            if nat and len(nat)<70:person['nationality']=nat
            players[cid].append(person)
            seen[cid].add(token)
    by_id={c['id']:c for c in clubs}
    pack={'format':'velton-offline-1','season':'2025/26 EA FC 26 historical game roster',
          'description':'Only real person names and listed 2025 club links; not 2026/27 verified roster; no EA attributes.',
          'clubs':[{'id':c['id'],'league_id':c['league_id'],'name':c['name'],
                    'source':SOURCE+' (game snapshot, not official squad)',
                    'players':sorted(players[cid],key=lambda p:p['id'])}
                   for cid in sorted(players) for c in [by_id[cid]] if players[cid]]}
    audit={'clubs_with_names':len(pack['clubs']),'player_records':sum(len(c['players']) for c in pack['clubs']),
           'source':SOURCE,'snapshot_warning':'Game roster of 2025/26, not confirmed current 2026/27!',
           'exclusions':dict(excluded),
           'unmatched_source_clubs':[{'key':k} for k,v in club_match.items() if not v]}
    return pack,audit


def main():
    p=argparse.ArgumentParser(description='Import locally provided licensed FC 26 CSV for wider 2025/26 squad coverage')
    p.add_argument('csv',type=Path,help='Local Kaggle FC26 dataset downloaded by the operator')
    p.add_argument('--output',type=Path,default=ROOT/'world_data'/'snapshots_v09'/'velton_z_fc26_2025_26.json')
    p.add_argument('--aliases',type=Path,help='Optional reviewed map source club ID/name -> VELTON club ID')
    p.add_argument('--max-per-club',type=int,default=35)
    p.add_argument('--install',action='store_true')
    a=p.parse_args()
    if not 20<=a.max_per_club<=100:p.error('Choose max per club between 20 and 100')
    aliases=json.loads(a.aliases.read_text(encoding='utf-8')) if a.aliases else {}
    result,audit=make_fc_pack(a.csv,aliases=aliases,max_per_club=a.max_per_club)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    parse_pack(a.output)
    a.output.with_suffix('.audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in audit.items() if k!='unmatched_source_clubs'},ensure_ascii=False,indent=2))
    if a.install:
        target=ROOT/'world_data'/'packs'/'velton_z_fc26_2025_26.json'
        if target.exists():p.error('Existing pack; back it up and review before replacement')
        shutil.copy2(a.output,target)
        print('Installed for future careers only:',target)

if __name__=='__main__':
    try:main()
    except (ValueError,FileNotFoundError,OSError) as ex:
        print('Import error:',ex,file=sys.stderr);sys.exit(1)
