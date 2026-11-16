#!/usr/bin/env python3
"""Curated, checked entries from 2026 FIFA tournament team roster snapshot.

The fixture universe and simulator stay offline. The data below is a **subset**
not a claim of full live 2026/27 club squads. Source:
https://github.com/matyuschenko/fifa-wc2026-players/blob/main/data/players.tsv
CC BY 4.0; collected 2026-09-10. Attribution in THIRD_PARTY_NOTICES.md.
"""
import hashlib, json, sqlite3, sys, unicodedata, re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from offline_catalog import parse_pack

SOURCE='https://github.com/matyuschenko/fifa-wc2026-players/blob/main/data/players.tsv (CC BY 4.0; team affiliations as reported 2026-09-10; not full squads)'
# Each club is a real VELTON league entrant. The selected names & positions below
# appear in the dated, public roster dataset above. Unknown club links are OMITTED.
DATA=r'''
ENG_1|Brentford|Igor Thiago~FW,Jordan Henderson~MF,Kristoffer Ajer~DF,Aaron Hickey~DF
ENG_1|AFC Bournemouth|Justin Kluivert~MF,Ryan Christie~MF,Ben Gannon-Doak~FW,Tyler Adams~MF
ENG_1|Brighton & Hove Albion|Maxim De Cuyper~DF,Pascal Gross~MF,Bart Verbruggen~GK,Jan Paul Van Hecke~DF,Mats Wieffer~DF,Diego Gomez~MF,Yasin Ayari~MF,Ferdi Kadioglu~DF
ENG_1|Everton|Jordan Pickford~GK,Nathan Patterson~DF,Idrissa Gana Gueye~MF,Iliman Ndiaye~FW
ENG_1|Fulham|Timothy Castagne~DF,Raul Jimenez~FW,Issa Diop~DF,Sander Berge~MF,Oscar Bobb~MF,Antonee Robinson~DF
ENG_1|Newcastle United|Bruno Guimaraes~MF,Yoane Wissa~FW,Tino Livramento~DF,Dan Burn~DF,Anthony Gordon~FW,Nick Woltemade~FW,Malick Thiaw~DF,Anthony Elanga~FW
ENG_1|Nottingham Forest|Ibrahim Sangare~MF,Elliot Anderson~MF,Chris Wood~FW,Angus Gunn~GK,Dan Ndoye~FW
ENG_1|Sunderland|Noah Sadiki~MF,Nilson Angulo~FW,Wilson Isidor~FW,Chemsdine Talbi~MF,Lutsharel Geertruida~DF,Robin Roefs~GK,Brian Brobbey~FW,Omar Alderete~DF,Habib Diarra~MF,Granit Xhaka~MF
ENG_1|Leeds United|Ao Tanaka~MF,Gabriel Gudmundsson~DF,Noah Okafor~FW,Brenden Aaronson~FW
ESP_1|Athletic Club|Inaki Williams~FW,Aymeric Laporte~DF,Nico Williams~FW,Unai Simon~GK
ESP_1|CA Osasuna|Ante Budimir~FW,Victor Munoz~FW
ESP_1|Celta|Borja Iglesias~FW,Carl Starfelt~DF
ESP_1|Elche CF|David Affengruber~DF
ESP_1|Levante UD|Mathew Ryan~GK
ESP_1|RCD Espanyol|Charles Pickel~MF
ESP_1|Rayo Vallecano|Abdul Mumin~DF,Pathe Ciss~MF
ESP_1|Sevilla FC|Orjan Nyland~GK,Djibril Sow~MF,Ruben Vargas~FW
ESP_1|Valencia CF|Eray Comert~DF
ESP_1|Real Betis|Giovani Lo Celso~MF,Cucho Hernandez~FW,Cedric Bakambu~FW,Alvaro Fidalgo~MF,Sofyan Amrabat~MF,Abde Ezzalzouli~FW,Ricardo Rodriguez~DF
ESP_1|Real Sociedad|Duje Caleta-Car~DF,Luka Sucic~MF,Takefusa Kubo~MF,Goncalo Guedes~FW,Mikel Oyarzabal~FW
ESP_1|Atlético de Madrid|Juan Musso~GK,Julian Alvarez~FW,Nico Gonzalez~MF,Thiago Almada~FW,Giuliano Simeone~FW,Nahuel Molina~DF,Obed Vargas~MF,Alexander Sorloth~FW,Marc Pubill~DF,Marcos Llorente~DF,Alex Baena~MF,Jose Maria Gimenez~DF
ESP_1|Villarreal CF|Logan Costa~DF,Tani Oluwaseyi~FW,Tajon Buchanan~FW,Nicolas Pepe~FW,Thomas Partey~MF,Renato Veiga~DF,Pape Gueye~MF,Alex Freeman~DF
GER_1|FC Augsburg|Michael Gregoritsch~FW,Kristijan Jakic~DF,Fabian Rieder~MF,Ismael Gharbi~MF
GER_1|SC Freiburg|Philipp Lienhart~DF,Igor Matanovic~FW,Yuito Suzuki~MF,Johan Manzambi~MF
GER_1|SV Werder Bremen|Romano Schmid~MF,Marco Friedl~DF,Yukinari Sugawara~DF
GER_1|1. FC Union Berlin|Rani Khedira~MF
GER_1|Hamburger SV|Luka Vuskovic~DF,Sander Tangvik~GK,Miro Muheim~DF
GER_1|FC Schalke 04|Edin Dzeko~FW,Nikola Katic~DF
GER_1|Borussia Mönchengladbach|Haris Tabakovic~FW,Jens Castrop~DF,Nico Elvedi~DF,Giovanni Reyna~MF,Joe Scally~DF
GER_1|RB Leipzig|Xaver Schlager~MF,Nicolas Seiwald~MF,Christoph Baumgartner~MF,Yan Diomande~FW,David Raum~DF,Assan Ouedraogo~MF,Antonio Nusa~FW
GER_1|1. FSV Mainz 05|Stefan Posch~DF,Phillip Mwene~DF,Nadiem Amiri~MF,Kaishu Sano~MF,Jaesung Lee~MF,Silvan Widmer~DF
GER_1|Eintracht Frankfurt|Fares Chaibi~MF,Arthur Theate~DF,Nathaniel Brown~DF,Ritsu Doan~MF,Ayoube Amaimouni~FW,Aurele Amenda~DF,Ellyes Skhiri~MF,Can Uzun~FW
ITA_1|Napoli|Kevin De Bruyne~MF,Romelu Lukaku~FW,Scott McTominay~MF,Mathias Olivera~DF
ITA_1|Parma|Alessandro Circati~DF,Zion Suzuki~GK
ITA_1|Sassuolo|Cristian Volpato~FW,Tarik Muharemovic~DF,Ismael Kone~MF,Kristian Thorstvedt~MF
ITA_1|Como|Nico Paz~FW,Martin Baturina~MF,Assane Diao~FW
ITA_1|Torino|Nikola Vlasic~MF,Marcus Holmgren Pedersen~DF,Che Adams~FW
ITA_1|Fiorentina|Marin Pongracic~DF
ITA_1|Cagliari|Yerry Mina~DF
ITA_1|Genoa|Johan Vasquez~DF,Leo Ostigard~DF
ITA_1|Udinese|Jesper Karlstrom~MF
ITA_1|Frosinone|Fares Ghedjemis~FW
ITA_1|Inter|Lautaro Martinez~FW,Ange-Yoan Bonny~FW,Petar Sucic~MF,Marcus Thuram~FW,Denzel Dumfries~DF,Manuel Akanji~DF,Hakan Calhanoglu~MF
ITA_1|Atalanta|Charles De Ketelaere~FW,Sead Kolasinac~DF,Ederson Silva~MF,Odilon Kossounou~DF,Mario Pasalic~MF,Kamaldeen Sulemana~FW,Marten De Roon~MF,Isak Hien~DF
ITA_1|Roma|Evan Ndicka~DF,Manu Kone~MF,Neil El Aynaoui~MF,Donyell Malen~FW,Zeki Celik~DF
ITA_1|Juventus|Bremer~DF,Jonathan David~FW,Teun Koopmeiners~MF,Francisco Conceicao~FW,Kenan Yildiz~FW,Weston McKennie~MF
ITA_1|Milan|Koni De Winter~DF,Alexis Saelemaekers~MF,Luka Modric~MF,Pervis Estupinan~DF,Adrien Rabiot~MF,Mike Maignan~GK,Santiago Gimenez~FW,Rafael Leao~FW,Ardon Jashari~MF,Christian Pulisic~FW
FRA_1|Olympique Lyonnais|Nicolas Tagliafico~DF,Endrick~FW,Pavel Sulc~FW,Ernest Nuamah~FW,Moussa Niakhate~DF
FRA_1|Paris FC|Samir Chergui~DF
FRA_1|Racing Club de Lens|Nidal Celik~DF,Arthur Masuaku~DF,Robin Risser~GK,Saud Abdulhamid~DF
FRA_1|Stade Rennais FC 1901|Brice Samba~GK,Alidu Seidu~DF,Mousa Altamari~FW,Breel Embolo~FW
FRA_1|AJ Auxerre|Gideon Mensah~DF,Elisha Owusu~MF,Marvin Senaya~DF,Josue Casimir~FW
FRA_1|FC Lorient|Bamba Dieng~FW,Yvon Mvogo~GK,Montassar Talbi~DF
FRA_1|Le Havre AC|Lionel Mpasi~GK,Ayumu Seko~DF,Mory Diaw~GK
FRA_1|Angers SCO|Carlens Arcus~DF
FRA_1|Toulouse FC|Mark McKenzie~DF
FRA_1|Paris Saint-Germain FC|Marquinhos~DF,Willian Pacho~DF,Ousmane Dembele~FW,Bradley Barcola~FW,Warren Zaire-Emery~MF,Desire Doue~FW,Lucas Hernandez~DF,Kangin Lee~MF,Achraf Hakimi~DF,Goncalo Ramos~FW,Joao Neves~MF,Vitinha~MF,Nuno Mendes~DF,Ibrahim Mbaye~FW,Fabian Ruiz~MF,Khalil Ayari~MF
FRA_1|AS Monaco FC|Simon Adingra~FW,Maghnes Akliouche~MF,Lamine Camara~MF,Krepin Diatta~DF,Denis Zakaria~MF,Folarin Balogun~FW
FRA_1|RC Strasbourg Alsace|Valentin Barco~MF,Mike Penders~GK,Diego Moreira~MF,Guela Doue~DF,Samir El Mourabet~MF,Gessime Yassine~MF,Julio Enciso~FW
'''

def key(s):
    normalized=''.join(ch for ch in unicodedata.normalize('NFKD',s.casefold()) if not unicodedata.combining(ch))
    return ''.join(ch for ch in normalized if ch.isalnum())

def read_initial_packs():
    from collections import defaultdict
    clubs={};players={}; name_to_club={};global_players={}
    for f in sorted((ROOT/'world_data'/'packs').glob('*.json')):
        for cid,lid,name,_,source,ps in parse_pack(f):
            clubs[(lid,name)]=cid
            name_to_club.setdefault((lid,key(name)), cid)
            for pid,_,pn,_,_,_,_ in ps:
                players.setdefault(cid,set()).add(key(pn))
                global_players.setdefault(key(pn),set()).add(cid)
    return clubs,players,global_players

def build():
    clubs,known_names,all_names=read_initial_packs()
    out=[];skipped=[]
    for row in DATA.strip().splitlines():
        lid,name,terms=row.split('|',2)
        cid=clubs.get((lid,name))
        if not cid:
            raise SystemExit('Club missing from catalog: '+lid+' '+name)
        new=[]
        for term in terms.split(','):
            pn,pos=term.strip().split('~')
            if key(pn) in known_names.get(cid,set()):
                skipped.append((lid,name,pn,'already at club'));continue
            if key(pn) in all_names and cid not in all_names[key(pn)]:
                skipped.append((lid,name,pn,'listed in another club in older snapshot'));continue
            if key(pn) in {key(x['name']) for x in new}:
                continue
            pid='v07:'+hashlib.sha256((lid+cid+key(pn)).encode()).hexdigest()[:20]
            new.append({'id':pid,'name':pn,'position':pos,'source':SOURCE})
            known_names.setdefault(cid,set()).add(key(pn));all_names.setdefault(key(pn),set()).add(cid)
        if new:
            out.append({'id':cid,'league_id':lid,'name':name,'source':SOURCE,'players':new})
    result={'format':'velton-offline-1','version':'v0.7-curated-wc2026','basis':'2026 national team tournament list (2026-09-10); partial club coverage','clubs':out}
    destination=ROOT/'world_data/packs/velton_verified_players_v07.json'
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    audit={'clubs_with_new_players':len(out),'new_player_records':sum(len(x['players']) for x in out),'skipped_known_or_disputed':skipped,'source':SOURCE}
    (ROOT/'world_data/verified_players_audit_v07.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'pack':str(destination),'clubs':len(out),'new_players':audit['new_player_records'],'skipped':len(skipped)},ensure_ascii=False))

if __name__=='__main__':build()
