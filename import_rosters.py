#!/usr/bin/env python3
"""Import a LOCAL, sourced VELTON catalog pack. No network access."""
import argparse, json, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from offline_catalog import parse_pack, PACK_DIR

def main():
    parser=argparse.ArgumentParser(description='Add verified clubs and named footballers to the next VELTON offline release')
    parser.add_argument('json_file',type=Path,help='Path to a velton-offline-1 JSON file on this computer')
    parser.add_argument('--install',action='store_true',help='Copy validated pack to world_data/packs; picked up by next server restart')
    args=parser.parse_args()
    clubs=parse_pack(args.json_file)
    num=sum(len(cl[-1]) for cl in clubs)
    print(json.dumps({'valid':True,'clubs':len(clubs),'named_players':num,'source_file':str(args.json_file)},ensure_ascii=False,indent=2))
    if args.install:
        PACK_DIR.mkdir(parents=True,exist_ok=True)
        destination=PACK_DIR/args.json_file.name
        if destination.resolve()!=args.json_file.resolve():
            if destination.exists():parser.error('File already exists: '+str(destination))
            shutil.copy2(args.json_file,destination)
        print('Pack installed. Restart server to load new teams into new careers:',destination)

if __name__=='__main__':
    try:main()
    except (ValueError,json.JSONDecodeError,OSError) as exc:
        print('Import error:',exc,file=sys.stderr)
        sys.exit(1)
