import requests
import os
import re
import datetime
import subprocess 
import time
import random
import sys

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
TEMPORADA = '2025'
COMPETICION = '1'
LOG_FILE = "data/log.txt"
BUFFER_FILE = "data/buffer_control.txt"

# 🚨 INTERRUPTOR DE PRUEBAS 🚨
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
    except:
        return 0
    return last_jornada

def get_game_ids(temp_id, comp_id, jornada_id):
    url_base = f"https://api2.acb.com/api/seasondata/Competition/matches?competitionId={comp_id}"
    try:
        r_base = requests.get(url_base, headers=HEADERS_API, timeout=15)
        if r_base.status_code == 200:
            data = r_base.json()
            rondas = data.get('availableFilters', {}).get('rounds', [])
            round_id_interno = next((r.get('id') for r in rondas if str(r.get('roundNumber')) == str(jornada_id)), None)
            if not round_id_interno: return []
            url_jornada = f"https://api2.acb.com/api/seasondata/Competition/matches?competitionId={comp_id}&roundId={round_id_interno}"
            r_jornada = requests.get(url_jornada, headers=HEADERS_API, timeout=15)
            if r_jornada.status_code == 200:
                return [p.get('id') for p in r_jornada.json().get('matches', []) if p.get('id')]
        return []
    except:
        return []

def is_game_finished(game_id):
    url = "https://api2.acb.com/api/matchdata/Result/boxscores"
    try:
        r = requests.get(url, params={'matchId': game_id}, headers=HEADERS_API, timeout=5)
        return 'teamBoxscores' in r.json()
    except: return False

def ejecutar_secuencia_completa(jornada):
    print(f"🔄 Iniciando secuencia completa para Jornada {jornada}...")

    # PASO 0: SCRAPER
    try:
        subprocess.run(["python", "boxscore_ACB_headless.py"], check=True)
    except: return False

    # PASO 1: IA (Le pasamos el número de jornada como argumento)
    print(f"🤖 1. Ejecutando ai_writer.py para Jornada {jornada}...")
    try:
        subprocess.run(["python", "ai_writer.py", str(jornada)], check=True)
    except: return False

    # PASO 2: EMAIL
    print("📧 2. Ejecutando email_sender.py...")
    try:
        subprocess.run(["python", "email_sender.py"], check=True)
        return True
    except: return False

def main():
    last_sent = get_last_jornada_from_log()
    target_jornada = last_sent + 1
    
    print(f"--- INICIO SCRIPT DE CONTROL ---")
    print(f"Revisando Jornada/Semana: {target_jornada}")

    game_ids = get_game_ids(TEMPORADA, COMPETICION, str(target_jornada))
    if len(game_ids) < 8: return

    finished_count = sum(1 for gid in game_ids if is_game_finished(gid))
    print(f"📊 Estado: {finished_count}/{len(game_ids)} terminados.")

    if finished_count >= 7:
        if not MODO_PRUEBA:
            time.sleep(random.randint(5, 45) * 60)
        
        if ejecutar_secuencia_completa(target_jornada):
            fecha_log = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{fecha_log} : ✅ Jornada {target_jornada} completada y enviada.\n")
            print("🏁 Newsletter enviada con éxito.")

if __name__ == "__main__":
    main()
