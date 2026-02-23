import pandas as pd
import os
import google.generativeai as genai
import sys
import re
import numpy as np

# ==============================================================================
# 1. CONFIGURACIÓN ESPECIAL LIGA ENDESA (ACB)
# ==============================================================================
MODEL_NAME = "gemini-2.5-flash"
FILE_PATH = "data/BoxScore_ACB_2025_Cumulative.csv"

# Mapa de Equipos (Los 18 de la Liga Endesa)
TEAM_MAP = {
    'UNI': 'Unicaja', 'SBB': 'Bilbao Basket', 'BUR': 'San Pablo Burgos', 'GIR': 'Bàsquet Girona',
    'TEN': 'La Laguna Tenerife', 'MAN': 'BAXI Manresa', 'LLE': 'Hiopos Lleida', 'BRE': 'Río Breogán',
    'COV': 'Covirán Granada', 'JOV': 'Joventut Badalona', 'RMB': 'Real Madrid', 'GCA': 'Dreamland Gran Canaria',
    'CAZ': 'Casademont Zaragoza', 'BKN': 'Baskonia', 'UCM': 'UCAM Murcia', 'MBA': 'MoraBanc Andorra',
    'VBC': 'Valencia Basket', 'BAR': 'Barça'
}

# Mapa de Entrenadores (Temporada 2025/2026 - ACTUALIZADO OFICIAL)
COACH_MAP = {
    'BAR': 'Xavi Pascual', 'RMB': 'Sergio Scariolo', 'UNI': 'Ibon Navarro',
    'BKN': 'Paolo Galbiati', 'VBC': 'Pedro Martínez', 'UCM': 'Sito Alonso',
    'GCA': 'Jaka Lakovic', 'TEN': 'Txus Vidorreta', 'JOV': 'Dani Miret',
    'MAN': 'Diego Ocampo', 'SBB': 'Jaume Ponsarnau', 'CAZ': 'Joan Plaza',
    'GIR': 'Moncho Fernández', 'BRE': 'Luis Casimiro', 'LLE': 'Gerard Encuentra',
    'COV': 'Arturo Ruíz', 'MBA': 'Zan Tabak', 'BUR': 'Porfi Fisac'
}

# ==============================================================================
# 2. DICCIONARIO MAESTRO DE JUGADORES (ACB)
# ==============================================================================
CORRECCIONES_VIP = {
    # --- BARÇA (BAR) ---
    "D. Brizuela": "Darío Brizuela", "D. González": "Dani González", "J. Marcos": "Juani Marcos", "J. Parra": "Joel Parra", "J. Vesely": "Jan Vesely", "K. Punter": "Kevin Punter", "M. Cale": "Myles Cale", "M. Norris": "Miles Norris", "N. Kusturica": "Nikola Kusturica", "N. Laprovittola": "Nico Laprovittola", "S. Keita": "Sayon Keita", "T. Satoransky": "Tomas Satoransky", "T. Shengelia": "Toko Shengelia", "W. Clyburn": "Will Clyburn", "W. Hernangómez": "Willy Hernangómez", "Y. Fall": "Youssoupha Fall",
    # --- BASKONIA (BKN) ---
    "C. Frisch": "Clément Frisch", "E. Omoruyi": "Eugene Omoruyi", "G. Radzevicius": "Gytis Radzevicius", "H. Diallo": "Hamidou Diallo", "K. Diop": "Khalifa Diop", "K. Simmons": "Kobi Simmons", "L. Samanic": "Luka Samanic", "Luwawu-Cabarrot": "Timothé Luwawu-Cabarrot", "M. Diakite": "Mamadi Diakite", "M. Howard": "Markus Howard", "M. Nowell": "Markquis Nowell", "M. Spagnolo": "Matteo Spagnolo", "R. Kurucs": "Rodions Kurucs", "R. Villar": "Rafa Villar", "S. Joksimovic": "Stefan Joksimovic", "T. Forrest": "Trent Forrest", "T. Sedekerskis": "Tadas Sedekerskis",
    # --- RÍO BREOGÁN (BRE) ---
    "A. Aranitovic": "Aleksandar Aranitovic", "A. Kurucs": "Arturs Kurucs", "B. Dibba": "Bamba Dibba", "D. Apic": "Dragan Apic", "D. Brankovic": "Danko Brankovic", "D. Drežnjak": "Dario Drežnjak", "D. Mavra": "Dominik Mavra", "D. Russell": "Daron Russell", "E. Quintela": "Erik Quintela", "F. Alonso": "Francis Alonso", "J. Sakho": "Jordan Sakho", "K. Cook": "Keaton Cook", "M. Andric": "Mihajlo Andric",
    # --- SAN PABLO BURGOS (BUR) ---
    "D. Díez": "Dani Díez", "E. Happ": "Ethan Happ", "G. Corbalán": "Gonzalo Corbalán", "J. Gudmundsson": "Jon Axel Gudmundsson", "J. Jackson": "Justin Jackson", "J. Rubio": "Joan Rubio", "J. Samuels": "Jermaine Samuels", "L. Fischer": "Luke Fischer", "L. Meindl": "Leo Meindl", "P. Almazán": "Pablo Almazán", "R. Neto": "Raulzinho Neto", "R. Rodríguez": "Rodrigo Rodríguez", "S. García": "Sergi García", "S. de Sousa": "Silvio de Sousa", "Y. Nzosa": "Yannick Nzosa",
    # --- CASADEMONT ZARAGOZA (CAZ) ---
    "B. Dubljevic": "Bojan Dubljevic", "C. Alías": "Carlos Alías", "C. Koumadje": "Christ Koumadje", "D. Robinson": "Devin Robinson", "D. Stephens": "D.J. Stephens", "E. Kabaca": "Emir Kabaca", "E. Stevenson": "Erik Stevenson", "J. Fernández": "Jaime Fernández", "J. Rodríguez": "Joaquín Rodríguez", "J. Soriano": "Joel Soriano", "L. Langarita": "Lucas Langarita", "M. González": "Miguel González", "M. Lukic": "Matija Lukic", "M. Spissu": "Marco Spissu", "S. Yusta": "Santi Yusta", "T. Bell-Haynes": "Trae Bell-Haynes", "Y. Traoré": "Youssouf Traoré",
    # --- COVIRÁN GRANADA (COV) ---
    "A. Alibegovic": "Amar Alibegovic", "A. Brimah": "Amida Brimah", "B. Burjanadze": "Beka Burjanadze", "B. Olumuyiwa": "Babatunde Olumuyiwa", "E. Durán": "Edu Durán", "E. Valtonen": "Elias Valtonen", "I. Aurrecoechea": "Iván Aurrecoechea", "J. Kljajic": "Jovan Kljajic", "J. Pérez": "Josep Pérez", "J. Rousselle": "Jonathan Rousselle", "L. Bozic": "Luka Bozic", "L. Costa": "Lluís Costa", "M. Ngouama": "Mehdy Ngouama", "M. Speight": "Micah Speight", "M. Thomas": "Malcolm Thomas", "O. Cerdá": "Osi Cerdá", "P. Tomàs": "Pere Tomàs", "T. Munnings": "Travis Munnings", "W. Howard": "William Howard", "Z. Hankins": "Zach Hankins",
    # --- DREAMLAND GRAN CANARIA (GCA) ---
    "A. Albicy": "Andrew Albicy", "B. Angola": "Braian Angola", "C. Alocén": "Carlos Alocén", "E. Vila": "Eric Vila", "I. Wong": "Isaiah Wong", "K. Kuath": "Kur Kuath", "L. Labeyrie": "Louis Labeyrie", "L. Maniema": "Lucas Maniema", "M. Salvó": "Miquel Salvó", "M. Tobey": "Mike Tobey", "N. Brussino": "Nico Brussino", "P. Pelos": "Pierre Pelos", "Z. Samar": "Ziga Samar",
    # --- BÀSQUET GIRONA (GIR) ---
    "D. Needham": "Derek Needham", "G. Ferrando": "Guillem Ferrando", "J. Fernández": "Juan Fernández", "M. Fjellerup": "Máximo Fjellerup", "M. Geben": "Martinas Geben", "M. Hughes": "Michael Hughes", "M. Susinskas": "Mindaugas Susinskas", "N. Maric": "Nikola Maric", "O. Livingston": "Otis Livingston", "P. Busquets": "Pep Busquets", "P. Vildoza": "Pato Vildoza", "S. Hollanders": "Sander Hollanders", "S. Martínez": "Sergi Martínez",
    # --- JOVENTUT BADALONA (JOV) ---
    "A. Hanga": "Adam Hanga", "A. Tomic": "Ante Tomic", "A. Torres": "Adrià Torres", "C. Hunt": "Cameron Hunt", "F. Mauri": "Ferran Mauri", "G. Vives": "Guillem Vives", "H. Drell": "Henri Drell", "L. Hakanson": "Ludde Hakanson", "M. Allen": "Miguel Allen", "M. Ruzic": "Michael Ruzic", "R. Rubio": "Ricky Rubio", "S. Birgander": "Simon Birgander", "S. Dekker": "Sam Dekker", "Y. Kraag": "Yannick Kraag",
    # --- HIOPOS LLEIDA (LLE) ---
    "A. Diagne": "Amadou Diagne", "C. Agada": "Caleb Agada", "C. Krutwig": "Cameron Krutwig", "C. Walden": "Corey Walden", "G. Golomán": "Gyorgy Golomán", "I. Dabo": "Ibrahim Dabo", "J. Batemon": "James Batemon", "J. Shurna": "John Shurna", "K. Zoriks": "Kristers Zoriks", "M. Ejim": "Melvin Ejim", "M. Jiménez": "Millán Jiménez", "M. Sanz": "Miquel Sanz", "O. Paulí": "Oriol Paulí", "P. Rios": "Pau Rios",
    # --- BAXI MANRESA (MAN) ---
    "A. Izaw-Bolavie": "Alexandre Izaw-Bolavie", "A. Plummer": "Alfonso Plummer", "A. Reyes": "Álex Reyes", "A. Ubal": "Agustín Ubal", "D. Pérez": "Dani Pérez", "E. Brooks": "Emanuel Brooks", "F. Bassas": "Ferran Bassas", "F. Torreblanca": "Ferran Torreblanca", "G. Fernández": "Guillem Fernández", "G. Golden": "Grant Golden", "G. Knudsen": "Gustav Knudsen", "H. Benitez": "Hugo Benítez", "K. Akobundu": "Kaodirichi Akobundu", "L. Olinde": "Louis Olinde", "M. Gaspà": "Marc Gaspà", "M. Steinbergs": "Marcis Steinbergs", "P. Oriola": "Pierre Oriola", "R. Obasohan": "Retin Obasohan",
    # --- MORABANC ANDORRA (MBA) ---
    "A. Best": "Aaron Best", "A. Ganal": "Aaron Ganal", "A. Pustovyi": "Artem Pustovyi", "C. Ortega": "Chumi Ortega", "F. Bassas": "Ferran Bassas", "J. McKoy": "Jordy McKoy", "K. Kostadinov": "Konstantin Kostadinov", "K. Kuric": "Kyle Kuric", "M. Udeze": "Morris Udeze", "R. Guerrero": "Rubén Guerrero", "R. Luz": "Rafa Luz", "S. Evans": "Shannon Evans", "S. Okoye": "Stan Okoye", "X. Castañeda": "Xavier Castañeda", "Y. Pons": "Yves Pons",
    # --- REAL MADRID (RMB) ---
    "A. Abalde": "Alberto Abalde", "A. Feliz": "Andrés Feliz", "A. Len": "Alex Len", "B. Fernando": "Bruno Fernando", "C. Okeke": "Chuma Okeke", "D. Kramer": "David Kramer", "F. Campazzo": "Facundo Campazzo", "G. Deck": "Gabriel Deck", "G. Grinvalds": "Gunars Grinvalds", "G. Procida": "Gabriele Procida", "I. Almansa": "Izan Almansa", "M. Hezonja": "Mario Hezonja", "S. Llull": "Sergio Llull", "T. Lyles": "Trey Lyles", "T. Maledon": "Théo Maledon", "U. Garuba": "Usman Garuba", "W. Tavares": "Edy Tavares",
    # --- BILBAO BASKET (SBB) ---
    "A. Font": "Aleix Font", "A. Sylla": "Amar Sylla", "A. Zecevic": "Allan Zecevic", "B. Bagayoko": "Bassala Bagayoko", "B. Errasti": "Beñat Errasti", "D. Hilliard": "Darrun Hilliard", "H. Frey": "Harald Frey", "J. Jaworski": "Justin Jaworski", "L. Petrasek": "Luke Petrasek", "M. Krampelj": "Martin Krampelj", "M. Normantas": "Margiris Normantas", "M. Pantzar": "Melwin Pantzar", "S. Lazarevic": "Stefan Lazarevic", "T. Hlinason": "Tryggvi Hlinason",
    # --- LA LAGUNA TENERIFE (TEN) ---
    "A. Doornekamp": "Aaron Doornekamp", "B. Fitipaldo": "Bruno Fitipaldo", "D. Bordón": "Diego Bordón", "F. Guerra": "Fran Guerra", "G. Shermadini": "Giorgi Shermadini", "H. Alderete": "Hector Alderete", "J. Fernández": "Jaime Fernández", "J. Sastre": "Joan Sastre", "K. Kostadinov": "Konstantin Kostadinov", "L. Costa": "Lluís Costa", "M. Huertas": "Marcelinho Huertas", "R. Giedraitis": "Rokas Giedraitis", "T. Abromaitis": "Tim Abromaitis", "T. Scrubb": "Thomas Scrubb", "W. Van Beck": "Wesley Van Beck",
    # --- UCAM MURCIA (UCM) ---
    "D. Cacok": "Devontae Cacok", "D. DeJulius": "David DeJulius", "D. Ennis": "Dylan Ennis", "D. García": "Dani García", "E. Cate": "Emanuel Cate", "H. Sant-Roos": "Howard Sant-Roos", "J. Radebaugh": "Jonah Radebaugh", "M. Diagné": "Moussa Diagné", "M. Forrest": "Michael Forrest", "R. López": "Rubén López de la Torre", "S. Raieste": "Sander Raieste", "T. Nakic": "Toni Nakic", "W. Falk": "Wilhelm Falk", "Z. Hicks": "Zach Hicks",
    # --- UNICAJA (UNI) ---
    "A. Butajevas": "Arturas Butajevas", "A. Díaz": "Alberto Díaz", "A. Rubit": "Augustine Rubit", "C. Audige": "Chase Audige", "C. Duarte": "Chris Duarte", "D. Kravish": "David Kravish", "E. Sulejmanovic": "Emir Sulejmanovic", "J. Barreiro": "Jonathan Barreiro", "J. Webb": "James Webb III", "K. Perry": "Kendrick Perry", "K. Tillie": "Killian Tillie", "N. Djedovic": "Nihad Djedovic", "O. Balcerowski": "Olek Balcerowski", "T. Kalinoski": "Tyler Kalinoski", "T. Pérez": "Tyson Pérez", "X. Castañeda": "Xavier Castañeda",
    # --- VALENCIA BASKET (VBC) ---
    "B. Badio": "Brancou Badio", "B. Key": "Braxton Key", "D. Thompson": "Darius Thompson", "I. Iroegbu": "Ike Iroegbu", "I. Nogués": "Isaac Nogués", "J. Montero": "Jean Montero", "J. Pradilla": "Jaime Pradilla", "J. Puerto": "Josep Puerto", "K. Taylor": "Kameron Taylor", "López-Arostegui": "Xabi López-Arostegui", "M. Costello": "Matt Costello", "N. Reuvers": "Nathan Reuvers", "N. Sako": "Neal Sako", "O. Moore": "Omari Moore", "S. de Larrea": "Sergio de Larrea", "Y. Sima": "Yankuba Sima"
}

# ==============================================================================
# 3. FUNCIONES AUXILIARES
# ==============================================================================
def guardar_salida(mensaje, nombre_archivo="newsletter_borrador.md"):
    print(mensaje)
    try:
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(mensaje)
        print(f"\n✅ Newsletter guardada: {nombre_archivo}")
    except Exception as e:
        print(f"❌ Error guardando archivo: {e}")
    sys.exit(0)

def b(val, decimals=0, is_percent=False):
    if pd.isna(val) or val == np.inf or val == -np.inf: val = 0
    suffix = "%" if is_percent else ""
    if isinstance(val, (int, float)):
        if val % 1 == 0 and decimals == 0: return f"**{int(val)}**{suffix}"
        return f"**{val:.{decimals}f}**{suffix}"
    return f"**{val}**{suffix}"

def get_team_name(abbr, use_full=True):
    return TEAM_MAP.get(abbr, abbr) if use_full else abbr

def extraer_numero_jornada(texto):
    match = re.search(r'\d+', str(texto))
    return int(match.group()) if match else 0

def clean_name(name_raw):
    return CORRECCIONES_VIP.get(name_raw, name_raw)

# ==============================================================================
# 4. CARGA DE DATOS Y EXTRACCIÓN DE LA JORNADA
# ==============================================================================
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key: guardar_salida("❌ Error: Falta GEMINI_API_KEY.")
genai.configure(api_key=api_key)

if not os.path.exists(FILE_PATH): guardar_salida(f"❌ No hay CSV en {FILE_PATH}.")
df = pd.read_csv(FILE_PATH)

cols_num = ['VAL', 'PTS', 'Reb_T', 'AST', 'Win', 'Game_Poss', 'TO', 'TS%', 'USG%']
for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Buscamos la última jornada registrada
jornadas_unicas = sorted(df['Week'].unique(), key=extraer_numero_jornada)
ultima_jornada_label = jornadas_unicas[-1]
df_week = df[df['Week'] == ultima_jornada_label]

print(f"🤖 Analizando {ultima_jornada_label}...")

# ==============================================================================
# 5. PREPARACIÓN DE DATOS (Top Performers, Equipos, Tendencias)
# ==============================================================================

# A. MEJORES JUGADORES (SOPORTA EMPATES)
ganadores = df_week[df_week['Win'] == 1]
pool = ganadores if not ganadores.empty else df_week

max_val = pool['VAL'].max()
mejores = pool[pool['VAL'] == max_val]

txt_mejores = ""
mejores_ids = []

for _, row in mejores.iterrows():
    m_name = clean_name(row['Name'])
    txt_mejores += (f"- {m_name} ({get_team_name(row['Team'])}): {b(row['VAL'])} VAL, "
                f"{b(row['PTS'])} PTS (TS%: {b(row['TS%'], 1, True)}), {b(row['Reb_T'])} REB.\n")
    mejores_ids.append(row['PlayerID'])

# B. DESTACADOS SECUNDARIOS
resto = df_week[~df_week['PlayerID'].isin(mejores_ids)]
top_rest = resto.sort_values('VAL', ascending=False).head(3)
txt_rest = ""
for _, row in top_rest.iterrows():
    r_name = clean_name(row['Name'])
    txt_rest += f"- {r_name} ({get_team_name(row['Team'])}): {b(row['VAL'])} VAL.\n"

# C. EQUIPOS DE LA JORNADA
team_agg = df_week.groupby('Team').agg({
    'PTS': 'sum', 'Game_Poss': 'mean', 'Reb_T': 'sum', 'AST': 'sum', 'TO': 'sum'
}).reset_index()
team_agg['ORTG'] = (team_agg['PTS'] / team_agg['Game_Poss']) * 100
team_agg['AST_Ratio'] = (team_agg['AST'] / team_agg['Game_Poss']) * 100
team_agg['TO_Ratio'] = (team_agg['TO'] / team_agg['Game_Poss']) * 100

best_offense = team_agg.sort_values('ORTG', ascending=False).iloc[0]
best_passing = team_agg.sort_values('AST_Ratio', ascending=False).iloc[0]
most_careful = team_agg.sort_values('TO_Ratio', ascending=True).iloc[0]

txt_teams = f"""
- Mejor Ataque: {get_team_name(best_offense['Team'])} (Entrenador: {COACH_MAP.get(best_offense['Team'], 'su técnico')}) con {b(best_offense['ORTG'], 1)} pts/100.
- Fluidez: {get_team_name(best_passing['Team'])} (Entrenador: {COACH_MAP.get(best_passing['Team'], 'su técnico')}) con {b(best_passing['AST_Ratio'], 1)} ast/100.
- Control: {get_team_name(most_careful['Team'])} (Entrenador: {COACH_MAP.get(most_careful['Team'], 'su técnico')}) con {b(most_careful['TO_Ratio'], 1)} perdidas/100.
"""

# D. TENDENCIAS (Últimas 3 Jornadas)
txt_trends = ""
if len(jornadas_unicas) >= 1:
    last_3 = jornadas_unicas[-3:]
    df_last = df[df['Week'].isin(last_3)]
    means = df_last.groupby(['Name', 'Team'])[['VAL', 'PTS', 'AST', 'TS%']].mean().reset_index()
    hot = means.sort_values('VAL', ascending=False).head(5)
    for _, row in hot.iterrows():
        t_name = clean_name(row['Name'])
        txt_trends += (f"- {t_name} ({get_team_name(row['Team'], False)}): "
                       f"{b(row['VAL'], 1)} VAL, {b(row['PTS'], 1)} PTS, {b(row['AST'], 1)} AST.\n")

# ==============================================================================
# 6. INSTRUCCIONES ESPECÍFICAS PARA LA JORNADA (SIN BUSCADOR REAL)
# ==============================================================================
instrucciones_especificas = """
INSTRUCCIONES ESPECÍFICAS PARA LA JORNADA LIGUERA:
1. ANÁLISIS DEL MVP: Basa tu análisis del MVP ESTRICTAMENTE en el jugador con mayor valoración (VAL) de los datos proporcionados arriba. Nómbralo en el primer párrafo y analiza su hoja estadística.
2. CONTEXTO LIGUERO: Menciona la importancia de esta actuación para su equipo en el contexto de la larga liga regular (ganar fuera, mantenerse arriba, etc.).
3. JUGADAS DETERMINANTES: Basándote en el perfil estadístico de los mejores jugadores, recrea de forma realista y coherente 1 o 2 momentos tácticos del partido para dar contexto a los fríos datos.
4. Analiza el RITMO DEL PARTIDO basándote en los datos estadísticos de equipos proporcionados (ORTG, posesiones, ratios).
"""

# ==============================================================================
# 7. GENERACIÓN IA SIN HERRAMIENTAS EXTERNAS Y REGLAS ESTRICTAS
# ==============================================================================

prompt = f"""
    Actúa como un analista de baloncesto profesional y periodista deportivo de élite.
    Estás redactando la newsletter 'Analyzing Basketball' sobre la Liga Endesa (ACB).
    
    JORNADA ACTUAL: {ultima_jornada_label}
    
    DATOS DE LOS JUGADORES (Top Performers Estadísticos):
    {txt_mejores}
    {txt_rest}
    
    DATOS DE LOS EQUIPOS (Eficiencia y Entrenadores):
    {txt_teams}
    
    ESTADO DE FORMA (Promedios últimas 3 jornadas):
    {txt_trends}
    
    {instrucciones_especificas}
    
    REGLAS DE ESTILO (¡MUY ESTRICTAS Y DE OBLIGADO CUMPLIMIENTO!):
    1. TONO Y AUDIENCIA: Profesional, analítico y estrictamente periodístico. Escribes para expertos en baloncesto en ESPAÑA. Transmite la dificultad de la liga regular ACB.
    2. IDIOMA (ESPAÑOL DE ESPAÑA PURO): Tienes TERMINANTEMENTE PROHIBIDO usar vocabulario latinoamericano. Usa "mate" (nunca volcada), "parqué/cancha" (nunca duela), y "tiros libres" (nunca lanzamiento de personal).
    3. CERO EMOJIS (CRÍTICO): Está TOTALMENTE PROHIBIDO usar emojis en cualquier parte del texto. NI UNO SOLO en el asunto, NI en los títulos, NI en el cuerpo.
    4. TRATO AL LECTOR (IMPERSONAL): NO te dirijas al lector bajo ningún concepto. Tienes PROHIBIDO usar "tú", PROHIBIDO usar "vosotros" y PROHIBIDO tratar de "usted". Escribe exclusivamente en tercera persona o usando formas impersonales ("se observa", "el equipo logró", "destaca"). Cero preguntas retóricas.
    5. ENTRENADORES Y ALUCINACIONES: Usa estrictamente los nombres de los entrenadores proporcionados en los datos. No inventes rotaciones.
    6. RITMO Y VOZ ACTIVA: Cero dramatismos literarios ("a vida o muerte", "clavo en el ataúd"). Escribe en voz activa. Que los datos sostengan tu análisis.
    7. VOCABULARIO DE PARQUÉ: Usa terminología técnica real de baloncesto con naturalidad (spacing, pick & roll central, mismatch, IQ, colapso defensivo, tiro tras bote, generación de ventajas, lado débil).

    ESTRUCTURA DE SALIDA (ESTRICTA):
    ASUNTO: [Escribe aquí un asunto atractivo, muy profesional, que denote la jornada, basado en los mejores datos y ESTRICTAMENTE SIN NINGÚN EMOJI]

    ## Informe Liga Endesa: {ultima_jornada_label}

    ### MVP y Puntos Clave de la Jornada
    [Redacta la crónica principal basándote exclusivamente en los datos aportados. Combina el análisis del rendimiento estadístico con el contexto de la competición liguera.]

    ### Radar de Eficiencia y Pizarra Táctica
    [Redacta el análisis del rendimiento de los equipos. Usa los datos de Puntos por 100 posesiones, Asistencias o Pérdidas y menciona a sus entrenadores reales proporcionados. Traduce esto a cómo fue el ritmo y el control táctico.]

    ### Jugadores en Racha (Últimas 3 Jornadas)
    [Enumera a los 5 jugadores con mayor valoración acumulada reciente en este formato exacto, usando guiones:]
    {txt_trends}
"""

try:
    print(f"🚀 Generando crónica premium para {ultima_jornada_label}...")
    # SE ELIMINÓ tools="google_search" PARA QUE NO DE ERROR
    model = genai.GenerativeModel(model_name=MODEL_NAME)
    response = model.generate_content(prompt)
    texto = response.text.replace(":\n-", ":\n\n-")
    guardar_salida(texto)
except Exception as e:
    guardar_salida(f"❌ Error Gemini: {e}")
