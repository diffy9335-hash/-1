"""VELTON v0.6: manually transcribed, source-referenced real club identities.

Never guesses player names or creates invented clubs to reach an advertised quota.
For historical membership slices, the snapshot year is stored per club.
"""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_coverage_pack import canonical

# Confirmed same-club spelling variants across historical snapshots. Never
# merge youth/reserve clubs with their first team merely by similar names.
CLUB_ALIASES={
    'al ra ed':'al raed', 'al raed':'al raed',
    'js soualem':'js soualem', 'jeunesse sportive de soualem':'js soualem',
    'chabab mohammedia':'chabab mohammedia', 'sporting club chabab mohammedia':'chabab mohammedia',
    'olympique de safi':'olympique de safi', 'olympique club de safi':'olympique de safi',
    'chernomorets odessa':'chernomorets odessa', 'chornomorets odesa':'chernomorets odessa',
    'livyi bereh':'livyi bereh', 'livyi bereh kyiv':'livyi bereh',
    'chelyabinsk':'chelyabinsk', 'fc chelyabinsk':'chelyabinsk',
    'tekstilshchik':'tekstilshchik', 'tekstilshchik ivanovo':'tekstilshchik',
}

def club_key(name):
    key=canonical(name)
    return CLUB_ALIASES.get(key,key)

# league_id: (source season, public source URL, list of actual participating club names)
SOURCES = {
 'USA_2': ('2026','https://www.uslchampionship.com/about','''Birmingham Legion FC;Brooklyn FC;Charleston Battery;Colorado Springs Switchbacks FC;Detroit City FC;El Paso Locomotive FC;FC Tulsa;Hartford Athletic;Indy Eleven;Las Vegas Lights FC;Lexington SC;Loudoun United FC;Louisville City FC;Miami FC;Monterey Bay FC;New Mexico United;Oakland Roots SC;Orange County SC;Phoenix Rising FC;Pittsburgh Riverhounds SC;Rhode Island FC;Sacramento Republic FC;San Antonio FC;Sporting Club Jacksonville;Tampa Bay Rowdies'''),
 'GER_3': ('2025/26','https://github.com/openfootball/deutschland/blob/master/2025-26/3-liga3.txt','''Rot-Weiss Essen;TSV 1860 München;Waldhof Mannheim;SC Verl;FC Ingolstadt 04;Jahn Regensburg;VfL Osnabrück;Alemannia Aachen;Energie Cottbus;1. FC Saarbrücken;1899 Hoffenheim II;TSV Havelse;MSV Duisburg;VfB Stuttgart II;Erzgebirge Aue;Hansa Rostock;Viktoria Köln;1. FC Schweinfurt 05;SV Wehen Wiesbaden;SSV Ulm 1846'''),
 'SCO_2': ('2025/26','https://en.wikipedia.org/wiki/2025%E2%80%9326_Scottish_Championship','''Airdrieonians;Arbroath;Ayr United;Dunfermline Athletic;Greenock Morton;Partick Thistle;Queen's Park;Raith Rovers;Ross County;St Johnstone'''),
 'SCO_3': ('2025/26','https://clublogin.spfl.co.uk/league/league-one/archive/393','''Inverness Caledonian Thistle;Stenhousemuir;Queen of the South;Alloa Athletic;Peterhead;Montrose;Cove Rangers;East Fife;Hamilton Academical;Kelty Hearts'''),
 'JPN_2': ('2025','https://www.jleague.jp/en/j2/standings/2025/','''Mito Hollyhock;V-Varen Nagasaki;JEF United Chiba;Tokushima Vortis;Júbilo Iwata;RB Omiya Ardija;Vegalta Sendai;Sagan Tosu;Iwaki FC;Montedio Yamagata;FC Imabari;Hokkaido Consadole Sapporo;Ventforet Kofu;Blaublitz Akita;Fujieda MYFC;Oita Trinita;Kataller Toyama;Roasso Kumamoto;Renofa Yamaguchi FC;Ehime FC'''),
 'FRA_3': ('2025/26','https://www.fff.fr/article/15064-championnats-2025-2026-les-groupes.html','''AC Ajaccio;Aubagne Air Bel;Bourg-Péronnas;SM Caen;Châteauroux;Concarneau;Dijon FCO;FC Fleury 91;Le Puy Foot;US Orléans;Paris 13 Atletico;Quevilly-Rouen;FC Rouen 1899;FC Sochaux-Montbéliard;Stade Briochin;Valenciennes FC;FC Versailles 78;FC Villefranche Beaujolais'''),
 'BEL_2': ('2025/26 subset 15 of 17','https://www.transfermarkt.com/1b-pro-league/teilnehmer/pokalwettbewerb/BE2','''Jong Genk;KV Kortrijk;Beerschot VA;SK Beveren;KAS Eupen;RSCA Futures;Club NXT;Lommel SK;RWDM Brussels;Jong KAA Gent;Francs Borains;KSC Lokeren;Patro Eisden Maasmechelen;K Lierse SK;RFC Seraing'''),
 'ESP_3': ('2025/26','https://rfef.es/es/noticias/aprobados-los-grupos-de-primera-federacion-para-la-temporada-202526','''AD Mérida;Arenas Club;Athletic Club B;Barakaldo CF;CA Osasuna B;CD Arenteiro;CD Guadalajara;CD Lugo;CD Tenerife;CF Talavera de la Reina;CP Cacereño;Ourense CF;Pontevedra CF;Racing Club Ferrol;RC Celta Fortuna;Real Avilés Industrial;Real Madrid Castilla;SD Ponferradina;Unionistas de Salamanca CF;Zamora CF;AD Alcorcón;Algeciras CF;Atlético Sanluqueño CF;Antequera CF;Betis Deportivo Balompié;Club Atlético de Madrid B;CD Eldense;CD Teruel;CE Europa;CE Sabadell FC;FC Cartagena;Gimnàstic de Tarragona;Hércules CF;Juventud Torremolinos CF;Marbella FC;Real Murcia CF;SD Tarazona;Sevilla Atlético;UD Ibiza;Villarreal CF B'''),
 'ARG_2': ('2026','https://www.ambito.com/deportes/se-sorteo-la-primera-nacional-2026-asi-quedaron-conformadas-las-dos-zonas-los-36-equipos-n6227323','''All Boys;Ferro Carril Oeste;Deportivo Madryn;Chaco For Ever;Deportivo Morón;Estudiantes de Buenos Aires;Racing de Córdoba;Los Andes;Mitre de Santiago del Estero;Almirante Brown;Ciudad de Bolívar;Colón;Central Norte;Godoy Cruz;San Telmo;San Miguel;Defensores de Belgrano;Acassuso;Nueva Chicago;Chacarita Juniors;Atlanta;San Martín de Tucumán;Gimnasia de Jujuy;Almagro;San Martín de San Juan;Temperley;Güemes de Santiago del Estero;Tristán Suárez;Agropecuario;Patronato;Gimnasia y Tiro de Salta;Deportivo Maipú;Quilmes;Colegiales;Atlético de Rafaela;Ferrocarril Midland'''),
 'TUR_2': ('2025/26','https://www.tff.org/Default.aspx?hafta=36&pageID=1772','''Adana Demirspor;Iğdır FK;Amed SK;Çorum FK;Hatayspor;Pendikspor;Boluspor;Ümraniyespor;Ankara Keçiörengücü;Erzurumspor FK;Esenler Erokspor;Van Spor FK;İstanbulspor;Manisa FK;Sivasspor;Bandırmaspor;Sakaryaspor;Serikspor;Bodrum FK;Sarıyer'''),
 'CHN_2': ('2025','https://www.rsssf.org/tablesc/china2025.html','''Liaoning Tieren;Chongqing Tonglianglong;Guangdong Guangzhou Power;Yanbian Longding;Shijiazhuang Gongfu;Jiangxi Dingnan United;Nantong Zhiyun;Dalian K'un City;Shaanxi Union;Suzhou Dongwu;Nanjing City;Shanghai Jiading Huilong;Foshan Nanshi;Shenzhen Juniors;Guangxi Pingguo;Qingdao Red Lions'''),
 'CRO_2': ('2025/26','https://www.transfermarkt.nl/2-hnl/startseite/wettbewerb/KR2','''NK Rudeš;NK Dubrava Tim kabel;NK Sesvete;NK Dugopolje;HNK Orijent Rijeka;NK BSK Bijelo Brdo;HNK Cibalia Vinkovci;NK Karlovac 1919;NK Opatija;NK Jarun;NK Hrvace;NK Croatia Zmijavci'''),
 'SRB_2': ('2025/26','https://en.wikipedia.org/wiki/2025%E2%80%9326_Serbian_First_League','''Borac 1926;Dubočica;FAP;Jedinstvo Ub;Kabel Novi Sad;Loznica;Mačva Šabac;OFK Vršac;FK Smederevo;Dinamo Jug;Tekstilac Odžaci;Trayal Kruševac;RFK Grafičar;Ušće Novi Beograd;Voždovac;Zemun'''),
 'NED_3': ('2025/26','https://www.transfermarkt.com/tweede-divisie/startseite/wettbewerb/NTD/saison_id/2025','''Sparta Rotterdam U21;Almere City FC U23;Kozakken Boys Werkendam;VV IJsselmeervogels;VV Katwijk;RKAV Volendam;ACV Assen;AFC Amsterdam;BVV Barendrecht;Excelsior Maassluis;GVVV Veenendaal;Koninklijke HFC Haarlem;HHC Hardenberg;HSV Hoek;Rijnsburgse Boys;KVV Quick Boys Katwijk;SV Spakenburg;De Treffers'''),
 'EGY_2': ('2025/26','https://rsssf.org/tablese/egy2026.html','''El-Qanah Club;Asyut Petroleum;Abo Qir Semad;FC Masar;Proxy;La Viena;Telecom Egypt;El-Sekka El-Hadid;El-Mansoura;Maleyat Kafr El-Zayat;Tersana;El-Entag El-Harby;Al-Dakhleya;Dayrot;Tanta;Baladeyet Al-Mahalla;Aswan;Raya'''),
 'KSA_2': ('2025/26','https://www.rsssf.org/tabless/sau2026.html','''Abha;Al-Faisaly;Al-Diraiyah FC;Al-Ula;Al-Jabalain;Al-Raed;Al-Orobah;Al-Anwar;Al-Wehda;Al-Bukiryah;Al-Zulfi;Al-Tai;Al-Adalah;Al-Jandal;Al-Batin;Al-Arabi;Jeddah SC;Al-Jubail'''),
 'MAR_2': ('2026/27','https://lnfp.ma/','''Chabab Atlas Khénifra;Club Jeunesse Ben Guerir;Ittihad Zemmouri Khémisset;Jeunesse sportive Massira;Jeunesse Sportive de Soualem;Kénitra Athletic Club;Mouloudia Club d'Oujda;Olympique Club Khouribga;Olympique Club de Safi;Olympique Dcheira;Sporting Club Chabab Mohammédia;Stade Marocain;Union Sportive Bejaad;Union sportive musulmane d'Oujda;Union sportive Yacoub El Mansour;Wydad Athletic de Fès'''),
 'UKR_2': ('2025/26','https://www.rsssf.org/tableso/oekr2026.html','''Bukovyna Chernivtsi;Chornomorets Odesa;Livyi Bereh Kyiv;Ahrobiznes Volochysk;Inhulets Petrove;Prykarpattia Ivano-Frankivsk;Metalist Kharkiv;Probiy Horodenka;Phoenix Mariupol;Viktoriya Sumy;UCSA Tarasivka;Nyva Ternopil;FC Chernihiv;Vorskla Poltava;Podillia Khmelnytskyi;Metalurh Zaporizhzhia'''),
 'ITA_3': ('2025/26','https://www.lega-pro.com/com/2526-42L.pdf','''UC AlbinoLeffe;Team Altamura;SS Arezzo;Arzignano Valchiampo;Ascoli Calcio;Atalanta U23;Aurora Pro Patria;Benevento Calcio;AC Bra;Union Brescia;Campobasso FC;AC Carpi;Casarano Calcio;Casertana FC;Catania FC;Cavese 1919;Audace Cerignola;AS Cittadella;Cosenza Calcio;FC Crotone;Dolomiti Bellunesi;Calcio Foggia 1920;Forlì FC;AS Giana Erminio;Giugliano Calcio 1928;AS Gubbio 1910;Guidonia Montecelio 1937 FC;Inter U23;Juventus Next Gen;Latina Calcio 1932;Calcio Lecco 1912;US Livorno 1915;FC Lumezzane;Alcione Milano;SS Monopoli 1966;Novara FC;CPR Ospitaletto;US Pergolettese 1932;AC Perugia Calcio;Vis Pesaro 1898;US Pianese;AZ Picerno;Pineto Calcio;US Città di Pontedera;Potenza Calcio;Ravenna FC;AC Renate;Rimini FC;US Sambenedettese;US Salernitana 1919;Siracusa Calcio 1924;Sorrento Calcio 1945;Ternana Calcio;SEF Torres 1903;FC Trapani 1905;AC Trento;US Triestina;FC Pro Vercelli 1892;Virtus Verona;LR Vicenza'''),
 'BEL_3': ('2025/26','https://www.national-football-teams.com/app.php/leagues/20/2025/Belgium.html','''Crossing Schaerbeek;Excelsior Virton;RAEC Mons;RFC Meux;RRC Stockay-Warfusée;RSC Habay-la-Neuve;RU Tubize - Braine-le-Comte;SL 16 Liège;Union Rochefortoise;Union Saint-Gilloise U23;UR Namur;Zebra Elite Charleroi;Belisia Bilzen;Dessel Sport;Diegem Sport;Hoogstraten VV;Jong Cercle Brugge;KFC Merelbeke;Knokke FC;KVC Houtvenne;KVK Ninove;KVK Tienen;KVV Zelzate;Lyra-Lierse Berlaar;Oud-Heverlee Leuven U23;SK Roeselare;Sporting Hasselt;THES Sport Tessenderlo'''),
 'COL_2': ('2025','https://footballsoccerapi.com/our-football-api-data/colombia/primera-b/2025','''Jaguares de Córdoba;Patriotas Boyacá;Cúcuta Deportivo;Real Soacha Cundinamarca;Atlético Huila;Internacional Palmira;Real Cartagena;Tigres FC;Deportes Quindío;Boca Juniors de Cali;Real Santander;Orsomarso SC;Bogotá FC;Leones FC;Atlético FC;Barranquilla FC'''),
 'RUS_3': ('2024/25','https://www.rsssf.org/tablesr/rus2026.html','''Leningradets;Volgar Astrakhan;Kuban Krasnodar;Sibir Novosibirsk;FC Chelyabinsk;Veles Moscow;Spartak Kostroma;Tekstilshchik Ivanovo;FC Kaluga;Avangard Kursk;Krasnodar-2;Rodina-2 Moscow;FC Murom;Metallurg Lipetsk;Irtysh Omsk;Volga Ulyanovsk;Mashuk-KMV Pyatigorsk;Khimik Dzerzhinsk;Torpedo Miass;Dynamo Bryansk'''),
 'TUR_3': ('2025/26 subset 36/37','https://www.mus.gen.tr/spor/tff-2-ligde-gruplar-belli-oldu/','''Adana 01 FK;Altınordu;24 Erzincanspor;Batman Petrolspor;Beykoz Anadolu Spor;Beyoğlu Yeni Çarşı;Bucaspor 1928;Elazığspor;Kastamonuspor;İnegölspor;İskenderunspor;Karacabey Belediyespor;Karaman FK;Kepez Spor;Erbaaspor;MKE Ankaragücü;Muğlaspor;Ankaraspor;Şanlıurfaspor;68 Aksaray Belediyespor;Adanaspor;Aliağa FK;Ankara Demirspor;Arnavutköy Belediyespor;Belediye Derincespor;Bursaspor;Fethiyespor;Isparta 32 Spor;Kahramanmaraş İstiklalspor;1461 Trabzon FK;Kırklarelispor;Mardin 1969 Spor;Menemen FK;Muşspor;Somaspor;Yeni Mersin İdman Yurdu'''),
 'GRE_2': ('2025/26','https://www.rsssf.org/tablesg/grk2026.html','''Iraklis Thessaloniki;Niki Volou;Anagennisi Karditsas;Asteras Tripolis B;PAOK B Thessaloniki;AO Kavala;Nestos Chrysoupoli;Kampaniakos Chalastra;PAS Giannina;Makedonikos Neapoli;Kalamata;Panionios GSS;Marko Markopoulo;Olympiakos B Piraeus;Athens Kallithea FC;Hellas Syros;AO Aigaleo;GS Ilioupolis;AO Chania Kissamikos;Panargiakos APO'''),
 'POR_3': ('2025/26','https://www.transfermarkt.pt/liga-3/startseite/wettbewerb/PT3A/saison_id/2025','''Vitória SC B;SC Braga B;SU 1º Dezembro;CF Os Belenenses;União Santarém;Varzim SC;SC São João de Ver;SC Covilhã;Académica de Coimbra;Caldas SC;Amora FC;Amarante FC;AD Sanjoanense;CD Mafra;AD Marco 09;USC Paredes;CD Trofense;AD Fafe;Atlético CP;Lusitano GC'''),
}

def build():
    packs=[p for p in (ROOT/'world_data/packs').glob('*.json') if p.name != 'velton_verified_lower_leagues_v06.json']
    seen=set()
    for p in packs:
        for club in json.loads(p.read_text('utf-8'))['clubs']:
            seen.add((club['league_id'][:3],club_key(club['name'])))
    registry={r['league_id']:r['club_slots'] for r in json.loads((ROOT/'world_data/league_registry.json').read_text('utf-8'))['leagues']}
    clubs=[];skipped={};per={}
    for lid,(season,source,raw) in SOURCES.items():
        names=[n.strip() for n in raw.split(';') if n.strip()]
        assert len(names)<=registry[lid],(lid,len(names),registry[lid])
        per[lid]={'source':source,'season':season,'source_listed':len(names),'added':0}
        for name in names:
            key=(lid[:3],club_key(name))
            if key in seen:
                skipped.setdefault(lid,[]).append(name)
                continue
            seen.add(key)
            club_id='v06:'+hashlib.sha256(f'{lid}|{name}'.encode('utf-8')).hexdigest()[:18]
            clubs.append({'id':club_id,'league_id':lid,'name':name,'source':f'Real club; {season} participant snapshot; {source}','players':[]})
            per[lid]['added']+=1
    pack={'format':'velton-offline-1','season':'2025–2026 mixed snapshots',
       'description':'Sourced club identities from official league websites, FFF, SPFL, J.League, OpenFootball; no fabricated players; mixed season provenance, not a single contemporaneous roster.',
       'clubs':clubs}
    path=ROOT/'world_data/packs/velton_verified_lower_leagues_v06.json'
    path.write_text(json.dumps(pack,ensure_ascii=False,indent=2)+'\n','utf-8')
    audit={'added':len(clubs),'league_details':per,'not_imported_duplicate_with_existing_country':skipped}
    (ROOT/'world_data/verified_lower_leagues_audit_v06.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n','utf-8')
    return audit

if __name__=='__main__':
    print(json.dumps(build(),ensure_ascii=False,indent=2))
