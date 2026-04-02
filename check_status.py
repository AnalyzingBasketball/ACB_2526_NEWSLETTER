import requests
import os
import re
import datetime
import subprocess 
import time
import random

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
TEMPORADA = '2025'
COMPETICION = '1'
LOG_FILE = "data/log.txt"
BUFFER_FILE = "data/buffer_control.txt"

# 🚨 INTERRUPTOR DE PRUEBAS 🚨
# Cambia a True para probar sin esperas. Cámbialo a False para la ejecución real automatizada.
MODO_PRUEBA = True  

# API Key y Headers
API_KEY = '0dd94928-6f57-4c08-a3bd-b1b2f092976e'
HEADERS_API = {
    'X-APIKEY': API_KEY,
    'Accept': 'application/json',
    'Origin': 'https://www.acb.com',
    'Referer': 'https://www.acb.com/es/liga/calendario',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.4 Safari/605.1.15'
}

# ==============================================================================
# ZONA 1: FUNCIONES DE EXTRACCIÓN Y ESTADO
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
    url_base = f"https://api2.acb.com/api/seasondata/Competition/matches?competitionId={comp_id}"
    print(f"🔍 Fase 1: Obteniendo mapeo de rondas para la Jornada {jornada_id}...")
    ids = []
    
    try:
        r_base = requests.get(url_base, headers=HEADERS_API, timeout=15)
        print(f"📡 Código de respuesta API (Fase 1): {r_base.status_code}")
        
        if r_base.status_code == 200:
            data = r_base.json()
            
            rondas = data.get('availableFilters', {}).get('rounds', [])
            round_id_interno = None
            
            for ronda in rondas:
                if str(ronda.get('roundNumber')) == str(jornada_id):
                    round_id_interno = ronda.get('id')
                    break
            
            if not round_id_interno:
                print(f"⚠️ No se encontró el ID interno en la API para la Jornada {jornada_id}.")
                return []
                
            print(f"🔗 Correspondencia encontrada: Jornada {jornada_id} = roundId {round_id_interno}")
            
            url_jornada = f"https://api2.acb.com/api/seasondata/Competition/matches?competitionId={comp_id}&roundId={round_id_interno}"
            print(f"🔍 Fase 2: Extrayendo partidos del roundId {round_id_interno}...")
            
            r_jornada = requests.get(url_jornada, headers=HEADERS_API, timeout=15)
            print(f"📡 Código de respuesta API (Fase 2): {r_jornada.status_code}")
            
            if r_jornada.status_code == 200:
                data_jornada = r_jornada.json()
                partidos = data_jornada.get('matches', [])
                
                for partido in partidos:
                    game_id = partido.get('id')
                    if game_id:
                        ids.append(game_id)
                        
                print(f"🎯 IDs encontrados para Jornada {jornada_id}: {ids}")
                return ids
            else:
                print(f"⚠️ Error en Fase 2. Código: {r_jornada.status_code}")
                return []
                
        else:
            print(f"⚠️ La API base devolvió un error inesperado. Código: {r_base.status_code}")
            return []

    except Exception as e: 
        print(f"❌ Error crítico conectando con la API: {e}")
        return []

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
# ZONA 2: SECUENCIA DE ENVÍO
# ==============================================================================

def ejecutar_secuencia_completa(jornada):
    print(f"🔄 Iniciando secuencia completa para Jornada {jornada}...")

    NOMBRE_SCRIPT_DATOS = "boxscore_ACB_headless.py"
    print(f"📥 0. Ejecutando {NOMBRE_SCRIPT_DATOS}...")
    try:
        subprocess.run(["python", NOMBRE_SCRIPT_DATOS], check=True, text=True)
        print("✅ Datos actualizados correctamente.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error crítico actualizando datos: {e}")
        return False

    print("🤖 1. Ejecutando ai_writer.py...")
    try:
        subprocess.run(["python", "ai_writer.py"], check=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error crítico en ai_writer: {e}")
        return False

    print("📧 2. Ejecutando email_sender.py...")
    try:
        subprocess.run(["python", "email_sender.py"], check=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error crítico en email_sender: {e}")
        return False

# ==============================================================================
# MAIN 
# ==============================================================================

def main():
    last_sent = get_last_jornada_from_log()
    target_jornada = last_sent + 1
    
    print(f"--- INICIO SCRIPT DE CONTROL ---")
    print(f"Revisando Jornada/Semana: {target_jornada}")

    game_ids = get_game_ids(TEMPORADA, COMPETICION, str(target_jornada))
    
    if len(game_ids) < 8:
        print(f"⚠️ Solo veo {len(game_ids)} partidos. Faltan datos o ha cambiado la API. No envío nada.")
        return

    finished_count = 0
    for gid in game_ids:
        if is_game_finished(gid):
            finished_count += 1
    
    print(f"📊 Estado: {finished_count}/{len(game_ids)} terminados.")

    # Filtro: Mínimo de partidos terminados (Ej: 7 de 9)
    MIN_PARTIDOS_TERMINADOS = 7

    if finished_count >= MIN_PARTIDOS_TERMINADOS:
        print(f"✅ Jornada dada por terminada ({finished_count} jugados de {len(game_ids)}).")
        
        # --- CONTROL DE ESPERA (MODO PRUEBA) ---
        if MODO_PRUEBA:
            print("🚀 MODO PRUEBA ACTIVADO: Disparando secuencia instantáneamente, sin esperas.")
        else:
            minutos_espera = random.randint(5, 45)
            print(f"☕ Simulando comportamiento humano... Esperando {minutos_espera} minutos antes de enviar.")
            print("zzz...")
            time.sleep(minutos_espera * 60) 
            print("⏰ ¡Despierta! Enviando ahora.")
        # --------------------------------------

        exito = ejecutar_secuencia_completa(target_jornada)
        
        if exito:
            fecha_log = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            linea_log = f"{fecha_log} : ✅ Jornada {target_jornada} completada y enviada.\n"
            
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(linea_log)
            
            if os.path.exists(BUFFER_FILE):
                os.remove(BUFFER_FILE)
            print("🏁 Newsletter enviada con éxito.")

    else:
        print("⚽ Aún se está jugando o faltan datos.")

if __name__ == "__main__":
    main()
