import pandas as pd
import os
import google.generativeai as genai
import sys

# 1. CONFIGURACIÓN GEMINI
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ Error: No he encontrado la GEMINI_API_KEY en los secretos.")
    sys.exit(1)

# Configuramos la librería de Google
genai.configure(api_key=api_key)

FILE_PATH = "data/BoxScore_ACB_2025_Cumulative.csv"

# 2. CARGAR Y PREPARAR DATOS
if not os.path.exists(FILE_PATH):
    print("❌ No hay archivo de datos todavía.")
    sys.exit(0)

df = pd.read_csv(FILE_PATH)

# Filtrar la última jornada disponible
ultima_jornada = df['Week'].unique()[-1]
df_week = df[df['Week'] == ultima_jornada]

print(f"🤖 (Gemini) Analizando: {ultima_jornada}...")

# 3. EXTRAER INSIGHTS
top_players = df_week.sort_values('GmSc', ascending=False).head(3)
top_list_text = ""
for i, row in top_players.iterrows():
    top_list_text += f"- {row['Name']} ({row['Team']}): {row['PTS']} pts, {row['Reb_T']} reb, {row['AST']} ast. TS%: {row['TS%']}%. GmSc: {row['GmSc']}.\n"

shooters = df_week[(df_week['PTS'] >= 10)].sort_values('TS%', ascending=False).head(1)
shooter_text = ""
if not shooters.empty:
    s = shooters.iloc[0]
    shooter_text = f"Jugador más eficiente: {s['Name']} con {s['TS%']}% True Shooting anotando {s['PTS']} puntos."

# 4. CREAR EL PROMPT
prompt = f"""
Eres un analista experto de baloncesto ACB. Escribe un resumen breve y emocionante para una newsletter sobre la {ultima_jornada}.
Usa estilo periodístico deportivo, directo y con datos. No uses frases como "Aquí tienes el resumen", empieza directo.

DATOS:
LOS MEJORES (MVP):
{top_list_text}

DATO EFICIENCIA:
{shooter_text}

FORMATO:
# TÍTULO EMOTIVO 🏀
**El MVP de la semana**
[Párrafo sobre el mejor jugador]

**Otros destacados**
[Breve mención a los otros dos]

**El dato Moneyball 📊**
[Frase sobre la eficiencia]
"""

# 5. LLAMAR A GEMINI
try:
    # Usamos 'gemini-1.5-flash' que es rápido, gratis y muy bueno para texto
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    response = model.generate_content(prompt)
    
    newsletter_content = response.text
    
    print("\n✅ Newsletter Generada por Gemini:\n")
    print(newsletter_content)
    
    with open("newsletter_borrador.md", "w", encoding="utf-8") as f:
        f.write(newsletter_content)

except Exception as e:
    print(f"❌ Error conectando con Gemini: {e}")
