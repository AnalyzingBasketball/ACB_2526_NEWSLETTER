import pandas as pd
import os
import google.generativeai as genai
import sys

# Función auxiliar para guardar el error en el archivo y no romper GitHub Actions
def guardar_error_y_salir(mensaje):
    print(mensaje)
    with open("newsletter_borrador.md", "w", encoding="utf-8") as f:
        f.write(f"# ⚠️ Error en la generación\n\n{mensaje}")
    sys.exit(0) # Salimos con éxito (0) para que Git guarde el aviso de error

# 1. CONFIGURACIÓN GEMINI
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    guardar_error_y_salir("❌ Error: No se encontró la GEMINI_API_KEY en los secretos del repositorio.")

try:
    genai.configure(api_key=api_key)
except Exception as e:
    guardar_error_y_salir(f"❌ Error configurando Gemini: {e}")

FILE_PATH = "data/BoxScore_ACB_2025_Cumulative.csv"

# 2. CARGAR DATOS
if not os.path.exists(FILE_PATH):
    # Verificamos qué hay en la carpeta para debug
    print("Contenido de carpeta data/:")
    if os.path.exists("data"):
        print(os.listdir("data"))
    else:
        print("La carpeta data/ no existe.")
    guardar_error_y_salir(f"❌ Error: No se encontró el archivo {FILE_PATH}. ¿Se ejecutó bien el scraper?")

try:
    df = pd.read_csv(FILE_PATH)
    if df.empty:
         guardar_error_y_salir("⚠️ El CSV existe pero está vacío (sin datos).")
         
    # Filtrar la última jornada disponible
    if 'Week' not in df.columns:
        guardar_error_y_salir("❌ Error: El CSV no tiene la columna 'Week'.")
        
    ultima_jornada = df['Week'].unique()[-1]
    df_week = df[df['Week'] == ultima_jornada]
    print(f"🤖 (Gemini) Analizando: {ultima_jornada}...")

    # 3. EXTRAER INSIGHTS
    top_players = df_week.sort_values('GmSc', ascending=False).head(3)
    top_list_text = ""
    for i, row in top_players.iterrows():
        top_list_text += f"- {row['Name']} ({row['Team']}): {row['PTS']} pts, {row['GmSc']} val.\n"

    shooters = df_week[(df_week['PTS'] >= 10)].sort_values('TS%', ascending=False).head(1)
    shooter_text = "N/A"
    if not shooters.empty:
        s = shooters.iloc[0]
        shooter_text = f"{s['Name']} ({s['TS%']}% TS)"

    # 4. PROMPT
    prompt = f"""
    Escribe una newsletter breve de baloncesto ACB sobre la {ultima_jornada}.
    Destacados: {top_list_text}
    Eficiencia: {shooter_text}
    Formato Markdown. Título emotivo.
    """

    # 5. GENERAR
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    response = model.generate_content(prompt)
    
    contenido = response.text
    
    if not contenido:
        guardar_error_y_salir("⚠️ Gemini respondió pero el contenido está vacío.")

    print("\n✅ Newsletter Generada con éxito.")
    with open("newsletter_borrador.md", "w", encoding="utf-8") as f:
        f.write(contenido)

except Exception as e:
    guardar_error_y_salir(f"❌ Error inesperado durante el proceso: {str(e)}")
