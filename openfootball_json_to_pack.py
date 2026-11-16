#!/usr/bin/env python3
"""Convert a *downloaded* public-domain openfootball/football.json match file
into an offline club-only VELTON snapshot. No match results are imported.
NO network activity, key, external API, or live fixture dependency.
"""
import argparse,json,sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description='Offline openfootball club-name importer (not live matches)')
    ap.add_argument('league_id',help='VELTON league ID, e.g. ENG_3')
    ap.add_argument('input_json',type=Path,help='Previously downloaded football.json competition snapshot')
    ap.add_argument('output_json',type=Path,help='Output offline team pack')
    ap.add_argument('--source',required=True,help='URL or citation of the static snapshot you downloaded')
    args=ap.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from world import LEAGUES
    from offline_catalog import parse_pack
    if args.league_id not in LEAGUES:ap.error('Unknown league ID')
    doc=json.loads(args.input_json.read_text(encoding='utf-8'))
    if not isinstance(doc,dict) or not isinstance(doc.get('matches'),list):ap.error('Input is not openfootball football.json match JSON')
    teams=set()
    for game in doc['matches']:
        if not isinstance(game,dict):continue
        for key in ('team1','team2'):
            if isinstance(game.get(key),str) and game[key].strip():teams.add(game[key].strip())
    if not teams:ap.error('The snapshot contains no team names')
    if len(teams)>120:ap.error('Too many names in one league; check the source and groups')
    result={'format':'velton-offline-1','season':doc.get('name','static snapshot'),
      'description':'Only club names are used. All in-game games are simulated by VELTON.',
      'clubs':[{'league_id':args.league_id,'name':name,'source':args.source,'players':[]} for name in sorted(teams)]}
    args.output_json.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    parse_pack(args.output_json)
    print(f'Offline source validated: {len(teams)} clubs -> {args.output_json}')
if __name__=='__main__':main()
