#!/usr/bin/env python3
"""Safely review unmatched source clubs before importing historic real rosters.

No network. All suggestions are informational; no fuzzy matching is auto-applied.
Review file can be edited in Excel, then validated and installed as explicit aliases.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.install_real_rosters_v09 import (
    ALIAS_PATH, COMP_COUNTRY, DATA_PATH, baseline_catalog, basic_key,
    club_lookup, determine_club, open_csv, plain_club,
)
from world import LEAGUES

REVIEW_FIELDS = [
    'source_club_id', 'source_name', 'source_competition', 'country_code',
    'reason', 'suggested_clubs', 'velton_club_id',
]


def load_aliases(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                         for k, v in data.items()):
        raise ValueError('Alias file must be a JSON object: source club ID -> VELTON club ID')
    return data


def source_clubs(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f'Source clubs file not found: {path}')
    result = {}
    for row in open_csv(path):
        cid = str(row.get('club_id') or '').strip()
        if not cid:
            continue
        value = {'club_id': cid, 'name': str(row.get('name') or '').strip(),
                 'domestic_competition_id': str(row.get('domestic_competition_id') or '').strip().upper()}
        if cid in result and result[cid] != value:
            raise ValueError(f'Conflicting external club ID {cid}: source file has repeated different records')
        result[cid] = value
    return result


def suggest(source_name: str, association: str | None, catalog: list[dict], limit: int = 3):
    """Advisory suggestions only, restricted to the documented source country."""
    if not source_name or not association:
        return []
    key = plain_club(source_name)
    if len(key) < 3:
        return []
    scored = []
    for club in catalog:
        if LEAGUES[club['league_id']]['association_code'] != association:
            continue
        ratio = SequenceMatcher(None, key, plain_club(club['name'])).ratio()
        if ratio >= .48:
            scored.append((ratio, club['id'], club['name']))
    scored.sort(key=lambda r: (-r[0], r[2]))
    return [(cid, name, round(score, 3)) for score, cid, name in scored[:limit]]


def generate_review(clubs_csv: Path, aliases_path: Path, review_path: Path):
    catalog, _, _ = baseline_catalog()
    index, by_id = club_lookup(catalog)
    aliases = load_aliases(aliases_path)
    rows = []
    reasons = {}
    for external, source in sorted(source_clubs(clubs_csv).items(), key=lambda x: x[0]):
        matched, reason = determine_club(source, index, by_id, aliases)
        if matched:
            continue
        comp = source['domestic_competition_id']
        country = COMP_COUNTRY.get(comp, '')
        candidates = suggest(source['name'], country, catalog)
        rows.append({
            'source_club_id': external,
            'source_name': source['name'],
            'source_competition': comp,
            'country_code': country,
            'reason': reason,
            'suggested_clubs': ' | '.join(f'{cid} = {name} ({score:.2f})'
                                          for cid, name, score in candidates),
            'velton_club_id': '',
        })
        reasons[reason] = reasons.get(reason, 0) + 1
    review_path.parent.mkdir(parents=True, exist_ok=True)
    with review_path.open('w', encoding='utf-8-sig', newline='') as fd:
        writer = csv.DictWriter(fd, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return {'review_rows': len(rows), 'reasons': reasons, 'review_file': str(review_path)}


def apply_review(review_path: Path, clubs_csv: Path, aliases_path: Path):
    source = source_clubs(clubs_csv)
    clubs, _, _ = baseline_catalog()
    by_id = {row['id']: row for row in clubs}
    index, _ = club_lookup(clubs)
    aliases = load_aliases(aliases_path)
    staged = dict(aliases)
    used_targets = {v: k for k, v in aliases.items()}
    accepted = 0
    skipped = 0
    encountered = set()
    with review_path.open('r', encoding='utf-8-sig', newline='') as fd:
        reader = csv.DictReader(fd)
        if not set(REVIEW_FIELDS).issubset(reader.fieldnames or ()):
            raise ValueError('Review CSV has missing or renamed columns; rerun prepare')
        for lineno, row in enumerate(reader, 2):
            external = (row['source_club_id'] or '').strip()
            if external in encountered:
                raise ValueError(f'Line {lineno}: duplicate external club ID {external}')
            encountered.add(external)
            real = source.get(external)
            if not real:
                raise ValueError(f'Line {lineno}: source ID no longer exists ({external})')
            if row['source_name'] != real['name'] or row['source_competition'] != real['domestic_competition_id']:
                raise ValueError(f'Line {lineno}: source name/competition does not match original CSV')
            target = (row.get('velton_club_id') or '').strip()
            if not target:
                skipped += 1
                continue
            if target not in by_id:
                raise ValueError(f'Line {lineno}: VELTON club {target} not found')
            comp = real['domestic_competition_id']
            assoc = COMP_COUNTRY.get(comp)
            if not assoc:
                raise ValueError(f'Line {lineno}: unknown competition {comp}; cannot verify country')
            actual_assoc = LEAGUES[by_id[target]['league_id']]['association_code']
            if actual_assoc != assoc:
                raise ValueError(f'Line {lineno}: wrong country {comp} ({assoc}) != {actual_assoc}')
            previous = staged.get(external)
            if previous and previous != target:
                raise ValueError(f'Line {lineno}: attempts to overwrite reviewed alias {external}')
            other_external = used_targets.get(target)
            if other_external and other_external != external:
                raise ValueError(f'Line {lineno}: two source clubs mapped to one team: {other_external}/{external}')
            # Do not let manual overrides silently replace already unambiguous exact matches.
            automatic, reason = determine_club(real, index, by_id, {})
            if automatic and automatic != target:
                raise ValueError(f'Line {lineno}: existing exact match is {automatic}, not {target}')
            used_targets[target] = external
            if previous == target:
                skipped += 1
            else:
                staged[external] = target
                accepted += 1
    if accepted:
        aliases_path.parent.mkdir(parents=True, exist_ok=True)
        # No partially-written aliases even if an error is detected at the end.
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=aliases_path.parent,
                                         prefix='.velton-alias-', suffix='.json', delete=False) as fd:
            temp_path = Path(fd.name)
            try:
                json.dump(dict(sorted(staged.items())), fd, ensure_ascii=False, indent=2)
                fd.write('\n')
            except Exception:
                temp_path.unlink(missing_ok=True)
                raise
        os.replace(temp_path, aliases_path)
    return {'new_aliases': accepted, 'unchanged_or_blank_rows': skipped,
            'total_aliases': len(staged), 'aliases_file': str(aliases_path)}


def main():
    parser = argparse.ArgumentParser(description='Review unmatched VELTON real-world clubs (offline)')
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('prepare', 'apply'):
        command = sub.add_parser(action)
        command.add_argument('--clubs', type=Path, default=DATA_PATH/'clubs.csv.gz')
        command.add_argument('--aliases', type=Path, default=ALIAS_PATH)
        command.add_argument('--review', type=Path, default=DATA_PATH/'clubs_to_review_v10.csv')
    args = parser.parse_args()
    result = (generate_review(args.clubs, args.aliases, args.review) if args.action == 'prepare'
              else apply_review(args.review, args.clubs, args.aliases))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError, csv.Error) as err:
        print('VELTON review error:', err, file=sys.stderr)
        sys.exit(1)
