#!/usr/bin/env python3
"""Report real roster coverage across ALL VELTON clubs, without fake completion."""
from __future__ import annotations
import argparse, csv, json, sqlite3, sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from world import init_world_db
from offline_catalog import seed_local_catalog
from verified_rosters import update_verified_catalog


def audit(conn):
    rows=[dict(r) for r in conn.execute('''
        SELECT cc.id,cc.name,cc.league_id,lc.country, COUNT(pc.id) AS catalog_rows,
        SUM(CASE WHEN pc.id IS NOT NULL AND (vr.club_id IS NULL OR pc.confirmed_2627=1) THEN 1 ELSE 0 END) AS active_players,
        SUM(CASE WHEN pc.source LIKE '%snapshot 2026-07-%' THEN 1 ELSE 0 END) AS historical_bulk_players,
        COALESCE(vr.season,'') AS verified_season, COALESCE(vr.verified_players,0) AS verified_players
        FROM club_catalog cc JOIN league_catalog lc ON lc.id=cc.league_id
        LEFT JOIN roster_verified_clubs vr ON vr.club_id=cc.id
        LEFT JOIN player_catalog pc ON pc.club_id=cc.id
        GROUP BY cc.id ORDER BY cc.league_id,cc.name''')]
    for r in rows:
        r['active_players']=int(r['active_players'] or 0)
        r['historical_bulk_players']=int(r['historical_bulk_players'] or 0)
        r['coverage'] = ('official_2026_27' if r['verified_season']=='2026/27'
                          else 'historical_20_plus' if r['active_players']>=20
                          else 'partial' if r['active_players'] else 'empty')
    summary={'clubs':len(rows),'leagues':len(set(r['league_id'] for r in rows)),
             'players_available_in_new_saves':sum(r['active_players'] for r in rows),
             'clubs_20_plus':sum(r['active_players']>=20 for r in rows),
             'clubs_30_plus':sum(r['active_players']>=30 for r in rows),
             'clubs_empty':sum(not r['active_players'] for r in rows),
             'confirmed_official_2026_27_clubs':sum(r['coverage']=='official_2026_27' for r in rows),
             'coverage_states':dict(Counter(r['coverage'] for r in rows))}
    return rows,summary


def main():
    parser=argparse.ArgumentParser(description='VELTON full 35-country/80-league squad audit')
    parser.add_argument('--db',type=Path,help='Examine running VELTON sqlite database (read-only)')
    parser.add_argument('--csv',type=Path,default=ROOT/'docs'/'coverage_v09.csv')
    parser.add_argument('--json',type=Path,default=ROOT/'docs'/'coverage_v09.json')
    args=parser.parse_args()
    if args.db:
        if not args.db.is_file():parser.error('Database not found')
        conn=sqlite3.connect('file:'+str(args.db.resolve())+'?mode=ro',uri=True)
    else:
        conn=sqlite3.connect(':memory:')
    conn.row_factory=sqlite3.Row
    if not args.db:
        init_world_db(conn)
        seed_local_catalog(conn)
        update_verified_catalog(conn)
    rows,summary=audit(conn)
    args.csv.parent.mkdir(parents=True,exist_ok=True)
    fields=['league_id','country','name','id','active_players','catalog_rows',
            'historical_bulk_players','verified_season','verified_players','coverage']
    with args.csv.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    args.json.write_text(json.dumps({'summary':summary,'rows':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print('CSV',args.csv)
    conn.close()

if __name__=='__main__':main()
