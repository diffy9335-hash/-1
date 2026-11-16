"""Reproducible, no-network VELTON club membership seed.

Source is an explicit collection of real club names transcribed from OpenFootball
CC0 match-file participant lists. It is NOT the user's 2026/27 verified list for
older seasons. Every line records its original source snapshot. No fake entrants.
"""
from __future__ import annotations
import hashlib, json, unicodedata
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
BASE=json.loads((HERE/'world_data/packs/velton_2026_27_starter.json').read_text('utf-8'))
REG=json.loads((HERE/'world_data/league_registry.json').read_text('utf-8'))
SLOTS={l['league_id']:l['club_slots'] for l in REG['leagues']}

# @LEAGUE|source-year|repository|path
# The names were extracted from the participant fields of these open-source fixtures.
DATA=r'''
@FRA_1|2026-27|football.json|2026-27/fr.1.json
AJ Auxerre;AS Monaco FC;Angers SCO;ES Troyes AC;FC Lorient;Le Havre AC;Le Mans FC;Lille OSC;OGC Nice;Olympique Lyonnais;Olympique de Marseille;Paris FC;Paris Saint-Germain FC;RC Strasbourg Alsace;Racing Club de Lens;Stade Brestois 29;Stade Rennais FC 1901;Toulouse FC
@NED_1|2026-27|football.json|2026-27/nl.1.json
ADO Den Haag;AFC Ajax;AZ;FC Groningen;FC Twente '65;FC Utrecht;Feyenoord Rotterdam;Fortuna Sittard;Go Ahead Eagles;NEC;PEC Zwolle;PSV;SBV Excelsior;SC Cambuur-Leeuwarden;SC Heerenveen;Sparta Rotterdam;Telstar 1963;Willem II Tilburg
@POR_1|2026-27|football.json|2026-27/pt.1.json
Académico de Viseu FC;CD Nacional;CD Santa Clara;CF Estrela da Amadora;CS Marítimo;Casa Pia AC;FC Alverca;FC Arouca;FC Famalicão;FC Porto;GD Estoril Praia;Gil Vicente FC;Moreirense FC;Rio Ave FC;Sport Lisboa e Benfica;Sporting Clube de Braga;Sporting Clube de Portugal;Vitória Guimarães
@BRA_1|2026|football.json|2026/br.1.json
Botafogo FR;CA Mineiro;CA Paranaense;CR Flamengo;CR Vasco da Gama;Chapecoense AF;Clube do Remo;Coritiba FBC;Cruzeiro EC;EC Bahia;EC Vitória;Fluminense FC;Grêmio FBPA;Mirassol FC;RB Bragantino;SC Corinthians Paulista;SC Internacional;SE Palmeiras;Santos FC;São Paulo FC
@ENG_3|2025-26|football.json|2025-26/en.3.json
AFC Wimbledon;Barnsley FC;Blackpool FC;Bolton Wanderers;Bradford City;Burton Albion;Cardiff City;Doncaster Rovers;Exeter City;Huddersfield Town;Leyton Orient;Lincoln City;Luton Town;Mansfield Town;Northampton Town;Peterborough United;Plymouth Argyle;Port Vale FC;Reading FC;Rotherham United;Stevenage FC;Stockport County;Wigan Athletic;Wycombe Wanderers
@ESP_2|2025-26|football.json|2025-26/es.2.json
AD Ceuta FC;Albacete;Burgos CF;CD Castellón;CD Leganés;CD Mirandés;Cultural Leonesa;Cádiz CF;Córdoba CF;Deportivo La Coruña;FC Andorra;Granada CF;Málaga CF;Racing Santander;Real Sociedad B;Real Valladolid;Real Zaragoza;SD Eibar;SD Huesca;Sporting Gijón;UD Almería;UD Las Palmas
@GER_2|2025-26|football.json|2025-26/de.2.json
1. FC Kaiserslautern;1. FC Magdeburg;1. FC Nürnberg;Arminia Bielefeld;Dynamo Dresden;Eintracht Braunschweig;FC Schalke 04;Fortuna Düsseldorf;Hannover 96;Hertha BSC;Holstein Kiel;Karlsruher SC;Preußen Münster;SC Paderborn 07;SV 07 Elversberg;SV Darmstadt 98;SpVgg Greuther Fürth;VfL Bochum
@ITA_2|2025-26|football.json|2025-26/it.2.json
AC Monza;AC Reggiana 1919;Calcio Padova;Carrarese Calcio;Cesena FC;Delfino Pescara;Empoli FC;FC Südtirol;Frosinone Calcio;Juve Stabia;Mantova 1911 SSD;Modena FC;Palermo FC;SSC Bari;Sampdoria;Spezia Calcio;US Avellino;US Catanzaro;Venezia FC;Virtus Entella
@FRA_2|2025-26|football.json|2025-26/fr.2.json
AS Nancy Lorraine;AS Saint-Étienne;Amiens SC;Clermont Foot 63;EA Guingamp;ESTAC Troyes;FC Annecy;Grenoble Foot 38;Le Mans FC;Montpellier HSC;Pau FC;Red Star FC;Rodez AF;SC Bastia;Stade Lavallois;Stade de Reims;US Boulogne;USL Dunkerque
@AUT_1|2025-26|football.json|2025-26/at.1.json
Austria Wien;FC Blau Weiß Linz;Grazer AK;LASK;RB Salzburg;Rapid Wien;SCR Altach;SV Ried;Sturm Graz;TSV Hartberg;WSG Tirol;Wolfsberger AC
@AUT_2|2025-26|football.json|2025-26/at.2.json
Austria Lustenau;Austria Salzburg;Austria Wien II;FC Admira Wacker;FC Hertha Wels;FC Liefering;First Vienna FC;Floridsdorfer AC;Kapfenberger SV 1919;Rapid Wien II;SK Austria Klagenfurt;SKN St. Pölten;SKU Amstetten;SV Stripfing/Weiden;Schwarz-Weiß Bregenz;Sturm Graz II
@BEL_1|2025-26|football.json|2025-26/be.1.json
Cercle Brugge;Club Brugge KV;FCV Dender EH;KAA Gent;KRC Genk;KV Mechelen;KVC Westerlo;Oud-Heverlee Leuven;RAAL La Louviére;RSC Anderlecht;Royal Antwerp FC;SV Zulte Waregem;Sint-Truidense VV;Sporting Charleroi;Standard Liège;Union Saint-Gilloise
@GRE_1|2025-26|football.json|2025-26/gr.1.json
AE Kifisias;AE Lárissa;AEK Athen;Aris Saloniki;Asteras Tripolis;Atromitos;Levadiakos;OFI Heraklion;Olympiakos Piraeus;PAOK Saloniki;Panathinaikos;Panetolikos;Panserraikos;Volos NFC
@SCO_1|2025-26|football.json|2025-26/sco.1.json
Aberdeen FC;Celtic FC;Dundee FC;Dundee United;Falkirk FC;Heart of Midlothian;Hibernian FC;Kilmarnock FC;Livingston FC;Motherwell FC;Rangers FC;St. Mirren FC
@TUR_1|2025-26|football.json|2025-26/tr.1.json
Alanyaspor;Antalyaspor;Beşiktaş;Eyüpspor;Fatih Karagümrük;Fenerbahçe;Galatasaray;Gaziantep FK;Gençlerbirliği;Göztepe;Kasımpaşa SK;Kayserispor;Kocaelispor;Konyaspor;Samsunspor;Trabzonspor;Çaykur Rizespor;İstanbul Başakşehir
@ARG_1|2025|football.json|2025/ar.1.json
Aldosivi;Argentinos Juniors;Atlético Tucumán;Banfield;Barracas Central;Belgrano de Córdoba;Boca Juniors;Central Córdoba SdE;Defensa y Justicia;Deportivo Riestra;Estudiantes;Gimnasia de La Plata;Godoy Cruz;Huracán;Independiente;Independiente Rivadavia;Instituto de Córdoba;Lanús;Newell's Old Boys;Platense;Racing Club;River Plate;Rosario Central;San Lorenzo;San Martín de San Juan;Sarmiento de Junín;Talleres de Córdoba;Tigre;Unión de Santa Fe;Vélez Sarsfield
@BRA_2|2025|football.json|2025/br.2.json
Amazonas FC AM;América MG;Athletic MG;Athletico Paranaense;Atlético Goianiense;Avaí SC;Botafogo SP;CR Brasil AL;Chapecoense;Coritiba PR;Criciúma SC;Cuiabá MT;Ferroviária SP;Goiás GO;Grêmio Novorizontino SP;Operário Ferroviário PR;Paysandu PA;Remo PA;Vila Nova GO;Volta Redonda RJ
@CHN_1|2025|football.json|2025/cn.1.json
Beijing Guoan;Changchun Yatai;Chengdu Rongcheng;Dalian Yingbo;Henan FC;Meizhou Hakka;Qingdao Hainiu;Qingdao West Coast;Shandong Taishan;Shanghai Port FC;Shanghai Shenhua;Shenzhen Peng City;Tianjin Jinmen Tiger;Wuhan Three Towns;Yunnan Yukun;Zhejiang Professional
@COL_1|2025|football.json|2025/co.1.json
Alianza FC;América de Cali;Atlético Bucaramanga;Atlético Junior;Atlético Nacional;Boyacá Chicó;Deportes Tolima;Deportivo Cali;Deportivo Pasto;Deportivo Pereira;Envigado FC;Fortaleza FC;Independiente Medellín;La Equidad;Llaneros FC;Millonarios;Once Caldas;Santa Fe;Unión Magdalena;Águilas Doradas
@JPN_1|2025|football.json|2025/jp.1.json
Albirex Niigata;Avispa Fukuoka;Cerezo Osaka;FC Machida Zelvia;FC Tokyo;Fagiano Okayama;Gamba Osaka;Kashima Antlers;Kashiwa Reysol;Kawasaki Frontale;Kyoto Sanga FC;Nagoya Grampus;Sanfrecce Hiroshima;Shimizu S-Pulse;Shonan Bellmare;Tokyo Verdy;Urawa Red Diamonds;Vissel Kobe;Yokohama F. Marinos;Yokohama FC
@USA_1|2025|football.json|2025/mls.json
Atlanta United FC;Austin FC;CF Montréal;Charlotte FC;Chicago Fire;Colorado Rapids;Columbus Crew;D.C. United;FC Cincinnati;FC Dallas;Houston Dynamo;Inter Miami CF;Los Angeles FC;Los Angeles Galaxy;Minnesota United FC;Nashville SC;New England Revolution;New York City FC;New York RB;Orlando City;Philadelphia Union;Portland Timbers;Real Salt Lake;San Diego FC;San Jose Earthquakes;Seattle Sounders;Sporting Kansas City;St. Louis City SC;Toronto FC;Vancouver Whitecaps
@EGY_1|2024-25|football.json|2024-25/eg.1.json
Al Ahly SC;Al Masry Club;Ceramica Cleopatra;ENPPI;El Gouna;Future FC;Ghazl Al Mehalla;Haras El Hodood;Ismaily;Ittihad El Iskandary;National Bank SC;PetroJet FC;Pharco FC;Pyramids FC;Smouha Sporting Club;Tala'ea El Gaish SC;ZED FC;Zamalek
@MAR_1|2024-25|football.json|2024-25/ma.1.json
COD Meknés;CR Khemis Zemamra;Chabab Mohammédia;Difaâ d'el Jadida;FAR de Rabat;FUS de Rabat;Hassania US Agadir;Ittihad Tanger;JS Soualem;Maghrib de Fès;Moghreb de Tétouan;Olympique de Safi;RS Berkane;Raja Casablanca;Union de Touarga;Wydad AC
@MEX_1|2024-25|football.json|2024-25/mx.1.json
Atlas Guadalajara;Atlético San Luis;CF América;CF Monterrey;CF Pachuca;Club León;Club Necaxa;Club Tijuana;Cruz Azul;Deportivo Guadalajara;Deportivo Toluca;FC Juárez;Gallos Blancos;Mazatlán FC;Puebla FC;Pumas UNAM;Santos Laguna;UANL Tigres
'''
DATA+=r'''
@CZE_1|2026-27|europe|czech-republic/2026-27_cz1.txt
1.FC Slovácko;Artis Brno;Baník Ostrava;Bohemians 1905;FC Fastav Zlín;FK Jablonec;FK Mlada Boleslav;FK Pardubice;FK Teplice;Hradec Kralove;Sigma Olomouc;Slavia Praha;Slovan Liberec;Sparta Praha;Viktoria Plzeň;Zbrojovka Brno
@CZE_2|2024-25|europe|czech-republic/2024-25_cz2.txt
1. SK Prostějov;AC Sparta Praha B;Baník Ostrava B;FC Sellier & Bellot Vlašim;FC Zlín;FK MAS Táborsko;FK Varnsdorf;MFK Chrudim;MFK Vyškov;SFC Opava;SK Líšeň;Sigma Olomouc B;Slavia Praha B;Viktoria Žižkov;Vysočina Jihlava;Zbrojovka Brno
@DEN_1|2024-25|europe|denmark/2024-25_dk1.txt
Aalborg BK;Aarhus GF;Brøndby IF;FC København;FC Midtjylland;FC Nordsjælland;Lyngby BK;Randers FC;Silkeborg IF;SønderjyskE;Vejle BK;Viborg FF
@DEN_2|2024-25|europe|denmark/2024-25_dk2.txt
AC Horsens;B.93 København;Esbjerg fB;FC Fredericia;FC Roskilde;HB Køge;Hillerød GI;Hobro IK;Hvidovre IF;Kolding IF;Odense BK;Vendsyssel FF
@NOR_1|2025|europe|norway/2025_no1.txt
Bryne FK;FK Bodø/Glimt;FK Haugesund;Fredrikstad FK;Hamarkameratene;KFUM Oslo;Kristiansund BK;Molde FK;Rosenborg BK;SK Brann;Sandefjord Fotball;Sarpsborg 08;Strømsgodset IF;Tromsø IL;Viking FK;Vålerenga IF
@NOR_2|2025|europe|norway/2025_no2.txt
Aalesunds FK;Egersunds IK;IK Start;IL Hødd;Kongsvinger IL;Lillestrøm SK;Lyn Oslo;Mjøndalen IF;Moss FK;Odds BK;Ranheim IL;Raufoss IL;Skeid Fotball;Sogndal IL;Stabæk IF;Åsane Fotball
@POL_1|2024-25|europe|poland/2024-25_pl1.txt
FKS Stal Mielec;GKS Katowice;Górnik Zabrze;Jagiellonia Białystok;KS Cracovia;Korona Kielce;Lech Poznań;Lechia Gdańsk;Legia Warszawa;Motor Lublin;Piast Gliwice;Pogoń Szczecin;Puszcza Niepołomice;Radomiak Radom;Raków Częstochowa;Widzew Łódź;Zagłębie Lubin;Śląsk Wrocław
@POL_2|2024-25|europe|poland/2024-25_pl2.txt
Arka Gdynia;Bruk-Bet Termalica Nieciecza;Chrobry Głogów;GKS Tychy '71;Górnik Łęczna;Kotwica Kołobrzeg;Miedź Legnica;Odra Opole;Pogoń Siedlce;Polonia Warszawa;Ruch Chorzów;Stal Rzeszow;Stal Stalowa Wola;Warta Poznań;Wisła Kraków;Wisła Płock;Znicz Pruszków;ŁKS Łódź
@SWE_1|2025|europe|sweden/2025_se1.txt
AIK Solna;BK Häcken;Degerfors IF;Djurgårdens IF;GAIS Göteborg;Halmstads BK;Hammarby IF;IF Brommapojkarna;IF Elfsborg;IFK Göteborg;IFK Norrköping;IFK Värnamo;IK Sirius;Malmö FF;Mjällby AIF;Östers IF
@SWE_2|2025|europe|sweden/2025_se2.txt
Falkenbergs FF;GIF Sundsvall;Helsingborgs IF;IK Brage;IK Oddevold;Kalmar FF;Landskrona BoIS;Sandvikens IF;Trelleborgs FF;Umeå FC;Utsiktens BK;Varbergs BoIS;Västerås SK;Örebro SK;Örgryte IS;Östersunds FK
@SUI_1|2026-27|europe|switzerland/2026-27_ch1.txt
FC Basel;FC Lausanne-Sport;FC Luzern;FC Sankt Gallen;FC Sion;FC Thun;FC Vaduz;FC Zürich;Grasshoppers;Lugano;Servette FC;Young Boys
@SUI_2|2024-25|europe|switzerland/2024-25_ch2.txt
AC Bellinzona;Etoile Carouge FC;FC Aarau;FC Schaffhausen;FC Stade Nyonnais;FC Thun Berner Oberland;FC Vaduz;FC Wil 1900;Neuchâtel Xamax FCS;Stade Lausanne-Ouchy
@CRO_1|2024-25|europe|croatia/2024-25_hr1.txt
Dinamo Zagreb;HNK Gorica;HNK Rijeka;HNK Šibenik;Hajduk Split;Lokomotiva Zagreb;NK Istra 1961;NK Osijek;NK Varaždin;Slaven Belupo
@SRB_1|2026-27|verified|
Crvena Zvezda;FK Novi Pazar;FK Radnički 1923;FK Čukarički;IMT Beograd;Mladost Lučani;OFK Beograd;Partizan;Radnički Niš;Vojvodina;Železničar Pančevo;FK Radnik Surdulica;FK Mačva;FK Zemun
@UKR_1|2024-25|europe|ukraine/2024-25_ua1.txt
Chernomorets Odessa;Dinamo Kiev;FC LNZ Cherkasy;FK Obolon;FK Oleksandriya;Inhulets Petrove;Karpaty Lviv;Kolos Kovalivka;Kryvbas Kryvyi Rih;Livyi Bereh;NK Veres;Polissya Zhytomyr;Rukh Lviv;Shakhtar Donetsk;Vorskla Poltava;Zorya Lugansk
@RUS_1|2024-25|europe|russia/2024-25_ru1.txt
Akhmat Grozny;Akron Tolyatti;CSKA Moskva;Dinamo Moskva;FK Dinamo Makhachkala;FK Khimki;FK Krasnodar;FK Nizhny Novgorod;FK Orenburg;FK Rostov;Fakel Voronezh;Krylia Sovetov;Lokomotiv Moskva;Rubin Kazan;Spartak Moskva;Zenit St. Petersburg
@NED_2|2024-25|europe|netherlands/2024-25_nl2.txt
ADO Den Haag;AZ Alkmaar J;De Graafschap;FC Den Bosch;FC Dordrecht;FC Eindhoven;FC Emmen;FC Utrecht J;FC Volendam;Helmond Sport;Jong Ajax;Jong PSV;MVV;Roda JC Kerkrade;SBV Excelsior;SC Cambuur;TOP Oss;Telstar;VVV-Venlo;Vitesse
@POR_2|2024-25|europe|portugal/2024-25_pt2.txt
Académico de Viseu;CD Feirense;CD Mafra;CD Tondela;CS Marítimo;FC Alverca;FC Felgueiras 1932;FC Penafiel;FC Porto B;FC Vizela;GD Chaves;Leixões SC;Paços de Ferreira;Portimonense SC;SL Benfica B;UD Oliveirense;União Leiria;União Torreense
@KSA_1|2024-25|world|middle-east/saudi-arabia/2024-25_sa1.txt
Al Ahli SFC;Al Ettifaq;Al Fateh;Al Fayha;Al Hilal;Al Ittihad;Al Khaleej;Al Kholood;Al Nassr;Al Okhdood;Al Orobah;Al Qadsiah;Al Ra'ed;Al Riyadh;Al Shabab;Al Taawoun;Al Wehda;Damac FC
'''

# Verified 2026 league membership (not scraped at game runtime).
DATA += r'''
@URU_1|2026|verified-uru|
Albion;Boston River;Central Español;Cerro;Cerro Largo;Danubio;Defensor Sporting;Deportivo Maldonado;Juventud;Liverpool;Montevideo City Torque;Montevideo Wanderers;Nacional;Peñarol;Progreso;Racing
@CHI_1|2026|verified-chi|
Audax Italiano;Cobresal;Colo Colo;Coquimbo Unido;Deportes Concepción;Deportes La Serena;Deportes Limache;Everton;Huachipato;Ñublense;O'Higgins;Palestino;Unión La Calera;Universidad Católica;Universidad de Chile;Universidad de Concepción
@KOR_1|2026|verified-kor|
Jeonbuk Hyundai Motors;Daejeon Hana Citizen;Gimcheon Sangmu FC;Pohang Steelers;FC Seoul;Gangwon FC;Gwangju FC;Ulsan HD FC;Jeju SK FC;FC Anyang;Incheon United;Bucheon FC 1995
'''

# Verified second divisions from 2026 national league lists / federation standings.
DATA += r'''
@URU_2|2026|verified-uru2|
Atenas de San Carlos;Cerrito;Colón;Fénix;Huracán;La Luz;Miramar Misiones;Oriental;Paysandú;Plaza Colonia;Rentistas;River Plate;Tacuarembó;Uruguay Montevideo
@KOR_2|2026|verified-kor2|
Ansan Greeners;Busan IPark;Cheonan City;Chungbuk Cheongju;Chungnam Asan;Daegu FC;Gimpo FC;Gimhae FC 2008;Gyeongnam FC;Hwaseong FC;Jeonnam Dragons;Paju Frontier;Seongnam FC;Seoul E-Land;Suwon Samsung Bluewings;Suwon FC;Yongin FC
@CHI_2|2026|verified-chi2|
Cobreloa;San Luis de Quillota;Santiago Wanderers;Deportes Antofagasta;Magallanes;San Marcos de Arica;Deportes Recoleta;Deportes Copiapó;Unión Española;Deportes Iquique;Deportes Puerto Montt;Deportes Temuco;Curicó Unido;Deportes Santa Cruz;Unión San Felipe;Rangers de Talca
@RUS_2|2026-27|verified-rus2|
Nizhny Novgorod;Ural Yekaterinburg;Sochi;Torpedo Moscow;Veles Moscow;Spartak Kostroma;Shinnik Yaroslavl;Volga Ulyanovsk;Ufa;Rotor Volgograd;Chelyabinsk;Arsenal Tula;Leningradets;Yenisey Krasnoyarsk;SKA-Khabarovsk;KAMAZ;Neftekhimik;Tekstilshchik
'''

REPO={'football.json':'https://github.com/openfootball/football.json/blob/master/',
      'europe':'https://github.com/openfootball/europe/blob/master/',
      'world':'https://github.com/openfootball/world/blob/master/',
      'verified':'https://www.globalscorex.com/football/league/serbian-superliga',
      'verified-uru':'https://www.montevideo.com.uy/Deportes/Se-sorteo-la-Copa-AUF-Uruguay-2026-mira-como-quedaron-conformados-los-seis-grupos-uc971527',
      'verified-chi':'https://www.emol.com/especiales/2026/deportes/liga-de-primera/equipos.asp',
      'verified-kor':'https://en.wikipedia.org/wiki/2026_K_League_1',
      'verified-uru2':'https://auf.org.uy/se-sorteo-el-fixture-de-la-segunda-division-profesional-2026/',
      'verified-kor2':'https://en.wikipedia.org/wiki/2026_K_League_2',
      'verified-chi2':'https://chile.as.com/futbol/tabla-de-posiciones-de-la-primera-b-tras-nuevo-fallo-de-san-marcos-y-programacion-de-la-fecha-30-f202611-n/',
      'verified-rus2':'https://sportalic.com/tables/russia/first-league'}
# Specific historical aliases of clubs that moved a division. Keep reserve clubs distinct.
ALIAS={
  'estac troyes':'es troyes ac','fc thun berner oberland':'fc thun',
  'fc vaduz':'fc vaduz','fc zlín':'fc fastav zlín',
  'academico de viseu':'academico de viseu fc',
  'racing santander':'real racing club de santander',
  'deportivo la coruna':'rc deportivo la coruna',
  'malaga cf':'malaga cf',
  'fc schalke 04':'fc schalke 04',
  'sv 07 elversberg':'sv elversberg',
  'sc paderborn 07':'sc paderborn 07',
  'frosinone calcio':'frosinone',
  'ac monza':'ac monza',
  'venezia fc':'venezia fc',
  'chapecoense':'chapecoense af',
  'coritiba pr':'coritiba fbc',
  'remo pa':'clube do remo',
  'athletico paranaense':'ca paranaense',
  'ado den haag':'ado den haag',
  'telstar':'telstar 1963',
  'sc cambuur':'sc cambuur-leeuwarden',
  'sbv excelsior':'sbv excelsior',
  'zbrojovka brno':'zbrojovka brno',
  'fc thun':'fc thun',
  'raala la louviere':'raal la louviere',
  'nizhny novgorod':'fk nizhny novgorod'
}

def canonical(name:str)->str:
    n=unicodedata.normalize('NFKD',name)
    n=''.join(x for x in n if not unicodedata.combining(x))
    n=n.replace('ø','o').replace('Ø','o').replace('ł','l').replace('Ł','l').casefold()
    n=''.join(c if c.isalnum() else ' ' for c in n)
    n=' '.join(n.split())
    return ALIAS.get(n,n)

def parse_source():
    rows=[]
    current=None
    for raw in DATA.splitlines():
        line=raw.strip()
        if not line: continue
        if line.startswith('@'):
            pieces=line[1:].split('|')
            if len(pieces)!=4:raise ValueError('Bad source '+line)
            current=pieces
            if current[0] not in SLOTS:raise ValueError('Unknown league '+current[0])
        else:
            if not current:raise ValueError('Team list lacks header')
            for name in (x.strip() for x in line.split(';')):
                if name:rows.append((*current,name))
    return rows

def build():
    # In case of older seasons, the 2026/27 confirmed top-league list wins.
    existing={(lid[:3], canonical(c['name'])) for c in BASE['clubs'] for lid in [c['league_id']]}
    seen=set(existing)
    new=[]
    audit={}
    for lid,season,repo,path,name in parse_source():
        key=(lid[:3],canonical(name))
        info=audit.setdefault(lid,{'source':REPO[repo]+path,'season':season,'listed':0,'added':0,'excluded_older_or_duplicate':[]})
        info['listed']+=1
        if key in seen:
            info['excluded_older_or_duplicate'].append(name)
            continue
        # Some 2025/26 2nd-division snapshots include clubs that moved to
        # the already-imported 2026/27 top division. Do not place them twice.
        seen.add(key)
        digest=hashlib.sha256(f'{lid}|{name}'.encode()).hexdigest()[:16]
        new.append({'id':f'openfootball:{digest}','league_id':lid,'name':name,
          'source':f'OpenFootball CC0 team listing; snapshot {season}; {REPO[repo]+path}',
          'players':[]})
        info['added']+=1
    result={'format':'velton-offline-1','season':'mixed (2024/25–2026/27)',
      'description':'Real club identities from OpenFootball CC0. Mixed historical membership snapshots; NOT universally current 2026/27 and no players invented.',
      'clubs':new}
    out=HERE/'world_data/packs/velton_openfootball_coverage_v05.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (HERE/'world_data/coverage_manifest.json').write_text(json.dumps({
      'caveat':'Historical seasons can lack 2026/27 promoted/relegated clubs; do not treat as current squads.',
      'sources':audit,'new_clubs':len(new),'league_source_count':len(audit)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return len(new),len(audit)

if __name__=='__main__':print('Created CC0 sourced pack:',build())
