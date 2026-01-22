import requests
import os
import re
import datetime
import subprocess # <--- NUEVO: Para ejecutar tus otros scripts
from bs4 import BeautifulSoup

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
TEMPORADA = '2025'
COMPETICION = '1'
HORAS_BUFFER = 10 # Has puesto 10 horas. Si quieres 4, cámbialo aquí.
LOG_FILE = "data/log.txt"
BUFFER_FILE = "data/buffer_control.txt"

# API Key y Headers
API_KEY = '0dd94928-6f57-4c08-a3bd-b1b2f092976e'
HEADERS_API = {
    'x-apikey': API_KEY,
    'origin': 'https://live.acb.com',
    'referer': 'https://live.acb.com/',
    'user-agent': 'Mozilla/5.0'
}

# ==============================================================================
# ZONA 1: TUS FUNCIONES DE SCRAPING
# ==============================================================================

def get_last_jornada_from_log():
    if not os.path.exists(LOG_FILE):
        return 0
    last_jornada = 0
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                match = re.search(r'Jornada\s*[:#-]?\s*(\d+)', line, re.IGNORECASE)
                if match:
                    num = int(match.group(1))
                    if num > last_jornada:
                        last_jornada = num
    except Exception as e:
        print(f"Error leyendo log: {e}")
        return 0
    return last_jornada

def get_game_ids(temp_id, comp_id, jornada_id):
    url = f"https://www.acb.com/resultados-clasificacion/ver/temporada_id/{temp_id}/competicion_id/{comp_id}/jornada_numero/{jornada_id}"
    ids = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        for a in soup.find_all('a', href=True):
            if "/partido/estadisticas/id/" in a['href']:
                try:
                    pid = int(a['href'].split("/id/")[1].split("/")[0])
                    ids.append(pid)
                except: pass
        return list(set(ids))
    except: return []

def is_game_finished(game_id):
    url = "https://api2.acb.com/api/matchdata/Result/boxscores"
    try:
        r = requests.get(url, params={'matchId': game_id}, headers=HEADERS_API, timeout=5)
        if r.status_code != 200: return False
        data = r.json()
        if 'teamBoxscores' not in data or len(data['teamBoxscores']) < 2: return False
        return True
    except: return False

# ==============================================================================
# ZONA 2: EL PUENTE (Aquí está el cambio clave)
# ==============================================================================

def ejecutar_secuencia_completa(jornada):
    """
    Ejecuta ai_writer.py y luego email_sender.py
    """
    print(f"🔄 Iniciando secuencia para Jornada {jornada}...")

    # 1. EJECUTAR EL ESCRITOR (IA)
    print("🤖 1. Ejecutando ai_writer.py...")
    try:
        # Ejecuta el script y captura si falla
        resultado_ai = subprocess.run(["python", "ai_writer.py"], check=True, text=True, capture_output=True)
        print(resultado_ai.stdout) # Muestra lo que diga la IA
    except subprocess.CalledProcessError as e:
        print(f"❌ Error crítico en ai_writer: {e.stderr}")
        return False

    # 2. EJECUTAR EL ENVIADOR (EMAIL)
    print("📧 2. Ejecutando email_sender.py...")
    try:
        resultado_email = subprocess.run(["python", "email_sender.py"], check=True, text=True, capture_output=True)
        print(resultado_email.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error crítico en email_sender: {e.stderr}")
        return False

def gestionar_buffer(jornada):
    ahora = datetime.datetime.now()
    
    if os.path.exists(BUFFER_FILE):
        with open(BUFFER_FILE, "r") as f:
            contenido = f.read().strip().split(",")
            
        if len(contenido) != 2 or int(contenido[0]) != jornada:
            print(f"Detectado cambio de jornada o archivo corrupto. Reiniciando buffer para J{jornada}.")
            with open(BUFFER_FILE, "w") as f:
                f.write(f"{jornada},{ahora.timestamp()}")
            return False 

        timestamp_inicio = float(contenido[1])
        inicio_espera = datetime.datetime.fromtimestamp(timestamp_inicio)
        diferencia = ahora - inicio_espera
        horas_pasadas = diferencia.total_seconds() / 3600

        print(f"⏳ Buffer activo para J{jornada}. Llevamos {horas_pasadas:.2f} / {HORAS_BUFFER} horas.")

        if horas_pasadas >= HORAS_BUFFER:
            return True
        else:
            return False
            
    else:
        print(f"🆕 Jornada terminada detectada por primera vez. Iniciando cuenta atrás de {HORAS_BUFFER}h.")
        with open(BUFFER_FILE, "w") as f:
            f.write(f"{jornada},{ahora.timestamp()}")
        return False

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    last_sent = get_last_jornada_from_log()
    target_jornada = last_sent + 1
    
    print(f"--- INICIO SCRIPT ---")
    print(f"Última enviada: {last_sent}. Revisando Jornada: {target_jornada}")

    game_ids = get_game_ids(TEMPORADA, COMPETICION, str(target_jornada))
    
    if not game_ids:
        print(f"⛔ Jornada {target_jornada} sin partidos o futura.")
        return

    finished_count = 0
    for gid in game_ids:
        if is_game_finished(gid):
            finished_count += 1
    
    print(f"📊 Estado J{target_jornada}: {finished_count}/{len(game_ids)} terminados.")

    if finished_count == len(game_ids) and len(game_ids) > 0:
        print("✅ Todos los partidos han terminado.")
        
        tiempo_cumplido = gestionar_buffer(target_jornada)
        
        if tiempo_cumplido:
            print("🚀 Buffer superado. Lanzando la IA y el Email...")
            
            # LLAMAMOS A LA NUEVA FUNCIÓN QUE EJECUTA LOS OTROS ARCHIVOS
            exito = ejecutar_secuencia_completa(target_jornada)
            
            if exito:
                fecha_log = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                linea_log = f"{fecha_log} : ✅ Jornada {target_jornada} completada y enviada.\n"
                
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(linea_log)
                
                if os.path.exists(BUFFER_FILE):
                    os.remove(BUFFER_FILE)
                    
                print("🏁 Proceso finalizado con éxito.")
        else:
            print("zzz Esperando buffer...")
            
    else:
        print("⚽ Aún se está jugando.")
        if os.path.exists(BUFFER_FILE):
             os.remove(BUFFER_FILE)

if __name__ == "__main__":
    main()
