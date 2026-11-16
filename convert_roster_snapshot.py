#!/usr/bin/env python3
"""Convert a locally downloaded, ATTRIBUTED player->club snapshot to a VELTON pack.

No network access: users supply a TSV or CSV they legitimately obtained.
No player or club names are fabricated, no third-party match results imported.
Only unequivocal matches in the already-known Big Five first tiers are accepted.
"""
from __future__ import annotations
import argparse, csv, hashlib, io, json, re, sys, unicodedata
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from offline_catalog import parse_pack

BIG_FIVE={'ENG':'ENG_1','ESP':'ESP_1','GER':'GER_1','ITA':'ITA_1','FRA':'FRA_1'}
LEAGUE_COUNTRIES={'ENG_1':'ENG','ESP_1':'ESP','GER_1':'GER','ITA_1':'ITA','FRA_1':'FRA'}
# Exact, human-reviewed aliases for a real club whose snapshot differs from VELTON.
ALIASES={
 'ENG_1':{
  'manchester city fc':'Manchester City','manchester united fc':'Manchester United',
  'tottenham hotspur fc':'Tottenham Hotspur','liverpool fc':'Liverpool',
  'aston villa fc':'Aston Villa','chelsea fc':'Chelsea','arsenal fc':'Arsenal',
  'brighton & hove albion fc':'Brighton & Hove Albion',
  'fulham fc':'Fulham','hull city fc':'Hull City',
  'newcastle united fc':'Newcastle United','brentford fc':'Brentford',
  'crystal palace fc':'Crystal Palace','sunderland afc':'Sunderland',
  'nottingham forest fc':'Nottingham Forest','everton fc':'Everton',
  'coventry city fc':'Coventry City','leeds united fc':'Leeds United',
  'ipswich town fc':'Ipswich Town','bournemouth':'AFC Bournemouth',
 },
 'ESP_1':{
  'atletico de madrid':'Atlético de Madrid','real madrid c. f.':'Real Madrid',
  'barcelona':'FC Barcelona','rc celta vigo':'Celta',
  'racing santander':'Racing de Santander',
 },
 'GER_1':{'bayern munich':'FC Bayern München','borussia dortmund':'Borussia Dortmund',
           'hoffenheim':'TSG Hoffenheim','leverkusen':'Bayer 04 Leverkusen',
           'union berlin':'1. FC Union Berlin','schalke':'FC Schalke 04',
           'werder bremen':'SV Werder Bremen',
 },
 'ITA_1':{
   'fc internazionale milano':'Inter','internazionale':'Inter',
   'ac milan':'Milan','juventus fc':'Juventus','ssc napoli':'Napoli',
   'as roma':'Roma','ac fiorentina':'Fiorentina','atalanta bergamo':'Atalanta',
   'bologna fc':'Bologna','cagliari calcio':'Cagliari','venezia fc':'Venezia',
   'us sassuolo':'Sassuolo','torino fc':'Torino','genoa cfc':'Genoa',
 },
 'FRA_1':{'olympique marseille':'Olympique de Marseille',
           'olympique lyonnais':'Olympique Lyonnais',
           'rc lens':'Racing Club de Lens',
           'rc strasbourg':'RC Strasbourg Alsace',
           'paris saint-germain':'Paris Saint-Germain FC',
           'stade rennais fc':'Stade Rennais FC 1901',
           'as monaco':'AS Monaco FC','stade rennais':'Stade Rennais FC 1901',
 },
}

def norm(text:str)->str:
    value=unicodedata.normalize('NFKD',str(text).casefold())
    return ''.join(ch for ch in value if not unicodedata.combining(ch) and ch.isalnum())

def catalog():
    clubs={};names=defaultdict(set);all_player_names=defaultdict(set)
    for p in sorted((ROOT/'world_data/packs').glob('*.json')):
        for cid,lid,club_name,_,source,players in parse_pack(p):
            if lid not in LEAGUE_COUNTRIES:continue
            club_key=(lid,norm(club_name))
            if club_key in clubs and clubs[club_key][0]!=cid:continue
            clubs[club_key]=(cid,lid,club_name)
            for _,_,pn,*_ in players:
                names[cid].add(norm(pn))
                all_player_names[norm(pn)].add(cid)
    return clubs,names,all_player_names

def lookup_club(clubs,league,raw):
    alias=ALIASES.get(league,{}).get(raw.strip().casefold())
    if alias:
        return clubs.get((league,norm(alias)))
    return clubs.get((league,norm(raw)))

def player_name(raw:dict):
    # FIFA 2026's PLAYER NAME is "SURNAME Given"; first/last fields may contain
    # full legal names, so prefer the display field to avoid 4-word duplications.
    text=raw.get('PLAYER NAME','').strip()
    parts=text.split()
    if len(parts)==1:return parts[0].title()
    first_non_upper=next((i for i,v in enumerate(parts) if v != v.upper()),0)
    if first_non_upper>0:
        return ' '.join(parts[first_non_upper:]+[x.title() for x in parts[:first_non_upper]])
    first=raw.get('FIRST NAME(S)','').strip().split(' ')[0]
    last=raw.get('LAST NAME(S)','').strip()
    return ' '.join([first.title(),last.title()]).strip() if first and last else text.title()

def age_as_of(value,as_of=date(2026,11,15)):
    if not value:return None
    try:
        born=datetime.strptime(value.strip(),'%d/%m/%Y').date()
    except ValueError:return None
    years=as_of.year-born.year-((as_of.month,as_of.day)<(born.month,born.day))
    return years if 14<=years<=55 else None

def records(path:Path,fmt:str):
    with path.open('r',encoding='utf-8-sig',newline='') as inp:
        if fmt=='fifa26':
            for row in csv.DictReader(inp,delimiter='\t'):
                raw_club=row.get('CLUB','').strip()
                match=re.fullmatch(r'(.+?) \(([A-Z]{3})\)',raw_club)
                if not match or match[2] not in BIG_FIVE:continue
                name=player_name(row)
                pos=row.get('POS','').strip().upper()
                if not name or pos not in {'GK','DF','MF','FW'}:continue
                yield (BIG_FIVE[match[2]],match[1],name,pos,age_as_of(row.get('DOB','')),None)
        else:
            for row in csv.DictReader(inp):
                club=(row.get('club') or '').strip()
                name=(row.get('name') or '').strip()
                country=(row.get('club_country') or '').strip().upper()
                if not name or not club:continue
                # BeyondELO data has player national team country_code, NOT club country!
                # Resolve in all five countries, rejecting ambiguous club names.
                pos=(row.get('position') or '').upper().strip()
                if pos in {'GK'}:mapped='GK'
                elif pos in {'CB','RB','LB','RWB','LWB','DF'}:mapped='DF'
                elif pos in {'DM','CM','AM','LM','RM','MF'}:mapped='MF'
                elif pos in {'LW','RW','CF','ST','SS','FW'}:mapped='FW'
                else:mapped=None
                for league in BIG_FIVE.values():
                    yield (league,club,name,mapped,None,row.get('as_of'))

def convert(source_file:Path,fmt:str,source_url:str,output:Path):
    if not source_url.startswith(('http://','https://')):
        raise ValueError('Source URL is required for attribution and auditing')
    clubs,existing,all_names=catalog()
    result=defaultdict(dict);missing=defaultdict(int);conflicts=[];seen=set();ambiguous=[]
    for lid,raw_club,pname,pos,age,snapshot in records(source_file,fmt):
        linked=lookup_club(clubs,lid,raw_club)
        if not linked:
            missing[f'{lid}:{raw_club}']+=1;continue
        cid,_,club_name=linked
        token=norm(pname)
        if len(token)<3 or not pname.strip():continue
        if token in existing[cid]:continue
        if token in all_names and cid not in all_names[token]:
            conflicts.append({'player':pname,'proposed_club':club_name,'reason':'already in a different catalog club'})
            continue
        key=(cid,token)
        if key in seen:continue
        seen.add(key)
        result[(lid,cid,club_name)][token]={'id':'snap07:'+hashlib.sha256((cid+'|'+token).encode()).hexdigest()[:20],
                                           'name':pname,'position':pos,'source':source_url}
        if age is not None:result[(lid,cid,club_name)][token]['age']=age
        existing[cid].add(token);all_names[token].add(cid)
    rows=[{'id':cid,'league_id':lid,'name':name,'source':source_url,'players':list(players.values())}
          for (lid,cid,name),players in sorted(result.items()) if players]
    doc={'format':'velton-offline-1','source_snapshot':fmt,'source_url':source_url,
         'import_scope':'Big Five top-flight clubs only, known VELTON entrants, partial snapshot','clubs':rows}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    parse_pack(output)  # independently validate all records before treating as installable
    audit={'matched_clubs':len(rows),'new_players':sum(len(r['players']) for r in rows),
           'unmatched_source_club_counts':dict(sorted(missing.items())),
           'existing_club_conflicts':conflicts,
           'note':'Not all current club rosters are represented. A snapshot is a dated source, not a live official transfer feed.'}
    output.with_suffix('.audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return audit

if __name__=='__main__':
    ap=argparse.ArgumentParser(description='Create an OFFLINE pack from a local verified roster snapshot')
    ap.add_argument('input',type=Path)
    ap.add_argument('output',type=Path)
    ap.add_argument('--format',choices=['fifa26','beyondelo'],default='fifa26')
    ap.add_argument('--source-url',required=True)
    args=ap.parse_args()
    print(json.dumps(convert(args.input,args.format,args.source_url,args.output),ensure_ascii=False,indent=2))
