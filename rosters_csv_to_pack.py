#!/usr/bin/env python3
"""Make an offline JSON pack from a manually curated CSV (NO network calls)."""
import argparse,csv,json,sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description='CSV columns: league_id,club,player,position,age,nationality,source')
    ap.add_argument('csv_file',type=Path);ap.add_argument('output',type=Path)
    args=ap.parse_args()
    clubs={}
    with args.csv_file.open(encoding='utf-8-sig',newline='') as handle:
        reader=csv.DictReader(handle)
        if not {'league_id','club','player','source'} <= set(reader.fieldnames or []):
            ap.error('Required columns: league_id,club,player,source')
        for i,row in enumerate(reader,2):
            lid=(row.get('league_id') or '').strip();name=(row.get('club') or '').strip();source=(row.get('source') or '').strip()
            if not lid or not name or not source:ap.error(f'Missing league/club/source at CSV line {i}')
            key=(lid,name)
            if key not in clubs:clubs[key]={'league_id':lid,'name':name,'source':source,'players':[]}
            pn=(row.get('player') or '').strip()
            if pn:
                age=(row.get('age') or '').strip()
                clubs[key]['players'].append({'name':pn,'position':(row.get('position') or '').strip() or None,
                    'age':int(age) if age.isdigit() else None,'nationality':(row.get('nationality') or '').strip() or None,'source':source})
    result={'format':'velton-offline-1','season':'curated manually','clubs':list(clubs.values())}
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from offline_catalog import parse_pack
    parsed=parse_pack(args.output)
    print(f'Valid offline pack: {len(parsed)} clubs / {sum(len(x[-1]) for x in parsed)} footballers -> {args.output}')
if __name__=='__main__':main()
