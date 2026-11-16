"""Static 2026 World Cup squad snapshot (June 2026 club affiliation), no runtime network.

Names from ericsanmiguel/football_elo, data/squads/2026.csv (MIT).
Roster memberships may have changed since tournament kickoff: not a Nov 2026 live roster.
"""
from __future__ import annotations
import json,hashlib,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=json.loads((ROOT/'world_data/packs/velton_2026_27_starter.json').read_text('utf-8'))
MORE=json.loads((ROOT/'world_data/packs/velton_openfootball_coverage_v05.json').read_text('utf-8'))
ALL=BASE['clubs']+MORE['clubs']
CAT={(c['league_id'],c['name']):c for c in ALL}
SNAPSHOT_SOURCE='https://github.com/ericsanmiguel/football_elo/blob/main/data/squads/2026.csv'

# Real player names from 2026 tournament squads (not generated).
# @exact VELTON club key, not source alternate club name.
DATA=r'''
@ENG_1|Manchester City
Rayan Aït-Nouri;Jérémy Doku;Josko Gvardiol;Mateo Kovacic;Omar Marmoush;James Trafford;Nico O'Reilly;Marc Guéhi;John Stones;Rayan Cherki;Antoine Semenyo;Nathan Aké;Tijjani Reijnders;Erling Haaland;Rúben Dias
@GER_1|FC Bayern München
Konrad Laimer;Alphonso Davies;Luis Díaz;Josip Stanisic;Harry Kane;Dayot Upamecano;Michael Olise;Manuel Neuer;Jonathan Tah;Jamal Musiala;Aleksandar Pavlovic;Joshua Kimmich;Leon Goretzka;Hiroki Ito;Bara Sapoko Ndiaye
@ENG_1|Arsenal
Leandro Trossard;Gabriel;Gabriel Martinelli;Piero Hincapié;Declan Rice;Eberechi Eze;Bukayo Saka;Noni Madueke;William Saliba;Kai Havertz;Jurriën Timber;Martin Ødegaard;David Raya;Martín Zubimendi;Mikel Merino
@FRA_1|Paris Saint-Germain FC
Marquinhos;Willian Pacho;Lucas Hernández;Warren Zaïre-Emery;Désiré Doué;Ousmane Dembélé;Bradley Barcola;Achraf Hakimi;Nuno Mendes;João Neves;Vitinha;Gonçalo Ramos;Ibrahim Mbaye;Kang-in Lee;Fabián Ruiz
@ESP_1|FC Barcelona
Raphinha;Marcus Rashford;Jules Koundé;Frenkie de Jong;João Cancelo;Joan García;Pau Cubarsí;Eric García;Pedri;Dani Olmo;Gavi;Lamine Yamal;Ferran Torres;Ronald Araujo
@ESP_1|Atlético de Madrid
Juan Musso;Nahuel Molina;Julián Álvarez;Giuliano Simeone;Nico González;Thiago Almada;Obed Vargas;Alexander Sørloth;Marc Pubill;Marcos Llorente;Álex Baena;José María Giménez
@ENG_1|Crystal Palace
Daniel Muñoz;Jefferson Lerma;Dean Henderson;Maxence Lacroix;Jean-Philippe Mateta;Evann Guessand;Daichi Kamada;Chadi Riad;Jørgen Strand Larsen;Ismaïla Sarr;Yéremy Pino;Chris Richards
@KSA_1|Al Hilal
Theo Hernández;Yassine Bounou;Rúben Neves;Hassan Tambakti;Moteb Al-Harbi;Ali Lajami;Nasser Al-Dawsari;Mohamed Kanno;Salem Al-Dawsari;Sultan Mandash;Kalidou Koulibaly;Darwin Núñez
@GER_1|Borussia Dortmund
Ramy Bensebaini;Carney Chukwuemeka;Marcel Sabitzer;Nico Schlotterbeck;Waldemar Anton;Felix Nmecha;Maximilian Beier;Julian Ryerson;Daniel Svensson;Gregor Kobel;Salih Özcan
@ENG_1|Manchester United
Lisandro Martínez;Senne Lammens;Casemiro;Matheus Cunha;Kobbie Mainoo;Amad Diallo;Noussair Mazraoui;Diogo Dalot;Bruno Fernandes;Altay Bayındır;Manuel Ugarte
@ENG_1|Liverpool
Alexis Mac Allister;Alisson;Mohamed Salah;Ibrahima Konaté;Florian Wirtz;Wataru Endo;Virgil van Dijk;Ryan Gravenberch;Cody Gakpo;Andrew Robertson;Alexander Isak
@TUR_1|Galatasaray
Davinson Sánchez;Leroy Sané;Wilfried Singo;Noa Lang;Ismail Jakobs;Uğurcan Çakır;Abdülkerim Bardakcı;Eren Elmalı;Kaan Ayhan;Barış Alper Yılmaz;Yunus Akgün
@ESP_1|Real Madrid
David Alaba;Thibaut Courtois;Vinicius Junior;Jude Bellingham;Aurélien Tchouaméni;Kylian Mbappé;Antonio Rüdiger;Brahim Díaz;Arda Güler;Federico Valverde
@NED_1|PSV
Paul Wanner;Esmir Bajraktarevic;Ivan Perišić;Armando Obispo;Matej Kovar;Anass Salah-Eddine;Ismael Saibari;Guus Til;Sergiño Dest;Ricardo Pepi
@ITA_1|Milan
Koni De Winter;Alexis Saelemaekers;Luka Modrić;Pervis Estupiñán;Mike Maignan;Adrien Rabiot;Santiago Gimenez;Rafael Leão;Ardon Jashari;Christian Pulisic
@TUR_1|Fenerbahçe
Ederson;N'Golo Kanté;Edson Álvarez;Nélson Semedo;Mert Günok;Mert Müldür;Çağlar Söyüncü;İsmail Yüksek;Kerem Aktürkoğlu;Oğuz Aydın
@CZE_1|Slavia Praha
Jindrich Stanek;Stepan Chaloupek;David Zima;David Jurásek;Tomas Holes;Michal Sadílek;David Doudera;Lukas Provod;Mojmír Chytil;Tomas Chory
@KSA_1|Al Ahli SFC
Riyad Mahrez;Roger Ibañez;Ivan Toney;Franck Kessié;Ali Majrashi;Ziyad Al-Johani;Firas Al-Buraikan;Edouard Mendy;Merih Demiral
@ENG_1|Aston Villa
Emiliano Martínez;Amadou Onana;Youri Tielemans;Ezri Konsa;Morgan Rogers;Ollie Watkins;Lucas Digne;John McGinn;Victor Lindelöf
@BRA_1|CR Flamengo
Léo Pereira;Danilo;Alex Sandro;Lucas Paquetá;Jorge Carrascal;Gonzalo Plata;Guillermo Varela;Giorgian de Arrascaeta;Nicolás de la Cruz
@ENG_1|Sunderland
Noah Sadiki;Nilson Angulo;Wilson Isidor;Chemsdine Talbi;Robin Roefs;Brian Brobbey;Omar Alderete;Habib Diarra;Granit Xhaka
@EGY_1|Al Ahly SC
Oufa Shobeir;Mohamed El Shenawy;Mohamed Hany;Yasser Ibrahim;Emam Ashour;Marwan Ateya;Trezeguet;Zizo;Youssef Belammari
@KSA_1|Al Nassr
João Félix;Cristiano Ronaldo;Nawaf Al-Aqidi;Abdulelah Al-Amri;Nawaf Boushal;Ayman Yahya;Abdullah Al-Khaibari;Abdullah Al-Hamdan;Sadio Mané
@FRA_1|Lille OSC
Aïssa Mandi;Nabil Bentaleb;Nathan Ngoy;Thomas Meunier;Matias Fernandez-Pardo;Chancel Mbemba;Ngal'ayel Mukau;Ayyoub Bouaddi
@GER_1|Eintracht Frankfurt
Farès Chaïbi;Arthur Theate;Nathaniel Brown;Ritsu Doan;Ayoube Amaimouni-Echghouyab;Aurèle Amenda;Ellyes Skhiri;Can Uzun
@FRA_1|OGC Nice
Hicham Boudaoui;Moïse Bombito;Mohamed Abdelmonem;Kojo Peprah Oppong;Elye Wahi;Yehvann Diouf;Antoine Mendy;Ali Abdi
@ENG_1|Tottenham Hotspur
Cristian Romero;Kevin Danso;Djed Spence;Micky van de Ven;Pape Matar Sarr;Pedro Porro;Lucas Bergvall;Rodrigo Bentancur
@POR_1|Sport Lisboa e Benfica
Nicolás Otamendi;Dodi Lukébakio;Amar Dedić;Sidny Lopes Cabral;Richard Ríos;Fredrik Aursnes;Andreas Schjelderup;Tomás Araújo
@ENG_1|Chelsea
Enzo Fernández;Moisés Caicedo;Reece James;Malo Gusto;Jorrel Hato;Pedro Neto;Mamadou Sarr;Marc Cucurella
@GER_1|TSG Hoffenheim
Alexander Prass;Andrej Kramaric;Robin Hranac;Vladimír Coufal;Adam Hlozek;Oliver Baumann;Bazoumana Touré;Ozan Kabak
@ENG_1|Brighton & Hove Albion
Maxim De Cuyper;Pascal Groß;Bart Verbruggen;Jan Paul van Hecke;Mats Wieffer;Diego Gómez;Yasin Ayari;Ferdi Kadıoğlu
@GER_1|VfB Stuttgart
Ermedin Demirovic;Jeremy Arévalo;Alexander Nübel;Angelo Stiller;Jamie Leweling;Deniz Undav;Bilal El Khannouss;Luca Jaquez
@ENG_1|Newcastle United
Bruno Guimarães;Yoane Wissa;Tino Livramento;Dan Burn;Anthony Gordon;Malick Thiaw;Nick Woltemade;Anthony Elanga
@SCO_1|Celtic FC
Alistair Johnston;Daizen Maeda;Kieran Tierney;Anthony Ralston;Hyun-jun Yang;Benjamin Nygren;Sebastian Tounekti;Auston Trusty
@ESP_1|Villarreal CF
Tajon Buchanan;Tani Oluwaseyi;Logan Costa;Thomas Partey;Nicolas Pépé;Renato Veiga;Pape Gueye;Alex Freeman
@GER_1|Bayer 04 Leverkusen
Ibrahim Maza;Exequiel Palacios;Patrik Schick;Jarell Quansah;Mark Flekken;Alejandro Grimaldo;Malik Tillman
@FRA_1|Olympique de Marseille
Amine Gouiri;Gerónimo Rulli;Facundo Medina;Derek Cornelius;Nayef Aguerd;Quinten Timber;Timothy Weah
@FRA_1|RC Strasbourg Alsace
Valentín Barco;Mike Penders;Diego Moreira;Guéla Doué;Samir El Mourabet;Gessime Yassine;Julio Enciso
@ESP_1|Real Betis
Giovani Lo Celso;Cucho Hernández;Cédric Bakambu;Álvaro Fidalgo;Sofyan Amrabat;Abde Ezzalzouli;Ricardo Rodríguez
@ITA_1|Inter
Lautaro Martínez;Petar Sučić;Marcus Thuram;Ange-Yoan Bonny;Denzel Dumfries;Manuel Akanji;Hakan Çalhanoğlu
@POR_1|Sporting Clube de Portugal
Zeno Debast;Luis Suárez;Ousmane Diomande;Rui Silva;Gonçalo Inácio;Francisco Trincão;Maxi Araújo
@ITA_1|Atalanta
Charles De Ketelaere;Sead Kolasinac;Mario Pašalić;Kamaldeen Sulemana;Odilon Kossounou;Marten de Roon;Isak Hien
@GER_1|1. FSV Mainz 05
Stefan Posch;Phillipp Mwene;Nadiem Amiri;Kaishu Sano;Jae-sung Lee;Silvan Widmer
@GER_1|RB Leipzig
Nicolas Seiwald;Xaver Schlager;David Raum;Assan Ouédraogo;Yan Diomande;Antonio Nusa
@ENG_1|Fulham
Timothy Castagne;Raúl Jiménez;Issa Diop;Sander Berge;Oscar Bobb;Antonee Robinson
@ITA_1|Roma
Wesley;Manu Koné;Evan Ndicka;Neil El Aynaoui;Donyell Malen;Zeki Çelik
@ITA_1|Juventus
Bremer;Jonathan David;Teun Koopmeiners;Francisco Conceição;Kenan Yıldız;Weston McKennie
@FRA_1|AS Monaco FC
Maghnes Akliouche;Simon Adingra;Lamine Camara;Krépin Diatta;Denis Zakaria;Folarin Balogun
@BEL_1|Club Brugge KV
Joaquin Seys;Brandon Mechele;Hans Vanaken;Joel Ordóñez;Gustaf Nilsson
@SCO_1|Rangers FC
Nicolas Raskin;Thelo Aasgaard;Liam Kelly;John Souttar;Findlay Curtis
@GER_1|Borussia Mönchengladbach
Haris Tabakovic;Jens Castrop;Nico Elvedi;Joe Scally;Giovanni Reyna
@ENG_1|AFC Bournemouth
Rayan;Justin Kluivert;Ryan Christie;Ben Gannon-Doak;Tyler Adams
@ITA_1|Bologna
Jhon Lucumí;Nikola Moro;Torbjørn Heggem;Lewis Ferguson;Remo Freuler
@ESP_1|Real Sociedad
Duje Caleta-Car;Luka Sucic;Takefusa Kubo;Gonçalo Guedes;Mikel Oyarzabal
@EGY_1|Pyramids FC
Fiston Mayele;Karim Hafez;Mohanad Lasheen;Mostafa Ziko;Odeh Fakhoury
@ENG_1|Nottingham Forest
Elliot Anderson;Ibrahim Sangaré;Chris Wood;Angus Gunn;Dan Ndoye
'''

def norm(name):
    s=unicodedata.normalize('NFKD',name.casefold())
    return ''.join(c for c in s if not unicodedata.combining(c) and c.isalnum())

def build():
    used={norm(p['name']):c['name'] for c in ALL for p in c.get('players',[])}
    out=[]; conflicts=[];added=0
    target=None
    for line in DATA.splitlines():
        line=line.strip()
        if not line: continue
        if line.startswith('@'):
            lid,name=line[1:].split('|',1)
            target=CAT.get((lid,name))
            if target is None:raise ValueError(f'Unknown catalog club {lid}|{name}')
            continue
        item={'id':target['id'],'league_id':target['league_id'],'name':target['name'],
              'source':SNAPSHOT_SOURCE+' (MIT; 2026 World Cup kickoff roster; NOT current 2026/27)',
              'players':[]}
        for name in (x.strip() for x in line.split(';')):
            if not name: continue
            tag=norm(name)
            if tag in used:
                conflicts.append({'name':name,'existing_club':used[tag],'proposed_club':target['name']})
                continue
            used[tag]=target['name'];added+=1
            pid=hashlib.sha256((target['id']+'|'+tag).encode()).hexdigest()[:18]
            item['players'].append({'id':'wc2026:'+pid,'name':name,'source':SNAPSHOT_SOURCE+'; roster at tournament kickoff June 2026'})
        if item['players']:out.append(item)
    pack={'format':'velton-offline-1','season':'2026 World Cup kickoff snapshot',
          'description':'True names + historical club affiliation at June 2026 tournament, may differ Nov 2026. In-game ratings/wages are fictional.',
          'clubs':out}
    (ROOT/'world_data/packs/velton_wc_2026_players_v05.json').write_text(json.dumps(pack,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'world_data/wc2026_player_audit.json').write_text(json.dumps({'new_players':added,'existing_or_mismatched_names_skipped':conflicts},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return added,len(out),len(conflicts)
if __name__=='__main__':print('WC player addition (name-only historical memberships):',build())
