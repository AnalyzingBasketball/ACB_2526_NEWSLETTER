import pandas as pd
import os
import google.generativeai as genai
import sys
import re # IMPORTANTE: Necesario para el reemplazo inteligente de nombres

# --- CONFIGURACIÓN ---
def guardar_salida(mensaje, nombre_archivo="newsletter_borrador.md"):
    print(mensaje)
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(mensaje)
    sys.exit(0)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key: guardar_salida("❌ Error: Falta GEMINI_API_KEY.")

try:
    genai.configure(api_key=api_key)
except Exception as e:
    guardar_salida(f"❌ Error config Gemini: {e}")

FILE_PATH = "data/BoxScore_ACB_2025_Cumulative.csv"
if not os.path.exists(FILE_PATH): guardar_salida("❌ No hay CSV de datos.")

# --- CARGA DATOS ---
df = pd.read_csv(FILE_PATH)
if 'Week' not in df.columns: guardar_salida("❌ CSV sin columna Week.")

ultima_jornada_label = df['Week'].unique()[-1]
df_week = df[df['Week'] == ultima_jornada_label]
print(f"🤖 Procesando {ultima_jornada_label}...")

# --- 1. MVP ---
ganadores = df_week[df_week['Win'] == 1]
pool = ganadores if not ganadores.empty else df_week
mvp = pool.sort_values('VAL', ascending=False).iloc[0]
txt_mvp = f"{mvp['Name']} ({mvp['Team']}): {mvp['VAL']} VAL, {mvp['PTS']} pts, {mvp['Reb_T']} reb."

# --- 2. DESTACADOS ---
resto = df_week[df_week['PlayerID'] != mvp['PlayerID']]
top_rest = resto.sort_values('VAL', ascending=False).head(3)
txt_rest = ""
for _, row in top_rest.iterrows():
    txt_rest += f"- {row['Name']} ({row['Team']}): {row['VAL']} VAL.\n"

# --- 3. EQUIPOS ---
team_stats = df_week.groupby('Team').agg({'PTS': 'sum', 'Game_Poss': 'mean'}).reset_index()
team_stats['ORTG'] = (team_stats['PTS'] / team_stats['Game_Poss']) * 100
best_offense = team_stats.sort_values('ORTG', ascending=False).iloc[0]
txt_teams = f"Mejor Ataque: {best_offense['Team']} ({best_offense['ORTG']:.1f} pts/100 poss)."

# --- 4. TENDENCIAS (CON ASISTENCIAS) ---
jornadas = df['Week'].unique()
txt_trends = "Datos insuficientes para tendencias."
if len(jornadas) >= 3:
    last_3 = jornadas[-3:]
    df_last = df[df['Week'].isin(last_3)]
    
    # MODIFICACIÓN: Añadir 'AST' a la lista de columnas
    cols_to_mean = ['VAL', 'PTS', 'Reb_T']
    if 'AST' in df.columns: cols_to_mean.append('AST')
    
    means = df_last.groupby(['Name', 'Team'])[cols_to_mean].mean().reset_index()
    hot = means.sort_values('VAL', ascending=False).head(5)
    txt_trends = ""
    for _, row in hot.iterrows():
        # MODIFICACIÓN: Añadir el dato de AST al texto si existe
        linea = f"- {row['Name']} ({row['Team']}): {row['VAL']:.1f} VAL, {row['PTS']:.1f} PTS, {row['Reb_T']:.1f} REB"
        if 'AST' in df.columns: linea += f", {row['AST']:.1f} AST"
        linea += ".\n"

# --- 5. PROMPT ---
# NOTA: He añadido \n después de cada título en negrita para forzar el salto de línea visual.
prompt = f"""
Actúa como Data Scientist senior de "Analyzing Basketball". Escribe un informe técnico y sobrio de la {ultima_jornada_label}.

DATOS INPUT:
MVP: {txt_mvp}
TOP: {txt_rest}
EQUIPO: {txt_teams}
TENDENCIAS:
{txt_trends}

ESTRUCTURA OBLIGATORIA DEL INFORME:
**INFORME TÉCNICO: {ultima_jornada_label}**

**1. Análisis de Impacto Individual**\n
[Analiza al MVP en un párrafo de 3-4 líneas, enfocándote en su eficiencia y por qué sus números importan más allá del boxscore básico.]

**2. Cuadro de Honor**\n
[Menciona brevemente a los otros destacados y qué aportaron a sus equipos.]

**3. Desempeño Colectivo**\n
[Analiza el mejor ataque mencionado en los datos.]

**4. Proyección Estadística (Tendencias)**\n
A continuación, los jugadores a vigilar la próxima semana por su estado de forma (Medias últimas 3 jornadas):

[INSTRUCCIÓN CRÍTICA: Copia la lista de tendencias TAL CUAL. Usa guiones para crear una lista vertical. NO añadas texto extra.]
{txt_trends}

---
AB
"""

# --- 6. GENERACIÓN Y LIMPIEZA ---
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    texto_final = response.text

    # --- CAMBIO CLAVE: REEMPLAZO INTELIGENTE DE SIGLAS ---
    # 1. Mapa de siglas a nombres completos (Ajusta si falta alguno de esta temporada)
    team_map = {
        'UNI': 'Unicaja', 'RMB': 'Real Madrid', 'FCB': 'Barça',
        'VBC': 'Valencia Basket', 'TFU': 'Lenovo Tenerife', 'UCM': 'UCAM Murcia',
        'GCB': 'Dreamland Gran Canaria', 'JOV': 'Joventut Badalona', 'BKN': 'Baskonia',
        'MAN': 'BAXI Manresa', 'ZAR': 'Casademont Zaragoza', 'BIL': 'Surne Bilbao Basket',
        'GIR': 'Bàsquet Girona', 'BRE': 'Río Breogán', 'OBR': 'Monbus Obradoiro',
        'GRA': 'Covirán Granada', 'PAL': 'Zunder Palencia', 'AND': 'MoraBanc Andorra',
        'COV': 'Covirán Granada' # Por si acaso usa este
    }

    # 2. Función que hace el reemplazo si encuentra una coincidencia
    def replace_team_acronym(match):
        acronym = match.group(1) # La sigla encontrada (ej: UNI)
        # Devuelve el nombre completo si está en el mapa, si no, devuelve la sigla original
        return team_map.get(acronym, acronym)

    # 3. La Expresión Regular Mágica:
    # (?<!\()  -> Mira atrás y asegúrate de que NO hay un paréntesis abierto '('
    # (...)    -> Busca cualquiera de las siglas de nuestro mapa (UNI|RMB|FCB...)
    # (?!\))   -> Mira adelante y asegúrate de que NO hay un paréntesis cerrado ')'
    pattern = r"(?<!\()(" + "|".join(team_map.keys()) + r")(?!\))"

    # Aplicamos el reemplazo sobre el texto generado por Gemini
    texto_final_limpio = re.sub(pattern, replace_team_acronym, texto_final)

    # --- LIMPIEZA FINAL DE FORMATO ---
    texto_final_limpio = texto_final_limpio.replace(". -", ".\n\n-").replace(": -", ":\n\n-")
    
    guardar_salida(texto_final_limpio)
    
except Exception as e:
    guardar_salida(f"❌ Error Gemini: {e}")

