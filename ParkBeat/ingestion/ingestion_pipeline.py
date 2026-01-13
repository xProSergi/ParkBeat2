import os
import time
import schedule
import subprocess
import requests
import pandas as pd
from datetime import datetime
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw", "queue_times")
os.makedirs(RAW_DIR, exist_ok=True)
LOG_FILE = os.path.join(BASE_DIR, "data", "logs", "ingestion_log.txt")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

QUEUE_TIMES_URL = "https://queue-times.com/parks/298/queue_times.json"
SCRIPTS = [
    "scripts/preclean_queue_times.py",
    "scripts/combine_queue_times.py",
    "scripts/enrich_queue_times.py",
    "scripts/weather_enrichment.py",
    "scripts/add_temporada.py"
]

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")

# ---------------- Descarga datos nuevos ----------------
def download_queue_times():
    try:
        response = requests.get(QUEUE_TIMES_URL)
        response.raise_for_status()
        data = response.json()

        rides_list = []
        for land in data.get("lands", []):
            for ride in land.get("rides", []):
                if ride["is_open"] == True:
                    rides_list.append({
                        "zona": land["name"],
                        "atraccion": ride["name"],
                        "tiempo_espera": ride["wait_time"],
                        "ultima_actualizacion": ride["last_updated"]
                    })

        df = pd.DataFrame(rides_list)
        if df.empty:
            log("⚠️ No se descargaron registros nuevos")
            return

        df["ultima_actualizacion"] = pd.to_datetime(df["ultima_actualizacion"])
        now = datetime.now()
        df["fecha"] = now.strftime("%Y-%m-%d")
        df["hora"] = now.strftime("%H:%M")
        df["dia_semana"] = now.strftime("%A")

        if "timestamp" in df.columns:
            df = df.drop(columns=["timestamp"])

        filename = f"queue_times_{now.strftime('%Y-%m-%d_%H-%M')}.csv"
        output_path = os.path.join(RAW_DIR, filename)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

        log(f"📥 Ingesta completada: {len(df)} registros → {output_path}")

    except Exception as e:
        log(f"❌ Error durante la ingesta: {e}")

# ---------------- Ejecutar scripts ----------------
def run_pipeline():
    log("🚀 Ejecutando pipeline completo...")
    for script in SCRIPTS:
        path = os.path.join(BASE_DIR, script)
        if os.path.exists(path):
            log(f"▶ Ejecutando {script}...")
            try:
                subprocess.run([sys.executable, path], check=True)
                log(f"✅ Finalizado {script}")
            except subprocess.CalledProcessError as e:
                log(f"❌ Error en {script}: {e}")
        else:
            log(f"❌ No se encontró {script}")
    log("Pipeline completo.\n")

# ---------------- Scheduler ----------------
def run_scheduler(interval_minutes=15):
    log(f"⏰ Iniciando ingesta automática cada {interval_minutes} minutos")
    
    def job():
        download_queue_times()
        run_pipeline()
    
    schedule.every(interval_minutes).minutes.do(job)
    job()  # primera ejecución inmediata

    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    run_scheduler(15)