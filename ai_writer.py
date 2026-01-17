import pandas as pd
import os
import google.generativeai as genai
import sys

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

# --- 4. TENDENCIAS (GARANTIZADO: SIN BLOQUEOS) ---
jornadas = df['Week'].unique()
txt_trends = "Datos insuficientes para tendencias."

# Usamos >= 1 para que salga SIEMPRE
if len(jornadas) >= 1:
    last_3 = jornadas[-3:]
    df_last = df[df['Week'].isin(last_3)]
    
    cols_calc = ['VAL', 'PTS', 'Reb_T', 'AST']
    means = df_last.groupby(['Name', 'Team'])[cols_calc].mean().reset_index()
    hot = means.sort_values('VAL', ascending=False).head(5)
    
    txt_trends = ""
    for _, row in hot.iterrows():
        # \n\n AL FINAL PARA QUE RESPIRE LA LISTA
        txt_trends += f"- {row['Name']} ({row['Team']}): {row['VAL']:.1f} VAL, {row['PTS']:.1f} PTS, {row['Reb_T']:.1f} REB, {row['AST']:.1f} AST.\n\n"

# --- MAPA DE EQUIPOS PARA EL PROMPT ---
# Se lo pasamos a Gemini para que sepa cómo escribir los nombres
mapa_equipos = """
UNI -> Unicaja
RMB -> Real Madrid
FCB -> Barça
VBC -> Valencia Basket
TFU -> Lenovo Tenerife
UCM -> UCAM Murcia
GCB -> Dreamland Gran Canaria
JOV -> Joventut Badalona
BKN -> Baskonia
MAN -> BAXI Manresa
ZAR -> Casademont Zaragoza
BIL -> Surne Bilbao Basket
GIR -> Bàsquet Girona
BRE -> Río Breogán
GRA -> Covirán Granada
PAL -> Zunder Palencia
AND -> MoraBanc Andorra
MBA -> MoraBanc Andorra
LLE -> Hiopos Lleida
COR -> Leyma Coruña
COV -> Covirán Granada
"""

# --- 5. PROMPT ---
prompt = f"""
Actúa como Data Scientist de "Analyzing Basketball". Escribe un informe técnico de la {ultima_jornada_label}.

DATOS DE ENTRADA:
MVP: {txt_mvp}
TOP: {txt_rest}
EQUIPO: {txt_teams}
TENDENCIAS:
{txt_trends}

DICCIONARIO DE EQUIPOS:
{mapa_equipos}

INSTRUCCIONES CRÍTICAS DE REDACCIÓN (SÍGUELAS AL PIE DE LA LETRA):

1. **JUGADORES Y EQUIPOS EN TEXTO NARRATIVO (SECCIONES 1 y 2):**
   - JAMÁS escribas "Nombre (SIGLA)". Está PROHIBIDO usar paréntesis para el equipo en los párrafos.
   - DEBES escribir siempre: "Nombre, del [Nombre Completo del Equipo],".
   - Ejemplo INCORRECTO: "F. Alonso (BRE) anotó..."
   - Ejemplo CORRECTO: "F. Alonso, del Río Breogán, anotó..."
   - Usa el diccionario de arriba para traducir las siglas (ej: MBA -> MoraBanc Andorra).

2. **VALORACIÓN:**
   - En los párrafos narrativos escribe la palabra completa "valoración".
   - En la lista de tendencias (Sección 4), mantén "VAL".

ESTRUCTURA OBLIGATORIA:
**INFORME TÉCNICO: {ultima_jornada_label}**

**1. Análisis de Impacto Individual**
[Párrafo analizando al MVP siguiendo la regla de "Nombre, del Equipo,".]

**2. Cuadro de Honor**
[Párrafo mencionando destacados siguiendo la regla de "Nombre, del Equipo,".]

**3. Desempeño Colectivo**
[Menciona el mejor ataque]

**4. Proyección Estadística (Tendencias)**
A continuación, los jugadores a vigilar la próxima semana por su estado de forma (Medias últimas jornadas):

{txt_trends}

---
AB
"""

# --- 6. GENERACIÓN Y LIMPIEZA A MARTILLAZOS ---
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    
    texto_final = response.text
    
    # 1. SEGURIDAD LISTA: Forzar saltos de línea en listas si Gemini los ha quitado
    texto_final = texto_final.replace(". -", ".\n\n-").replace(": -", ":\n\n-")

    # 2. SEGURIDAD TÍTULOS (LO QUE PEDÍAS DE LAS BARRAS):
    # Reemplazamos los encabezados conocidos por el encabezado + DOBLE SALTO DE LÍNEA explícito
    texto_final = texto_final.replace("**1. Análisis de Impacto Individual**", "**1. Análisis de Impacto Individual**\n\n")
    texto_final = texto_final.replace("**2. Cuadro de Honor**", "\n\n**2. Cuadro de Honor**\n\n")
    texto_final = texto_final.replace("**3. Desempeño Colectivo**", "\n\n**3. Desempeño Colectivo**\n\n")
    texto_final = texto_final.replace("**4. Proyección Estadística (Tendencias)**", "\n\n**4. Proyección Estadística (Tendencias)**\n\n")

    # 3. SEGURIDAD FINAL EQUIPOS (Por si Gemini falla):
    # Si queda algún "MBA" suelto (sin paréntesis), lo cambiamos a mano
    texto_final = texto_final.replace(" MBA ", " MoraBanc Andorra ").replace(" UNI ", " Unicaja ")
    
    guardar_salida(texto_final)
    
except Exception as e:
    guardar_salida(f"❌ Error Gemini: {e}")
