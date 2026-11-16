"""Optional personally supplied licensed FC26 factual-roster CSV import."""
import csv, json
from tools.import_fc26_local import make_fc_pack
from offline_catalog import parse_pack


def test_optional_fc26_accepts_names_rejects_ambiguous_and_womens(tmp_path):
    source=tmp_path/'fc26.csv'
    keys=['sofifa_id','long_name','short_name','club_name','player_positions','dob','gender','nationality_name']
    rows=[{'sofifa_id':str(i),'long_name':f'Source Factual Person {i}',
           'club_name':'Atalanta','player_positions':('ST','CM','CB','GK')[i%4],
           'dob':'2000-01-03','gender':"Men's Football",'nationality_name':'Italy'}
          for i in range(1,22)]
    rows += [{'sofifa_id':'9999','long_name':'Test Women Footballer','club_name':'Atalanta',
             'player_positions':'ST','gender':"Women's Football"},
             {'sofifa_id':'10000','long_name':'Nonexistent Club Athlete','club_name':'Invented City',
             'player_positions':'ST','gender':"Men's Football"},
             {'sofifa_id':'10001','long_name':'Verified Team Athlete','club_name':'Arsenal',
             'player_positions':'ST','gender':"Men's Football"}]
    with source.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
    pack,audit=make_fc_pack(source)
    assert len(pack['clubs'])==1 and pack['clubs'][0]['name']=='Atalanta'
    assert audit['player_records']==21
    assert audit['exclusions']['official_2026_27_priority']==1
    assert audit['exclusions']['different_womens_competition']==1
    f=tmp_path/'pack.json';f.write_text(json.dumps(pack),encoding='utf-8')
    assert len(parse_pack(f)[0][-1])==21
